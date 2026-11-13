from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.dependencies import DbDep, UserDep
from app.exceptions import ConflictError, NotFoundError
from app.models import IndexJob, Repository
from app.models.index_job import IndexJobMode, IndexJobStatus
from app.models.repository import RepositoryStatus
from app.schemas.indexing import IndexJobCreate, IndexJobResponse

router = APIRouter(tags=["index-jobs"])


@router.post("/repositories/{repository_id}/index-jobs", response_model=IndexJobResponse, status_code=202)
async def create_index_job(
    repository_id: uuid.UUID,
    body: IndexJobCreate,
    current_user: UserDep,
    db: DbDep,
) -> IndexJobResponse:
    """Enqueue an indexing job for the specified repository."""
    # Verify repo ownership
    repo_result = await db.execute(
        select(Repository).where(
            Repository.id == repository_id,
            Repository.user_id == current_user.id,
        )
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise NotFoundError("Repository not found or not accessible.")

    # Check for an already active job
    active_result = await db.execute(
        select(IndexJob).where(
            IndexJob.repository_id == repository_id,
            IndexJob.status.in_([
                IndexJobStatus.queued,
                IndexJobStatus.fetching,
                IndexJobStatus.classifying,
                IndexJobStatus.parsing,
                IndexJobStatus.summarizing,
                IndexJobStatus.embedding,
                IndexJobStatus.persisting,
            ]),
        )
    )
    if active_result.scalar_one_or_none():
        raise ConflictError("An indexing job is already active for this repository.")

    job = IndexJob(
        repository_id=repository_id,
        mode=body.mode,
        status=IndexJobStatus.queued,
    )
    db.add(job)

    # Mark repo as indexing
    repo.status = RepositoryStatus.indexing
    await db.commit()
    await db.refresh(job)

    return IndexJobResponse.model_validate(job)


@router.get("/index-jobs/{job_id}", response_model=IndexJobResponse)
async def get_index_job(
    job_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> IndexJobResponse:
    """Get current status and progress of an indexing job."""
    result = await db.execute(
        select(IndexJob, Repository)
        .join(Repository, IndexJob.repository_id == Repository.id)
        .where(IndexJob.id == job_id, Repository.user_id == current_user.id)
    )
    row = result.first()
    if not row:
        raise NotFoundError("Index job not found or not accessible.")

    job, _ = row
    return IndexJobResponse.model_validate(job)
