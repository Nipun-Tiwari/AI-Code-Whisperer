from __future__ import annotations

import structlog
from google import genai
from google.genai import types as gtypes
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.agents.state import WorkflowState
from app.retrieval.service import EvidenceItem, RetrievalService

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are a code repository expert. Answer questions about the repository using ONLY the provided code evidence.

Rules:
- If the evidence doesn't support an answer, say so explicitly
- Always cite file paths and line numbers from the provided evidence
- Distinguish between facts visible in the code and your inferences
- Do not invent functionality not shown in the retrieved code

Respond with valid JSON:
{
  "answer": "<detailed answer>",
  "citations": [{"file_path": "<path>", "line_start": <N>, "line_end": <N>, "excerpt": "<short quote>"}],
  "confidence": "high|medium|low",
  "limitations": "<what evidence was missing or insufficient>"
}"""

_MAX_CONTEXT_CHARS = 8000


async def repository_agent_node(state: WorkflowState, db: AsyncSession | None = None) -> WorkflowState:
    """Answer repository Q&A using hybrid retrieval + Gemini."""
    settings = get_settings()

    # Check token budget
    if state.get("tokens_used", 0) >= state.get("token_budget", 4000):
        state.setdefault("warnings", []).append("repository_agent: token budget reached before execution")
        return {**state, "agent_outputs": {**state.get("agent_outputs", {}), "repository_agent": {"skipped": True}}}

    evidence_items: list[EvidenceItem] = []

    if db is not None:
        try:
            retrieval = RetrievalService(db)
            evidence_items = await retrieval.search(
                query=state["user_request"],
                repository_id=state["repository_id"],
                top_k=10,
            )
            # Store evidence in state
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
                    "retrieval_method": e.retrieval_method,
                }
                for e in evidence_items
            ]
        except Exception as exc:
            logger.error("Repository agent retrieval failed", error=str(exc))
            state.setdefault("errors", []).append(f"repository_agent retrieval: {exc}")

    if not evidence_items:
        result = {
            "answer": "No relevant code was found for your question. Ensure the repository is indexed and try rephrasing.",
            "citations": [],
            "confidence": "low",
            "limitations": "No evidence retrieved from the repository index.",
        }
        return {
            **state,
            "agent_outputs": {**state.get("agent_outputs", {}), "repository_agent": result},
        }

    # Build context respecting token budget
    context_parts: list[str] = []
    total_chars = 0
    for item in evidence_items:
        snippet = f"File: {item.file_path} (lines {item.line_start}–{item.line_end})\n```\n{item.text[:600]}\n```"
        if total_chars + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        context_parts.append(snippet)
        total_chars += len(snippet)

    context = "\n\n".join(context_parts)
    prompt = f"""{_SYSTEM_PROMPT}

User question: {state["user_request"]}

Retrieved code evidence:
{context}"""

    result: dict = {}

    if settings.gemini_configured:
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            import json
            response = await client.aio.models.generate_content(
                model=settings.gemini_model_strong,
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=1024,
                    temperature=0.2,
                ),
            )
            raw = response.text or "{}"
            result = json.loads(raw)

            usage = response.usage_metadata
            tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
            state["tokens_used"] = state.get("tokens_used", 0) + tokens

        except Exception as exc:
            logger.error("Repository agent LLM call failed", error=str(exc))
            state.setdefault("errors", []).append(f"repository_agent llm: {exc}")
            result = {
                "answer": "Failed to generate an answer. Please try again.",
                "citations": [],
                "confidence": "low",
                "limitations": str(exc),
            }
    else:
        # Return raw evidence without LLM synthesis
        result = {
            "answer": f"Found {len(evidence_items)} relevant code sections. LLM synthesis unavailable.",
            "citations": [
                {
                    "file_path": e.file_path,
                    "line_start": e.line_start,
                    "line_end": e.line_end,
                    "excerpt": e.text[:100],
                }
                for e in evidence_items[:5]
            ],
            "confidence": "low",
            "limitations": "Gemini not configured — raw retrieval only.",
        }

    return {
        **state,
        "agent_outputs": {**state.get("agent_outputs", {}), "repository_agent": result},
    }
