"""
GitHub App client stub.

Full implementation will be added in Phase 1 completion (after GitHub App credentials
are provided). This module exposes the interface that the rest of the application will
use, so imports won't break.
"""
from __future__ import annotations

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class GitHubAppClient:
    """
    Thin wrapper around GitHub App authentication.

    TODO (Phase 1): implement JWT generation, installation token exchange,
    and authorized GitHub API requests using the private key from settings.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return self._settings.github_configured

    def get_installation_access_token(self, installation_id: str) -> str:
        """
        Exchange a GitHub App installation ID for a short-lived access token.

        TODO: implement using PyJWT + httpx GitHub API call.
        Raises NotImplementedError until credentials are configured.
        """
        if not self.is_configured:
            raise RuntimeError(
                "GitHub App credentials are not configured. "
                "Set GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY in your .env file."
            )
        raise NotImplementedError("GitHub App token exchange not yet implemented.")

    def get_app_installation_url(self) -> str:
        """Return the GitHub App installation URL for new users."""
        if not self._settings.github_app_name:
            return "https://github.com/apps/"
        return f"https://github.com/apps/{self._settings.github_app_name}/installations/new"


_client: GitHubAppClient | None = None


def get_github_app_client() -> GitHubAppClient:
    global _client
    if _client is None:
        _client = GitHubAppClient()
    return _client
