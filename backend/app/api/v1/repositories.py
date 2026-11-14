from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.auth.github_app import get_github_client
from app.dependencies import DbDep, UserDep
from app.exceptions import ForbiddenError, NotFoundError, ServiceUnavailableError
from app.models import GitHubConnection, IndexJob, Repository, RepositoryVersion
from app.models.index_job import IndexJobStatus
from app.models.repository import RepositoryStatus
from app.schemas.common import PaginatedResponse
from app.schemas.indexing import IndexJobResponse
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
    stmt = select(Repository).where(
        Repository.user_id == current_user.id,
        Repository.status != RepositoryStatus.removed,
    )
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Repository.name.ilike(pattern) | Repository.owner.ilike(pattern)
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Repository.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    repos = (await db.execute(stmt)).scalars().all()

    repo_schemas: list[RepositorySchema] = []
    for repo in repos:
        version_stmt = (
            select(RepositoryVersion)
            .where(RepositoryVersion.repository_id == repo.id, RepositoryVersion.branch == repo.selected_branch)
            .order_by(RepositoryVersion.index_version.desc())
            .limit(1)
        )
        latest_version = (await db.execute(version_stmt)).scalar_one_or_none()
        schema = RepositorySchema.model_validate(repo)
        if latest_version:
            schema.latest_version = RepositoryVersionSchema.model_validate(latest_version)
        schema.full_name = f"{repo.owner}/{repo.name}"
        repo_schemas.append(schema)

    return PaginatedResponse(items=repo_schemas, total=total, page=page, page_size=page_size, has_more=(page * page_size) < total)


@router.post("", response_model=RepositorySchema, status_code=201)
async def add_repository(
    body: AddRepositoryRequest,
    current_user: UserDep,
    db: DbDep,
) -> RepositorySchema:
    """Register an authorized GitHub repository for indexing."""
    # Validate the GitHub connection belongs to this user
    conn_result = await db.execute(
        select(GitHubConnection).where(
            GitHubConnection.id == body.github_connection_id,
            GitHubConnection.user_id == current_user.id,
        )
    )
    conn = conn_result.scalar_one_or_none()
    if not conn:
        raise ForbiddenError("GitHub connection not found or not accessible.")

    if not conn.github_app_installation_id:
        raise ForbiddenError("GitHub App installation is missing.")

    github = get_github_client()
    try:
        installation_token = await github.get_installation_token(
            int(conn.github_app_installation_id)
        )
        info = await github.get_repo_info(body.owner, body.name, installation_token)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403, 404}:
            raise ForbiddenError(
                "Repository is not accessible through this GitHub App installation."
            ) from exc
        raise ServiceUnavailableError(
            "Unable to validate repository access with GitHub.",
            service="github",
        ) from exc
    except httpx.RequestError as exc:
        raise ServiceUnavailableError(
            "Unable to reach GitHub to validate repository access.",
            service="github",
        ) from exc

    github_repo_id = str(info.get("id", ""))
    default_branch = info.get("default_branch", body.branch)

    repo = Repository(
        user_id=current_user.id,
        github_connection_id=body.github_connection_id,
        owner=body.owner,
        name=body.name,
        github_repo_id=github_repo_id,
        default_branch=default_branch,
        selected_branch=body.branch,
        status=RepositoryStatus.pending,
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
    repo = await _get_user_repo(repository_id, current_user.id, db)

    version_stmt = (
        select(RepositoryVersion)
        .where(RepositoryVersion.repository_id == repo.id, RepositoryVersion.branch == repo.selected_branch)
        .order_by(RepositoryVersion.index_version.desc())
        .limit(1)
    )
    latest_version = (await db.execute(version_stmt)).scalar_one_or_none()

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
    repo = await _get_user_repo(repository_id, current_user.id, db)

    # Soft-delete: mark as removed (actual vector deletion is async)
    repo.status = RepositoryStatus.removed
    await db.commit()

    # Schedule vector cleanup in background
    import asyncio
    from app.indexing.vector_store import get_vector_store
    asyncio.create_task(_cleanup_vectors(str(repository_id)))


@router.get("/{repository_id}/branches")
async def list_branches(
    repository_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> list[str]:
    repo = await _get_user_repo(repository_id, current_user.id, db)

    conn_result = await db.execute(
        select(GitHubConnection).where(GitHubConnection.id == repo.github_connection_id)
    )
    conn = conn_result.scalar_one_or_none()
    if not conn or not conn.github_app_installation_id:
        return [repo.default_branch]

    github = get_github_client()
    try:
        installation_token = await github.get_installation_token(
            int(conn.github_app_installation_id)
        )
        return await github.list_branches(
            repo.owner,
            repo.name,
            installation_token,
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise ServiceUnavailableError(
            "Unable to load branches from GitHub.",
            service="github",
        ) from exc


@router.get("/{repository_id}/index-jobs", response_model=list[IndexJobResponse])
async def list_index_jobs(
    repository_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> list[IndexJobResponse]:
    repo = await _get_user_repo(repository_id, current_user.id, db)
    result = await db.execute(
        select(IndexJob)
        .where(IndexJob.repository_id == repo.id)
        .order_by(IndexJob.created_at.desc())
        .limit(20)
    )
    jobs = result.scalars().all()
    return [IndexJobResponse.model_validate(j) for j in jobs]


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_repo(repo_id: uuid.UUID, user_id: uuid.UUID, db: DbDep) -> Repository:  # type: ignore[type-arg]
    result = await db.execute(
        select(Repository).where(Repository.id == repo_id, Repository.user_id == user_id)
    )
    repo = result.scalar_one_or_none()
    if not repo:
        raise NotFoundError("Repository not found or not accessible.")
    return repo


async def _cleanup_vectors(repository_id: str) -> None:
    from app.indexing.vector_store import get_vector_store
    try:
        vs = get_vector_store()
        await vs.delete_by_repository(repository_id)
    except Exception:
        pass
