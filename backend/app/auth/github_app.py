from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from jose import jwt

from app.config import get_settings

logger = structlog.get_logger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubAppClient:
    """GitHub App authentication and API access."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _private_key(self) -> str:
        """Return PEM key with literal \\n replaced by real newlines."""
        return self._settings.github_app_private_key.replace("\\n", "\n")

    def generate_jwt(self) -> str:
        """Generate a short-lived RS256 JWT for GitHub App authentication."""
        now = int(time.time())
        payload = {
            "iat": now - 60,   # issued 60s ago to allow clock skew
            "exp": now + 540,  # 9 minutes (max 10)
            "iss": self._settings.github_app_id,
        }
        return jwt.encode(payload, self._private_key(), algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> str:
        """Exchange an installation ID for a short-lived installation access token."""
        app_jwt = self.generate_jwt()
        url = f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            resp.raise_for_status()
            return resp.json()["token"]

    async def get_user_installations(self, user_token: str) -> list[dict[str, Any]]:
        """List GitHub App installations accessible to a user OAuth token."""
        url = f"{GITHUB_API}/user/installations"
        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            page = 1
            while True:
                resp = await client.get(
                    url,
                    params={"per_page": 100, "page": page},
                    headers=_user_headers(user_token),
                )
                resp.raise_for_status()
                data = resp.json()
                installations = data.get("installations", [])
                results.extend(installations)
                if len(installations) < 100:
                    break
                page += 1
        return results

    async def list_installation_repos(self, installation_token: str) -> list[dict[str, Any]]:
        """List repositories accessible to an installation token."""
        url = f"{GITHUB_API}/installation/repositories"
        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            page = 1
            while True:
                resp = await client.get(
                    url,
                    params={"per_page": 100, "page": page},
                    headers=_install_headers(installation_token),
                )
                resp.raise_for_status()
                data = resp.json()
                repos = data.get("repositories", [])
                results.extend(repos)
                if len(repos) < 100:
                    break
                page += 1
        return results

    async def get_repo_tree(
        self, owner: str, repo: str, ref: str, token: str
    ) -> list[dict[str, Any]]:
        """Fetch the recursive tree for a ref. Returns flat list of tree entries."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{ref}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                params={"recursive": "1"},
                headers=_install_headers(token),
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("tree", [])

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str, token: str
    ) -> bytes:
        """Fetch raw file content bytes."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                params={"ref": ref},
                headers={**_install_headers(token), "Accept": "application/vnd.github.raw+json"},
            )
            resp.raise_for_status()
            return resp.content

    async def get_commits(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
        token: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent commits touching a file path."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url,
                params={"path": path, "sha": ref, "per_page": limit},
                headers=_install_headers(token),
            )
            resp.raise_for_status()
            return resp.json()

    async def get_default_branch(self, owner: str, repo: str, token: str) -> str:
        """Return the default branch name for a repository."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_install_headers(token))
            resp.raise_for_status()
            return resp.json().get("default_branch", "main")

    async def get_repo_info(self, owner: str, repo: str, token: str) -> dict[str, Any]:
        """Return full repository metadata."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_install_headers(token))
            resp.raise_for_status()
            return resp.json()

    async def list_branches(self, owner: str, repo: str, token: str) -> list[str]:
        """List branch names for a repository."""
        url = f"{GITHUB_API}/repos/{owner}/{repo}/branches"
        results: list[str] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            page = 1
            while True:
                resp = await client.get(
                    url,
                    params={"per_page": 100, "page": page},
                    headers=_install_headers(token),
                )
                resp.raise_for_status()
                branches = resp.json()
                results.extend(b["name"] for b in branches)
                if len(branches) < 100:
                    break
                page += 1
        return results

    async def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
    ) -> dict[str, Any]:
        """Exchange OAuth code for user access token."""
        payload = {
            "client_id": self._settings.github_app_client_id,
            "client_secret": self._settings.github_app_client_secret,
            "code": code,
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data=payload,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_authenticated_user(self, user_token: str) -> dict[str, Any]:
        """Return the authenticated user's GitHub profile."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITHUB_API}/user",
                headers=_user_headers(user_token),
            )
            resp.raise_for_status()
            return resp.json()


def _install_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _user_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


# Module-level singleton
_client: GitHubAppClient | None = None


def get_github_client() -> GitHubAppClient:
    global _client
    if _client is None:
        _client = GitHubAppClient()
    return _client
