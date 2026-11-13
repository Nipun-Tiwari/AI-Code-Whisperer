from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.dependencies import DbDep, UserDep
from app.exceptions import ForbiddenError, NotFoundError, NotImplementedFeatureError
from app.models.index_job import IndexJob
from app.models.repository import Repository
from app.schemas.index_job import IndexJobSchema, StartIndexJobRequest

router = APIRouter(tags=["index-jobs"])


@router.post("/repositories/{repository_id}/index-jobs", response_model=IndexJobSchema, status_code=202)
async def start_index_job(
    repository_id: uuid.UUID,
    body: StartIndexJobRequest,
    current_user: UserDep,
    db: DbDep,
) -> IndexJobSchema:
    """
    Queue an indexing job for the specified repository.

    TODO (Phase 2): enqueue to background worker via Cloud Run job or task queue.
    For now creates the durable job record and returns it in queued state.
    """
    # Verify repository ownership
    stmt = select(Repository).where(
        Repository.id == repository_id,
        Repository.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if repo is None:
        raise NotFoundError("Repository not found or not accessible.")

    job = IndexJob(
        repository_id=repository_id,
        mode=body.mode,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return IndexJobSchema.model_validate(job)


@router.get("/index-jobs/{job_id}", response_model=IndexJobSchema)
async def get_index_job(
    job_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> IndexJobSchema:
    """Return the current state of an indexing job."""
    stmt = (
        select(IndexJob)
        .join(Repository, Repository.id == IndexJob.repository_id)
        .where(
            IndexJob.id == job_id,
            Repository.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if job is None:
        raise NotFoundError("Index job not found or not accessible.")

    return IndexJobSchema.model_validate(job)


@router.get("/repositories/{repository_id}/branches")
async def list_branches(
    repository_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> dict[str, list[str]]:
    """
    List branches available on the connected GitHub repository.

    TODO (Phase 1): fetch from GitHub API using the GitHub App client.
    """
    stmt = select(Repository).where(
        Repository.id == repository_id,
        Repository.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()
    if repo is None:
        raise NotFoundError("Repository not found or not accessible.")

    raise NotImplementedFeatureError(
        "Branch listing from GitHub API is not yet implemented. "
        "Configure GITHUB_APP credentials to enable this."
    )
