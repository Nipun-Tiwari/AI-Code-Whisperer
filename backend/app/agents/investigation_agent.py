from __future__ import annotations

import json

import structlog
from google import genai
from google.genai import types as gtypes
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.agents.state import WorkflowState
from app.retrieval.service import EvidenceItem, RetrievalService

logger = structlog.get_logger(__name__)

_MAX_CONTEXT_CHARS = 10000
_MAX_EVIDENCE_ITEMS = 15


async def investigation_agent_node(state: WorkflowState, db: AsyncSession | None = None) -> WorkflowState:
    """Perform multi-step code-level root-cause investigation."""
    settings = get_settings()
    issue_description = state["user_request"]

    if state.get("tokens_used", 0) >= state.get("token_budget", 8000):
        state.setdefault("warnings", []).append("investigation_agent: token budget reached")
        return {**state, "agent_outputs": {**state.get("agent_outputs", {}), "investigation_agent": {"skipped": True}}}

    # Step 1: Extract searchable entities
    key_entities: list[str] = state.get("plan", {}).get("key_entities", [])
    if not key_entities and settings.gemini_configured:
        key_entities = await _extract_entities(issue_description, settings)
        state["tokens_used"] = state.get("tokens_used", 0) + 100  # estimate

    if not key_entities:
        # Fall back to using the raw issue text
        key_entities = [issue_description]

    # Step 2: Retrieve evidence for each entity
    all_evidence: list[EvidenceItem] = []
    seen_chunk_ids: set[str] = set()

    if db is not None:
        retrieval = RetrievalService(db)
        queries = [issue_description] + key_entities[:4]  # limit queries

        for query in queries:
            try:
                items = await retrieval.search(
                    query=query,
                    repository_id=state["repository_id"],
                    top_k=6,
                )
                for item in items:
                    if item.chunk_id not in seen_chunk_ids:
                        seen_chunk_ids.add(item.chunk_id)
                        all_evidence.append(item)
            except Exception as exc:
                logger.warning("Investigation retrieval failed for query", query=query[:50], error=str(exc))

    all_evidence = all_evidence[:_MAX_EVIDENCE_ITEMS]

    # Store evidence
    state["retrieved_evidence"] = [
        {
            "chunk_id": e.chunk_id,
            "file_path": e.file_path,
            "line_start": e.line_start,
            "line_end": e.line_end,
            "text": e.text,
            "symbol_name": e.symbol_name,
            "language": e.language,
            "score": e.score,
        }
        for e in all_evidence
    ]

    if not all_evidence:
        result = {
            "symptom_summary": issue_description,
            "affected_files": [],
            "execution_path": [],
            "hypotheses": [
                {
                    "rank": 1,
                    "description": "Could not retrieve relevant code evidence for investigation.",
                    "supporting_evidence": [],
                    "confidence": "low",
                }
            ],
            "suggested_remediation": "Ensure the repository is indexed and re-submit the investigation.",
            "limitations": "No code evidence was retrieved from the repository.",
            "follow_up_checks": ["Verify repository indexing is complete"],
        }
        return {**state, "agent_outputs": {**state.get("agent_outputs", {}), "investigation_agent": result}}

    # Step 3 & 4: Trace code path and rank hypotheses
    result = await _run_investigation(issue_description, all_evidence, settings, state)

    return {
        **state,
        "agent_outputs": {**state.get("agent_outputs", {}), "investigation_agent": result},
    }


async def _extract_entities(issue_description: str, settings) -> list[str]:
    """Use Gemini Flash to extract searchable entities from the issue description."""
    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = f"""Extract searchable code entities from this issue description.
Return JSON: {{"entities": ["function_name", "module_name", "error_type", "keyword"]}}
Limit to 5 most specific, relevant entities.

Issue: {issue_description}"""

        response = await client.aio.models.generate_content(
            model=settings.gemini_model_fast,
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=200,
                temperature=0.1,
            ),
        )
        parsed = json.loads(response.text or "{}")
        return parsed.get("entities", [])
    except Exception as exc:
        logger.warning("Entity extraction failed", error=str(exc))
        return []


async def _run_investigation(
    issue_description: str,
    evidence: list[EvidenceItem],
    settings,
    state: WorkflowState,
) -> dict:
    """Run the full investigation analysis using Gemini Pro."""
    if not settings.gemini_configured:
        return {
            "symptom_summary": issue_description,
            "affected_files": list({e.file_path for e in evidence}),
            "execution_path": [],
            "hypotheses": [],
            "suggested_remediation": "LLM not configured.",
            "limitations": "Gemini not configured — raw retrieval only.",
            "follow_up_checks": [],
        }

    # Build context
    context_parts: list[str] = []
    total_chars = 0
    for item in evidence:
        snippet = (
            f"[{item.retrieval_method.upper()}] {item.file_path}:{item.line_start}-{item.line_end}"
            f" ({item.symbol_name or 'unknown'})\n```\n{item.text[:500]}\n```"
        )
        if total_chars + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        context_parts.append(snippet)
        total_chars += len(snippet)

    context = "\n\n".join(context_parts)

    prompt = f"""You are a senior software engineer performing root-cause analysis.

Issue reported: {issue_description}

Retrieved code evidence (each labeled with file:lines):
{context}

Perform a thorough investigation. For each step in the execution path, label it as either:
- "source_fact": directly observable from the retrieved code
- "inferred": your reasoning about likely behaviour not directly in the code

Respond with valid JSON:
{{
  "symptom_summary": "<restate the reported symptom clearly>",
  "affected_files": ["<file1>", "<file2>"],
  "execution_path": [
    {{
      "step": 1,
      "location": "<file>:<line>",
      "description": "<what happens here>",
      "evidence": "source_fact|inferred"
    }}
  ],
  "hypotheses": [
    {{
      "rank": 1,
      "description": "<most likely root cause>",
      "supporting_evidence": ["<file>:<line> - <observation>"],
      "confidence": "high|medium|low"
    }}
  ],
  "suggested_remediation": "<concrete steps to fix>",
  "limitations": "<what evidence was missing; note this is static analysis only, not runtime>",
  "follow_up_checks": ["<check1>", "<check2>"]
}}"""

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model_strong,
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=2048,
                temperature=0.2,
            ),
        )
        result = json.loads(response.text or "{}")

        usage = response.usage_metadata
        tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
        state["tokens_used"] = state.get("tokens_used", 0) + tokens

        # Ensure required fields
        result.setdefault("symptom_summary", issue_description)
        result.setdefault("affected_files", list({e.file_path for e in evidence}))
        result.setdefault("execution_path", [])
        result.setdefault("hypotheses", [])
        result.setdefault("suggested_remediation", "Review the evidence above and apply targeted fixes.")
        result.setdefault("limitations", "This is static code analysis only. Runtime behaviour was not inspected.")
        result.setdefault("follow_up_checks", [])
        return result

    except Exception as exc:
        logger.error("Investigation LLM call failed", error=str(exc))
        state.setdefault("errors", []).append(f"investigation_agent llm: {exc}")
        return {
            "symptom_summary": issue_description,
            "affected_files": list({e.file_path for e in evidence}),
            "execution_path": [],
            "hypotheses": [],
            "suggested_remediation": "LLM analysis failed. Review retrieved code evidence manually.",
            "limitations": f"LLM error: {exc}",
            "follow_up_checks": [],
        }
