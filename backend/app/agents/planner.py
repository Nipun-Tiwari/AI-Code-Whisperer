from __future__ import annotations

import json

import structlog
from google import genai
from google.genai import types as gtypes

from app.config import get_settings
from app.agents.state import WorkflowState

logger = structlog.get_logger(__name__)

_BUDGET_BY_TYPE: dict[str, int] = {
    "investigation": 8000,
    "security": 6000,
    "documentation": 6000,
    "repository_qa": 4000,
}

_SYSTEM_PROMPT = """You are a request classifier for a code repository intelligence tool.

Classify the user request into exactly one of these task types:
- repository_qa: Questions about code structure, how things work, what a file/function does, finding code, understanding architecture
- investigation: Debugging a bug, tracing an error, investigating unexpected behaviour, root-cause analysis of a defect
- security: Security audit, vulnerability scan, dependency check, finding insecure patterns
- documentation: Generating documentation, architecture overview, module explanation, API docs

Respond with valid JSON only:
{
  "type": "<task_type>",
  "reasoning": "<one sentence why>",
  "key_entities": ["<entity1>", "<entity2>"]
}

If unclear, default to "repository_qa"."""


async def planner_node(state: WorkflowState) -> WorkflowState:
    """Classify the user request and assign routing + token budget."""
    settings = get_settings()
    user_request = state["user_request"]

    # Check LLM quota before proceeding
    from app.usage.quota_manager import get_quota_manager
    qm = get_quota_manager()
    if not await qm.check_service_available("gemini_llm"):
        return {
            **state,
            "request_type": "repository_qa",
            "plan": {"type": "repository_qa", "reasoning": "llm_quota_exhausted", "key_entities": []},
            "token_budget": 0,
            "task_status": "failed",
            "service_constraints": [*(state.get("service_constraints") or []), "gemini_llm:quota_exhausted"],
            "errors": [*(state.get("errors") or []), "LLM service quota exhausted. Please try again later."],
        }

    request_type = "repository_qa"
    plan: dict = {}

    if settings.gemini_configured:
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = f"{_SYSTEM_PROMPT}\n\nUser request: {user_request}"

            response = await client.aio.models.generate_content(
                model=settings.gemini_model_fast,
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=256,
                    temperature=0.1,
                ),
            )

            raw = response.text or ""
            parsed = json.loads(raw)
            detected_type = parsed.get("type", "repository_qa")
            if detected_type in _BUDGET_BY_TYPE:
                request_type = detected_type

            plan = {
                "type": request_type,
                "reasoning": parsed.get("reasoning", ""),
                "key_entities": parsed.get("key_entities", []),
            }

            # Track token usage
            usage = response.usage_metadata
            tokens_used = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
            state["tokens_used"] = state.get("tokens_used", 0) + tokens_used

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Planner JSON parse failed, defaulting to repository_qa", error=str(exc))
            plan = {"type": request_type, "reasoning": "parse_error", "key_entities": []}
        except Exception as exc:
            logger.error("Planner LLM call failed", error=str(exc))
            state.setdefault("errors", []).append(f"planner: {exc}")
            plan = {"type": request_type, "reasoning": "llm_error", "key_entities": []}
    else:
        # Simple keyword-based fallback when Gemini is not configured
        lower = user_request.lower()
        if any(w in lower for w in ["bug", "error", "crash", "fail", "exception", "investigate", "root cause"]):
            request_type = "investigation"
        elif any(w in lower for w in ["security", "vulnerability", "cve", "dependency", "audit", "secret"]):
            request_type = "security"
        elif any(w in lower for w in ["document", "architecture", "overview", "explain module", "api doc"]):
            request_type = "documentation"
        plan = {"type": request_type, "reasoning": "keyword_fallback", "key_entities": []}

    return {
        **state,
        "request_type": request_type,
        "plan": plan,
        "token_budget": _BUDGET_BY_TYPE[request_type],
        "task_status": "running",
    }
