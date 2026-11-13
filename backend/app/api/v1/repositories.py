from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.dependencies import DbDep, UserDep
from app.exceptions import ForbiddenError, NotFoundError
from app.models.repository import Repository
from app.models.repository_version import RepositoryVersion
from app.schemas.common import PaginatedResponse
from app.schemas.repository import AddRepositoryRequest, RepositorySchema, RepositoryVersionSchema

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=PaginatedResponse[RepositorySchema])
async def list_repositories(
    current_user: UserDep,
    db: DbDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
) -> PaginatedResponse[RepositorySchema]:
    """List repositories accessible to the authenticated user."""
    stmt = select(Repository).where(Repository.user_id == current_user.id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Repository.name.ilike(pattern) | Repository.owner.ilike(pattern)
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    repos = result.scalars().all()

    # Attach latest version to each repo
    repo_schemas: list[RepositorySchema] = []
    for repo in repos:
        version_stmt = (
            select(RepositoryVersion)
            .where(
                RepositoryVersion.repository_id == repo.id,
                RepositoryVersion.branch == repo.selected_branch,
            )
            .order_by(RepositoryVersion.index_version.desc())
            .limit(1)
        )
        version_result = await db.execute(version_stmt)
        latest_version = version_result.scalar_one_or_none()

        schema = RepositorySchema.model_validate(repo)
        if latest_version:
            schema.latest_version = RepositoryVersionSchema.model_validate(latest_version)
        schema.full_name = f"{repo.owner}/{repo.name}"
        repo_schemas.append(schema)

    return PaginatedResponse(
        items=repo_schemas,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post("", response_model=RepositorySchema, status_code=201)
async def add_repository(
    body: AddRepositoryRequest,
    current_user: UserDep,
    db: DbDep,
) -> RepositorySchema:
    """
    Register a GitHub repository for indexing.

    TODO: validate the repository against the GitHub API using the GitHub connection.
    """
    repo = Repository(
        user_id=current_user.id,
        github_connection_id=body.github_connection_id,
        owner=body.owner,
        name=body.name,
        github_repo_id="",  # TODO: fetch from GitHub API
        default_branch=body.branch,
        selected_branch=body.branch,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    schema = RepositorySchema.model_validate(repo)
    schema.full_name = f"{repo.owner}/{repo.name}"
    return schema


@router.get("/{repository_id}", response_model=RepositorySchema)
async def get_repository(
    repository_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> RepositorySchema:
    """Get repository details for the authenticated user."""
    stmt = select(Repository).where(
        Repository.id == repository_id,
        Repository.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if repo is None:
        raise NotFoundError("Repository not found or not accessible.")

    version_stmt = (
        select(RepositoryVersion)
        .where(
            RepositoryVersion.repository_id == repo.id,
            RepositoryVersion.branch == repo.selected_branch,
        )
        .order_by(RepositoryVersion.index_version.desc())
        .limit(1)
    )
    version_result = await db.execute(version_stmt)
    latest_version = version_result.scalar_one_or_none()

    schema = RepositorySchema.model_validate(repo)
    if latest_version:
        schema.latest_version = RepositoryVersionSchema.model_validate(latest_version)
    schema.full_name = f"{repo.owner}/{repo.name}"
    return schema


@router.delete("/{repository_id}", status_code=204)
async def remove_repository(
    repository_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> None:
    """
    Remove a repository and schedule deletion of associated indexed data.

    TODO: enqueue a background job to delete vectors, chunks, summaries and job records.
    """
    stmt = select(Repository).where(
        Repository.id == repository_id,
        Repository.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    repo = result.scalar_one_or_none()

    if repo is None:
        raise NotFoundError("Repository not found or not accessible.")

    await db.delete(repo)
    await db.commit()
