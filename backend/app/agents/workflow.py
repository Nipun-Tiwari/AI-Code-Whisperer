from __future__ import annotations

from typing import Any

import structlog
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import WorkflowState
from app.agents.planner import planner_node
from app.agents.repository_agent import repository_agent_node
from app.agents.investigation_agent import investigation_agent_node
from app.agents.security_agent import security_agent_node
from app.agents.documentation_agent import documentation_agent_node
from app.agents.synthesizer import synthesizer_node

logger = structlog.get_logger(__name__)

_workflow = None


def _route_after_planner(state: WorkflowState) -> str:
    """Route to the appropriate specialist agent based on planner classification."""
    request_type = state.get("request_type", "repository_qa")
    route_map = {
        "repository_qa": "repository_agent",
        "investigation": "investigation_agent",
        "security": "security_agent",
        "documentation": "documentation_agent",
    }
    return route_map.get(request_type, "repository_agent")


def build_workflow(db: AsyncSession | None = None):
    """Build a compiled LangGraph workflow. Agents receive db via closure."""

    async def _repo_node(state: WorkflowState) -> WorkflowState:
        return await repository_agent_node(state, db=db)

    async def _invest_node(state: WorkflowState) -> WorkflowState:
        return await investigation_agent_node(state, db=db)

    async def _security_node(state: WorkflowState) -> WorkflowState:
        return await security_agent_node(state, db=db)

    async def _doc_node(state: WorkflowState) -> WorkflowState:
        return await documentation_agent_node(state, db=db)

    graph: StateGraph = StateGraph(WorkflowState)

    graph.add_node("planner", planner_node)
    graph.add_node("repository_agent", _repo_node)
    graph.add_node("investigation_agent", _invest_node)
    graph.add_node("security_agent", _security_node)
    graph.add_node("documentation_agent", _doc_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {
            "repository_agent": "repository_agent",
            "investigation_agent": "investigation_agent",
            "security_agent": "security_agent",
            "documentation_agent": "documentation_agent",
        },
    )

    for agent in ["repository_agent", "investigation_agent", "security_agent", "documentation_agent"]:
        graph.add_edge(agent, "synthesizer")

    graph.add_edge("synthesizer", END)

    return graph.compile()


def get_workflow(db: AsyncSession | None = None):
    """Return a compiled workflow. Pass db for agents that need DB access."""
    # Always build fresh when db is provided (per-request)
    return build_workflow(db=db)
