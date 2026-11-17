from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import select

from app.agents.chat_runner import run_chat_task_background
from app.agents.task_service import AgentTaskService
from app.dependencies import DbDep, UserDep
from app.exceptions import NotFoundError
from app.models import Repository
from app.models.repository import RepositoryStatus
from app.schemas.chat import ChatQueryRequest
from app.schemas.indexing import TaskResponse

router = APIRouter(prefix="/chat", tags=["chat"])

_service = AgentTaskService()


@router.post("/query", response_model=TaskResponse, status_code=202)
async def query_repository(
    body: ChatQueryRequest,
    current_user: UserDep,
    db: DbDep,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    """Start an async repository Q&A job (poll GET /chat/query/{task_id})."""
    repo_result = await db.execute(
        select(Repository).where(
            Repository.id == body.repository_id,
            Repository.user_id == current_user.id,
        )
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise NotFoundError("Repository not found or not accessible.")

    # Still create a task for not-yet-indexed repos so the client can poll a
    # consistent shape; the background runner returns a clear message.
    if repo.status not in (RepositoryStatus.indexed, RepositoryStatus.stale):
        pass

    task = await _service.create_task(
        db=db,
        user_id=current_user.id,
        repository_id=body.repository_id,
        request_type="repository_qa",
        user_request=body.question,
    )

    background_tasks.add_task(run_chat_task_background, task.id)

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=None,
        tokens_used=task.tokens_used,
    )


@router.get("/query/{task_id}", response_model=TaskResponse)
async def get_chat_query(
    task_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Get the status/result of an async chat query task."""
    task = await _service.get_task(db=db, task_id=task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError("Chat query not found.")

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=task.result,
        tokens_used=task.tokens_used,
    )
