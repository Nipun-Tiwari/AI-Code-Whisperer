"""
GitHub App integration endpoints.

OAuth/installation flow stubs — full implementation requires GitHub App credentials.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.auth.github_app import get_github_app_client
from app.exceptions import NotImplementedFeatureError

router = APIRouter(prefix="/integrations/github", tags=["github"])


@router.get("/install-url")
async def get_install_url() -> dict[str, str]:
    """Return the GitHub App installation URL for the connected app."""
    client = get_github_app_client()
    return {"installation_url": client.get_app_installation_url()}


@router.post("/connect")
async def start_github_connection() -> None:
    """
    Start the GitHub App authorization flow.

    TODO: implement after GitHub App credentials are configured.
    Returns the GitHub authorization URL to redirect the user to.
    """
    raise NotImplementedFeatureError(
        "GitHub App authorization flow is not yet implemented. "
        "Configure GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY to enable this endpoint."
    )


@router.get("/callback")
async def github_callback() -> None:
    """
    Handle the GitHub App installation callback.

    TODO: implement after GitHub App credentials are configured.
    Validates state parameter and stores the installation token reference.
    """
    raise NotImplementedFeatureError(
        "GitHub App callback handler is not yet implemented."
    )


@router.get("")
async def list_github_connections() -> dict[str, list]:
    """
    List GitHub App connections for the authenticated user.

    TODO: query GitHubConnection table once auth is wired up.
    """
    return {"connections": []}


@router.delete("/{connection_id}")
async def disconnect_github(connection_id: str) -> None:
    """
    Disconnect and remove a GitHub App installation.

    TODO: implement revocation and credential cleanup.
    """
    raise NotImplementedFeatureError(
        "GitHub disconnection is not yet implemented."
    )
