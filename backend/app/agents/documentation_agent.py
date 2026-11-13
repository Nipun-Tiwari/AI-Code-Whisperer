from __future__ import annotations

import json
from datetime import datetime, timezone

import structlog
from google import genai
from google.genai import types as gtypes
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import WorkflowState
from app.config import get_settings
from app.retrieval.service import RetrievalService

logger = structlog.get_logger(__name__)

_DOC_TYPE_PROMPTS = {
    "architecture": "Generate a high-level architecture overview document for this repository.",
    "module": "Generate a detailed module/file explanation document.",
    "technical": "Generate technical API and function-level documentation.",
}

_MAX_CONTEXT_CHARS = 10000


def _detect_doc_type(user_request: str) -> str:
    lower = user_request.lower()
    if any(w in lower for w in ["architecture", "overview", "system design", "high level", "how does it work"]):
        return "architecture"
    if any(w in lower for w in ["module", "file", "class", "explain this", "what does this"]):
        return "module"
    return "technical"


async def documentation_agent_node(state: WorkflowState, db: AsyncSession | None = None) -> WorkflowState:
    """Generate technical documentation grounded in repository evidence."""
    settings = get_settings()
    user_request = state["user_request"]

    if state.get("tokens_used", 0) >= state.get("token_budget", 6000):
        state.setdefault("warnings", []).append("documentation_agent: token budget reached")
        return {**state, "agent_outputs": {**state.get("agent_outputs", {}), "documentation_agent": {"skipped": True}}}

    doc_type = _detect_doc_type(user_request)
    evidence_items = []

    if db is not None:
        try:
            retrieval = RetrievalService(db)
            # For architecture docs, retrieve broadly; for module docs, retrieve specifically
            queries = [user_request]
            if doc_type == "architecture":
                queries += ["main entry point", "configuration", "database models"]
            elif doc_type == "module":
                queries += ["class definition", "function implementation"]

            seen = set()
            for query in queries:
                items = await retrieval.search(
                    query=query,
                    repository_id=state["repository_id"],
                    top_k=6,
                )
                for item in items:
                    if item.chunk_id not in seen:
                        seen.add(item.chunk_id)
                        evidence_items.append(item)

            evidence_items = evidence_items[:15]
        except Exception as exc:
            logger.error("Documentation agent retrieval failed", error=str(exc))
            state.setdefault("errors", []).append(f"documentation_agent retrieval: {exc}")

    if not evidence_items:
        result = {
            "doc_type": doc_type,
            "title": "Documentation Unavailable",
            "content": "No code evidence was retrieved. Ensure the repository is indexed.",
            "citations": [],
            "repository_version": state.get("commit_sha", "unknown"),
            "gaps": ["Repository not indexed or no relevant code found"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {**state, "agent_outputs": {**state.get("agent_outputs", {}), "documentation_agent": result}}

    if not settings.gemini_configured:
        result = {
            "doc_type": doc_type,
            "title": f"Repository Documentation ({doc_type})",
            "content": "LLM not configured. Raw evidence available.",
            "citations": [{"file_path": e.file_path, "line_start": e.line_start, "line_end": e.line_end} for e in evidence_items[:5]],
            "repository_version": state.get("commit_sha", "unknown"),
            "gaps": ["Gemini not configured — documentation generation unavailable"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {**state, "agent_outputs": {**state.get("agent_outputs", {}), "documentation_agent": result}}

    # Build context
    context_parts: list[str] = []
    total_chars = 0
    citations: list[dict] = []

    for item in evidence_items:
        snippet = f"### {item.file_path} (lines {item.line_start}–{item.line_end})\n```{item.language}\n{item.text[:600]}\n```"
        if total_chars + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        context_parts.append(snippet)
        citations.append({
            "file_path": item.file_path,
            "line_start": item.line_start,
            "line_end": item.line_end,
            "symbol_name": item.symbol_name,
        })
        total_chars += len(snippet)

    context = "\n\n".join(context_parts)
    doc_instruction = _DOC_TYPE_PROMPTS.get(doc_type, _DOC_TYPE_PROMPTS["technical"])

    prompt = f"""You are a technical writer generating documentation for a software repository.

Task: {doc_instruction}

User request: {user_request}

Code evidence from the repository:
{context}

Instructions:
- Base the documentation ONLY on the provided code evidence
- Use Markdown formatting with clear headers
- For any claim not directly supported by the code, add: "> **Note:** This is inferred, not confirmed by source code."
- Include specific file paths and function/class names
- Structure the document logically for the target audience (software developers)
- Be concise but complete

Respond with valid JSON:
{{
  "title": "<documentation title>",
  "content": "<full Markdown content>",
  "gaps": ["<what information was missing or uncertain>"]
}}"""

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model_strong,
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                response_mime_type="application/json",
                max_output_tokens=2048,
                temperature=0.3,
            ),
        )
        parsed = json.loads(response.text or "{}")

        usage = response.usage_metadata
        tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
        state["tokens_used"] = state.get("tokens_used", 0) + tokens

        result = {
            "doc_type": doc_type,
            "title": parsed.get("title", f"Repository Documentation ({doc_type})"),
            "content": parsed.get("content", ""),
            "citations": citations,
            "repository_version": state.get("commit_sha", "unknown"),
            "gaps": parsed.get("gaps", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        logger.error("Documentation agent LLM call failed", error=str(exc))
        state.setdefault("errors", []).append(f"documentation_agent llm: {exc}")
        result = {
            "doc_type": doc_type,
            "title": "Documentation Generation Failed",
            "content": f"LLM error: {exc}",
            "citations": citations,
            "repository_version": state.get("commit_sha", "unknown"),
            "gaps": ["LLM generation failed"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return {
        **state,
        "agent_outputs": {**state.get("agent_outputs", {}), "documentation_agent": result},
    }
