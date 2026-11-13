from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.agents.task_service import AgentTaskService
from app.dependencies import DbDep, UserDep
from app.exceptions import NotFoundError
from app.models.agent_task import TaskStatus
from app.schemas.indexing import TaskResponse

router = APIRouter(tags=["agent-activity"])

_service = AgentTaskService()


class TaskListItem(BaseModel):
    task_id: uuid.UUID
    task_type: str
    status: str
    repository_id: uuid.UUID
    created_at: str
    completed_at: str | None
    tokens_used: int | None

    class Config:
        from_attributes = True


@router.get("/agent-activity", response_model=list[TaskListItem])
async def list_agent_activity(
    current_user: UserDep,
    db: DbDep,
    limit: int = Query(default=20, le=100),
) -> list[TaskListItem]:
    """List recent agent tasks for the current user."""
    tasks = await _service.list_tasks(db=db, user_id=current_user.id, limit=limit)
    return [
        TaskListItem(
            task_id=task.id,
            task_type=task.task_type.value,
            status=task.status.value,
            repository_id=task.repository_id,
            created_at=task.created_at.isoformat() if task.created_at else "",
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            tokens_used=task.tokens_used,
        )
        for task in tasks
    ]


@router.get("/agent-activity/{task_id}", response_model=TaskResponse)
async def get_agent_activity_detail(
    task_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Get detailed result and trace for a specific agent task."""
    task = await _service.get_task(db=db, task_id=task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError("Task not found.")

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=task.result,
        tokens_used=task.tokens_used,
    )


@router.post("/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Retry a failed or partial agent task."""
    task = await _service.get_task(db=db, task_id=task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError("Task not found.")

    if task.status not in (TaskStatus.failed, TaskStatus.partial, TaskStatus.paused):
        from app.exceptions import ConflictError
        raise ConflictError(f"Task cannot be retried in status: {task.status.value}")

    # Reset task status for retry
    task.status = TaskStatus.queued
    task.result = None
    await db.commit()

    try:
        await _service.run_task(db=db, task_id=task.id)
        await db.refresh(task)
    except Exception:
        await db.refresh(task)

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=task.result,
        tokens_used=task.tokens_used,
    )
