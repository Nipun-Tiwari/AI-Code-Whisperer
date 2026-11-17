from __future__ import annotations

import uuid

import structlog

from app.agents.task_service import AgentTaskService
from app.db.session import get_session_factory

logger = structlog.get_logger(__name__)


async def run_agent_task_background(task_id: uuid.UUID) -> None:
    """Execute an AgentTask in a fresh DB session (for FastAPI BackgroundTasks)."""
    factory = get_session_factory()
    service = AgentTaskService()
    try:
        async with factory() as db:
            await service.run_task(db=db, task_id=task_id)
    except Exception as exc:
        logger.error(
            "Background agent task failed",
            task_id=str(task_id),
            error=str(exc),
            exc_info=True,
        )
