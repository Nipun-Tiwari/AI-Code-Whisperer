from __future__ import annotations

from typing import TypedDict


class WorkflowState(TypedDict):
    # Identity
    task_id: str
    user_id: str
    repository_id: str
    branch: str
    commit_sha: str

    # Request
    user_request: str
    request_type: str  # "repository_qa" | "investigation" | "security" | "documentation"

    # Planning
    plan: dict

    # Evidence collected during execution
    retrieved_evidence: list[dict]  # EvidenceItem dicts
    tool_results: list[dict]

    # Agent outputs keyed by agent name
    agent_outputs: dict

    # Token tracking
    token_budget: int
    tokens_used: int

    # Service constraints / unavailable services
    service_constraints: list[str]

    # Execution status
    errors: list[str]
    warnings: list[str]
    final_result: dict | None
    task_status: str  # "running" | "completed" | "partial" | "failed" | "paused"
