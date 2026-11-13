from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.agents.task_service import AgentTaskService
from app.dependencies import DbDep, UserDep
from app.exceptions import NotFoundError
from app.models import Repository
from app.schemas.indexing import TaskResponse

router = APIRouter(prefix="/documentation", tags=["documentation"])

_service = AgentTaskService()


class DocumentationCreate(BaseModel):
    repository_id: uuid.UUID
    doc_type: str = "architecture"  # architecture | module | technical
    module_path: str = ""
    branch: str = "main"


@router.post("/generate", response_model=TaskResponse, status_code=202)
async def generate_documentation(
    body: DocumentationCreate,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Generate technical documentation grounded in repository evidence."""
    repo_result = await db.execute(
        select(Repository).where(
            Repository.id == body.repository_id,
            Repository.user_id == current_user.id,
        )
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise NotFoundError("Repository not found or not accessible.")

    scope = f" for {body.module_path}" if body.module_path else ""
    user_request = f"Generate {body.doc_type} documentation{scope} for {repo.owner}/{repo.name}"

    task = await _service.create_task(
        db=db,
        user_id=current_user.id,
        repository_id=body.repository_id,
        request_type="documentation",
        user_request=user_request,
    )

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


@router.get("/{task_id}", response_model=TaskResponse)
async def get_documentation(
    task_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> TaskResponse:
    """Get the generated documentation."""
    task = await _service.get_task(db=db, task_id=task_id)
    if not task or task.user_id != current_user.id:
        raise NotFoundError("Documentation task not found.")

    return TaskResponse(
        task_id=task.id,
        status=task.status.value,
        task_type=task.task_type.value,
        result=task.result,
        tokens_used=task.tokens_used,
    )
