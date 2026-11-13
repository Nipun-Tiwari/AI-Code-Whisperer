from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.agents.task_service import AgentTaskService
from app.dependencies import DbDep, UserDep
from app.exceptions import NotFoundError
from app.models import AgentTask, Repository
from app.schemas.indexing import TaskResponse

router = APIRouter(prefix="/investigations", tags=["investigations"])

_service = AgentTaskService()


class InvestigationRequest:
    pass


from pydantic import BaseModel


class InvestigationCreate(BaseModel):
    repository_id: uuid.UUID
    description: str
    branch: str = "main"


@router.post("", response_model=TaskResponse, status_code=202)
async def start_investigation(
    body: InvestigationCreate,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Start a code-level root-cause investigation for a reported issue."""
    # Verify repo access
    repo_result = await db.execute(
        select(Repository).where(
            Repository.id == body.repository_id,
            Repository.user_id == current_user.id,
        )
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise NotFoundError("Repository not found or not accessible.")

    task = await _service.create_task(
        db=db,
        user_id=current_user.id,
        repository_id=body.repository_id,
        request_type="investigation",
        user_request=body.description,
    )

    # Run synchronously for now (async background task in Phase 4)
    try:
        result = await _service.run_task(db=db, task_id=task.id)
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


@router.get("/{task_id}", response_model=TaskResponse)
async def get_investigation(
    task_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Get the result of an investigation task."""
    task = await _service.get_task(db=db, task_id=task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError("Investigation not found.")

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=task.result,
        tokens_used=task.tokens_used,
    )
