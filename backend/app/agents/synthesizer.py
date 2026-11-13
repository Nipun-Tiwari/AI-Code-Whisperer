from __future__ import annotations

import structlog

from app.agents.state import WorkflowState

logger = structlog.get_logger(__name__)


async def synthesizer_node(state: WorkflowState) -> WorkflowState:
    """
    Controlled graph node — assembles agent outputs into a coherent final result.
    Not an LLM agent; uses deterministic logic only.
    """
    agent_outputs = state.get("agent_outputs", {})
    errors = state.get("errors", [])
    request_type = state.get("request_type", "repository_qa")

    # Determine which agent ran
    agent_map = {
        "repository_qa": "repository_agent",
        "investigation": "investigation_agent",
        "security": "security_agent",
        "documentation": "documentation_agent",
    }
    primary_agent = agent_map.get(request_type, "repository_agent")
    primary_output = agent_outputs.get(primary_agent, {})

    # Deduplicate citations across all outputs
    all_citations: list[dict] = []
    seen_citation_keys: set[str] = set()

    for output in agent_outputs.values():
        for citation in output.get("citations", []):
            key = f"{citation.get('file_path')}:{citation.get('line_start')}"
            if key not in seen_citation_keys:
                seen_citation_keys.add(key)
                all_citations.append(citation)

    # Build final result
    final_result: dict = {
        "request_type": request_type,
        "task_id": state.get("task_id"),
        "repository_id": state.get("repository_id"),
        "tokens_used": state.get("tokens_used", 0),
        "citations": all_citations,
        "warnings": state.get("warnings", []),
    }

    # Merge primary agent output
    if primary_output.get("skipped"):
        final_result["status"] = "partial"
        final_result["message"] = "Task was skipped due to token budget or service unavailability."
    else:
        final_result.update(primary_output)

    # Determine task status
    if errors:
        task_status = "partial" if primary_output else "failed"
        final_result["errors"] = errors
    else:
        task_status = "completed"

    # Validate required fields by type
    if request_type == "repository_qa" and "answer" not in final_result:
        final_result["answer"] = "No answer could be generated."
        task_status = "partial"

    elif request_type == "investigation" and "hypotheses" not in final_result:
        final_result["hypotheses"] = []
        task_status = "partial"

    elif request_type == "security" and "dependency_findings" not in final_result:
        final_result["dependency_findings"] = []
        task_status = "partial"

    elif request_type == "documentation" and "content" not in final_result:
        final_result["content"] = "No documentation could be generated."
        task_status = "partial"

    logger.info(
        "Task synthesized",
        task_id=state.get("task_id"),
        request_type=request_type,
        task_status=task_status,
        tokens_used=state.get("tokens_used", 0),
        error_count=len(errors),
    )

    return {
        **state,
        "final_result": final_result,
        "task_status": task_status,
    }
