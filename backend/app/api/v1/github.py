"""GitHub App OAuth integration endpoints."""
from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx
import structlog
from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select

from app.auth.github_app import get_github_client
from app.config import get_settings
from app.dependencies import DbDep, UserDep
from app.exceptions import ForbiddenError, NotFoundError, ServiceUnavailableError
from app.models import GitHubConnection, GitHubInstallState
from app.models.github_connection import GitHubConnectionStatus

router = APIRouter(prefix="/integrations/github", tags=["github"])
logger = structlog.get_logger(__name__)


@router.post("/connect")
async def start_github_connection(
    current_user: UserDep,
    db: DbDep,
) -> dict[str, str]:
    """Create an authenticated one-time state and return the GitHub install URL."""
    settings = get_settings()
    if not all(
        (
            settings.github_app_name,
            settings.github_app_id,
            settings.github_app_client_id,
            settings.github_app_client_secret,
            settings.github_app_private_key,
        )
    ):
        raise ServiceUnavailableError("The GitHub App is not configured.", service="github")

    now = datetime.now(timezone.utc)
    await db.execute(delete(GitHubInstallState).where(GitHubInstallState.expires_at <= now))
    state = secrets.token_urlsafe(32)
    db.add(
        GitHubInstallState(
            user_id=current_user.id,
            state_hash=_hash_state(state),
            phase="install",
            expires_at=now + timedelta(minutes=15),
        )
    )
    await db.commit()

    install_url = (
        f"https://github.com/apps/{quote(settings.github_app_name, safe='')}/installations/new?"
        f"{urlencode({'state': state})}"
    )
    return {"install_url": install_url}


@router.get("/callback")
async def github_callback(
    request: Request,
    db: DbDep,
    code: str | None = Query(default=None),
    installation_id: str | None = Query(default=None),
    setup_action: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """Handle both GitHub's App setup redirect and the OAuth callback."""
    settings = get_settings()
    frontend_url = (
        settings.allowed_origins[0]
        if settings.allowed_origins
        else "http://localhost:5173"
    )
    callback_url = settings.github_app_callback_url or str(
        request.url_for("github_callback")
    )

    if not state:
        return _frontend_redirect(frontend_url, "error", "invalid_state")

    state_result = await db.execute(
        select(GitHubInstallState)
        .where(GitHubInstallState.state_hash == _hash_state(state))
        .with_for_update()
    )
    pending = state_result.scalar_one_or_none()
    if not pending or pending.expires_at <= datetime.now(timezone.utc):
        return _frontend_redirect(frontend_url, "error", "expired_state")

    if error:
        await db.delete(pending)
        await db.commit()
        return _frontend_redirect(frontend_url, "error", "authorization_denied")

    if code is None:
        if pending.phase != "install" or not installation_id:
            await db.delete(pending)
            await db.commit()
            return _frontend_redirect(frontend_url, "error", "invalid_installation")

        if setup_action not in {None, "install", "update"}:
            await db.delete(pending)
            await db.commit()
            return _frontend_redirect(frontend_url, "error", "invalid_installation")

        try:
            normalized_installation_id = str(int(installation_id))
        except ValueError:
            await db.delete(pending)
            await db.commit()
            return _frontend_redirect(frontend_url, "error", "invalid_installation")
        if int(normalized_installation_id) <= 0:
            await db.delete(pending)
            await db.commit()
            return _frontend_redirect(frontend_url, "error", "invalid_installation")

        oauth_state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        pending.state_hash = _hash_state(oauth_state)
        pending.phase = "authorize"
        pending.installation_id = normalized_installation_id
        pending.code_verifier = code_verifier
        pending.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        await db.commit()

        authorize_url = "https://github.com/login/oauth/authorize?" + urlencode(
            {
                "client_id": settings.github_app_client_id,
                "redirect_uri": callback_url,
                "state": oauth_state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return RedirectResponse(url=authorize_url, status_code=303)

    if pending.phase != "authorize" or not pending.installation_id or not pending.code_verifier:
        await db.delete(pending)
        await db.commit()
        return _frontend_redirect(frontend_url, "error", "invalid_state")

    try:
        github = get_github_client()
        token_data = await github.exchange_code_for_token(
            code,
            pending.code_verifier,
            callback_url,
        )
        access_token = token_data.get("access_token")
        if not access_token:
            await db.delete(pending)
            await db.commit()
            return _frontend_redirect(frontend_url, "error", "authorization_failed")

        gh_user = await github.get_authenticated_user(access_token)
        installations = await github.get_user_installations(access_token)
    except httpx.HTTPError:
        logger.warning("GitHub authorization request failed")
        await db.delete(pending)
        await db.commit()
        return _frontend_redirect(frontend_url, "error", "github_unavailable")

    installation = next(
        (
            item
            for item in installations
            if str(item.get("id")) == pending.installation_id
        ),
        None,
    )
    account = installation.get("account") if installation else None
    if not installation or not isinstance(account, dict) or not account.get("login"):
        await db.delete(pending)
        await db.commit()
        return _frontend_redirect(frontend_url, "error", "installation_not_authorized")

    if not gh_user.get("login"):
        await db.delete(pending)
        await db.commit()
        return _frontend_redirect(frontend_url, "error", "authorization_failed")

    existing_result = await db.execute(
        select(GitHubConnection).where(
            GitHubConnection.user_id == pending.user_id,
            GitHubConnection.github_account_login == account["login"],
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        existing.github_account_type = account.get("type", "User")
        existing.github_app_installation_id = pending.installation_id
        existing.status = GitHubConnectionStatus.active
    else:
        db.add(
            GitHubConnection(
                user_id=pending.user_id,
                github_account_login=account["login"],
                github_account_type=account.get("type", "User"),
                github_app_installation_id=pending.installation_id,
                status=GitHubConnectionStatus.active,
            )
        )
    await db.delete(pending)
    await db.commit()

    return _frontend_redirect(frontend_url, "connected")


def _hash_state(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def _frontend_redirect(
    frontend_url: str,
    result: str,
    reason: str | None = None,
) -> RedirectResponse:
    params = {"github": result}
    if reason:
        params["reason"] = reason
    return RedirectResponse(
        url=f"{frontend_url}/repositories?{urlencode(params)}",
        status_code=303,
    )


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
    failed_connections = 0

    for conn in connections:
        if not conn.github_app_installation_id:
            failed_connections += 1
            continue
        try:
            install_token = await github.get_installation_token(
                int(conn.github_app_installation_id)
            )
            repos = await github.list_installation_repos(install_token)
        except httpx.HTTPError:
            logger.warning(
                "Unable to list repositories for GitHub installation",
                connection_id=str(conn.id),
            )
            failed_connections += 1
            continue
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

    if connections and failed_connections == len(connections):
        raise ServiceUnavailableError(
            "Unable to load repositories from GitHub. Please try again.",
            service="github",
        )

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
    await db.commit()
