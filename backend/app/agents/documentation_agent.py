from __future__ import annotations

import re
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
_MAX_OUTPUT_TOKENS = 8192
_H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_GAPS_SECTION_RE = re.compile(
    r"(?im)^##\s+gaps?\s*\n(.*?)(?=\n##\s|\Z)",
    re.DOTALL,
)
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+)$", re.MULTILINE)


def _detect_doc_type(user_request: str) -> str:
    lower = user_request.lower()
    if any(w in lower for w in ["architecture", "overview", "system design", "high level", "how does it work"]):
        return "architecture"
    if any(w in lower for w in ["module", "file", "class", "explain this", "what does this"]):
        return "module"
    return "technical"


def _finish_reason_is_max_tokens(response: object) -> bool:
    """Best-effort check for Gemini finish_reason indicating truncation."""
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return False
        reason = getattr(candidates[0], "finish_reason", None)
        if reason is None:
            return False
        text = str(reason).upper()
        return "MAX_TOKEN" in text or text.endswith("MAX_TOKENS") or text == "2"
    except Exception:
        return False


def _parse_markdown_documentation(
    markdown: str,
    doc_type: str,
    *,
    truncated: bool = False,
) -> tuple[str, str, list[str]]:
    """Extract title, full Markdown content, and gaps bullets from model output."""
    text = (markdown or "").strip()
    if not text:
        return (
            f"Repository Documentation ({doc_type})",
            "",
            ["Model returned empty documentation"],
        )

    title = f"Repository Documentation ({doc_type})"
    h1 = _H1_RE.search(text)
    if h1:
        title = h1.group(1).strip() or title

    gaps: list[str] = []
    gaps_match = _GAPS_SECTION_RE.search(text)
    if gaps_match:
        gaps = [m.group(1).strip() for m in _BULLET_RE.finditer(gaps_match.group(1)) if m.group(1).strip()]

    if truncated:
        gaps = [*gaps, "Output truncated by model token limit"]

    return title, text, gaps


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

Output format (Markdown only — do NOT wrap the document in JSON):
1. First line must be an H1 title: `# <documentation title>`
2. Then the full Markdown documentation body
3. Optionally end with a section:
## Gaps
- <what information was missing or uncertain>
"""

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model_strong,
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                max_output_tokens=_MAX_OUTPUT_TOKENS,
                temperature=0.3,
            ),
        )
        raw_text = (response.text or "").strip()
        truncated = _finish_reason_is_max_tokens(response)

        usage = response.usage_metadata
        if usage is not None:
            tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
            state["tokens_used"] = state.get("tokens_used", 0) + tokens

        if not raw_text:
            state.setdefault("errors", []).append("documentation_agent llm: empty response")
            result = {
                "doc_type": doc_type,
                "title": "Documentation Generation Failed",
                "content": "LLM returned empty documentation.",
                "citations": citations,
                "repository_version": state.get("commit_sha", "unknown"),
                "gaps": ["LLM generation returned empty output"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            title, content, gaps = _parse_markdown_documentation(
                raw_text,
                doc_type,
                truncated=truncated,
            )
            if truncated:
                state.setdefault("warnings", []).append(
                    "documentation_agent: output truncated by model token limit"
                )
            result = {
                "doc_type": doc_type,
                "title": title,
                "content": content,
                "citations": citations,
                "repository_version": state.get("commit_sha", "unknown"),
                "gaps": gaps,
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
