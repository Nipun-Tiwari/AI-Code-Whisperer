from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select

from app.agents.background import run_agent_task_background
from app.agents.task_service import AgentTaskService
from app.dependencies import DbDep, UserDep
from app.exceptions import NotFoundError
from app.models import Repository
from app.schemas.indexing import TaskResponse

router = APIRouter(prefix="/security", tags=["security"])

_service = AgentTaskService()


class SecurityScanCreate(BaseModel):
    repository_id: uuid.UUID
    branch: str = "main"


@router.post("/scans", response_model=TaskResponse, status_code=202)
async def start_security_scan(
    body: SecurityScanCreate,
    current_user: UserDep,
    db: DbDep,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    """Start a security scan for dependency vulnerabilities and insecure code patterns."""
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
        request_type="security",
        user_request=f"Security scan for {repo.owner}/{repo.name}",
    )

    background_tasks.add_task(run_agent_task_background, task.id)

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=None,
        tokens_used=task.tokens_used,
    )


@router.get("/scans/{scan_id}", response_model=TaskResponse)
async def get_security_scan(
    scan_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Get the results of a security scan."""
    task = await _service.get_task(db=db, task_id=scan_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError("Security scan not found.")

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=task.result,
        tokens_used=task.tokens_used,
    )
