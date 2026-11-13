"""GitHub App OAuth integration endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.auth.github_app import get_github_client
from app.config import get_settings
from app.dependencies import DbDep, UserDep
from app.exceptions import ForbiddenError, NotFoundError
from app.models import GitHubConnection
from app.models.github_connection import GitHubConnectionStatus

router = APIRouter(prefix="/integrations/github", tags=["github"])


@router.get("/connect")
async def start_github_connection() -> RedirectResponse:
    """Redirect the user to the GitHub App installation page."""
    settings = get_settings()
    install_url = f"https://github.com/apps/{settings.github_app_name}/installations/new"
    return RedirectResponse(url=install_url, status_code=302)


@router.get("/callback")
async def github_callback(
    code: str = Query(...),
    installation_id: str | None = Query(default=None),
    setup_action: str | None = Query(default=None),
    current_user: UserDep = None,  # type: ignore[assignment]
    db: DbDep = None,              # type: ignore[assignment]
) -> RedirectResponse:
    """
    Handle GitHub App OAuth callback.
    Exchanges code for user access token and stores the connection.
    """
    settings = get_settings()
    frontend_url = settings.allowed_origins[0] if settings.allowed_origins else "http://localhost:5173"

    try:
        github = get_github_client()
        token_data = await github.exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            return RedirectResponse(url=f"{frontend_url}/settings?github=error&reason=no_token")

        # Get the authenticated user's GitHub identity
        gh_user = await github.get_authenticated_user(access_token)
        github_login = gh_user.get("login", "")
        github_account_type = gh_user.get("type", "User")

        if current_user:
            # Check for existing connection
            existing_result = await db.execute(
                select(GitHubConnection).where(
                    GitHubConnection.user_id == current_user.id,
                    GitHubConnection.github_account_login == github_login,
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                existing.access_token = access_token
                existing.status = GitHubConnectionStatus.active
                if installation_id:
                    existing.github_app_installation_id = installation_id
            else:
                conn = GitHubConnection(
                    user_id=current_user.id,
                    github_account_login=github_login,
                    github_account_type=github_account_type,
                    access_token=access_token,
                    github_app_installation_id=installation_id,
                    status=GitHubConnectionStatus.active,
                )
                db.add(conn)
            await db.commit()

    except Exception as exc:
        return RedirectResponse(url=f"{frontend_url}/settings?github=error&reason=callback_failed")

    return RedirectResponse(url=f"{frontend_url}/settings?github=connected")


@router.get("")
async def list_github_connections(
    current_user: UserDep,
    db: DbDep,
) -> list[dict]:
    """List GitHub App connections for the authenticated user."""
    result = await db.execute(
        select(GitHubConnection).where(
            GitHubConnection.user_id == current_user.id,
            GitHubConnection.status == GitHubConnectionStatus.active,
        )
    )
    connections = result.scalars().all()
    return [
        {
            "id": str(conn.id),
            "github_account_login": conn.github_account_login,
            "github_account_type": conn.github_account_type,
            "installation_id": conn.github_app_installation_id,
            "status": conn.status,
            "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
        }
        for conn in connections
    ]


@router.get("/repositories")
async def list_accessible_repositories(
    current_user: UserDep,
    db: DbDep,
) -> list[dict]:
    """List GitHub repositories accessible through the user's App installation."""
    result = await db.execute(
        select(GitHubConnection).where(
            GitHubConnection.user_id == current_user.id,
            GitHubConnection.status == GitHubConnectionStatus.active,
        )
    )
    connections = result.scalars().all()

    all_repos: list[dict] = []
    github = get_github_client()

    for conn in connections:
        try:
            if conn.github_app_installation_id:
                install_token = await github.get_installation_token(
                    int(conn.github_app_installation_id)
                )
                repos = await github.list_installation_repos(install_token)
                for r in repos:
                    all_repos.append({
                        "id": str(r.get("id", "")),
                        "owner": r.get("owner", {}).get("login", ""),
                        "name": r.get("name", ""),
                        "full_name": r.get("full_name", ""),
                        "visibility": r.get("visibility", "private"),
                        "default_branch": r.get("default_branch", "main"),
                        "description": r.get("description"),
                        "github_connection_id": str(conn.id),
                    })
        except Exception:
            continue

    return all_repos


@router.delete("/{connection_id}", status_code=204)
async def disconnect_github(
    connection_id: uuid.UUID,
    current_user: UserDep,
    db: DbDep,
) -> None:
    """Disconnect a GitHub App connection."""
    result = await db.execute(
        select(GitHubConnection).where(
            GitHubConnection.id == connection_id,
            GitHubConnection.user_id == current_user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise NotFoundError("GitHub connection not found.")

    conn.status = GitHubConnectionStatus.revoked
    conn.access_token = None
    await db.commit()
