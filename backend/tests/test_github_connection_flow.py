from __future__ import annotations

import base64
import hashlib
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import Request

from app.api.v1 import github as github_api
from app.auth import github_app
from app.config import Settings
from app.models import GitHubConnection, GitHubInstallState, User


class FakeResult:
    def __init__(self, value=None) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self) -> None:
        self.state: GitHubInstallState | None = None
        self.connections: list[GitHubConnection] = []

    async def execute(self, statement):
        if getattr(statement, "column_descriptions", None):
            entity = statement.column_descriptions[0]["entity"]
            if entity is GitHubInstallState:
                expected_hash = next(
                    value
                    for key, value in statement.compile().params.items()
                    if "state_hash" in key
                )
                if self.state and self.state.state_hash == expected_hash:
                    return FakeResult(self.state)
                return FakeResult()
            if entity is GitHubConnection:
                return FakeResult(None)
        return FakeResult()

    def add(self, instance) -> None:
        if isinstance(instance, GitHubInstallState):
            self.state = instance
        elif isinstance(instance, GitHubConnection):
            self.connections.append(instance)

    async def delete(self, instance) -> None:
        if instance is self.state:
            self.state = None

    async def commit(self) -> None:
        return None


class FakeGitHubClient:
    def __init__(self, installations: list[dict]) -> None:
        self.installations = installations
        self.code_verifier: str | None = None
        self.redirect_uri: str | None = None

    async def exchange_code_for_token(
        self, code: str, code_verifier: str, redirect_uri: str
    ):
        self.code_verifier = code_verifier
        self.redirect_uri = redirect_uri
        return {"access_token": "temporary-user-token"}

    async def get_authenticated_user(self, access_token: str):
        return {"login": "alice"}

    async def get_user_installations(self, access_token: str):
        return self.installations


class FakeTokenResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"access_token": "temporary-user-token"}


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("localhost", 8000),
            "client": ("localhost", 50000),
            "root_path": "",
            "path": "/api/v1/integrations/github/callback",
            "query_string": b"",
            "headers": [],
        }
    )


def _configure(monkeypatch, github_client: FakeGitHubClient) -> None:
    settings = Settings(
        github_app_id="app-id",
        github_app_name="codewhisperer",
        github_app_client_id="client-id",
        github_app_client_secret="client-secret",
        github_app_private_key="unused-test-key",
        github_app_callback_url="http://localhost:8000/api/v1/integrations/github/callback",
        allowed_origins=["http://localhost:5173"],
    )
    monkeypatch.setattr(github_api, "get_settings", lambda: settings)
    monkeypatch.setattr(github_api, "get_github_client", lambda: github_client)


async def _start_and_install(monkeypatch, db: FakeSession, client: FakeGitHubClient):
    _configure(monkeypatch, client)
    user = User(
        id=uuid.uuid4(),
        supabase_user_id=str(uuid.uuid4()),
        email="alice@example.com",
    )
    result = await github_api.start_github_connection(current_user=user, db=db)
    installation_state = parse_qs(urlparse(result["install_url"]).query)["state"][0]

    setup_response = await github_api.github_callback(
        request=_request(),
        db=db,
        code=None,
        installation_id="123",
        setup_action=None,
        state=installation_state,
        error=None,
    )
    assert setup_response.headers["location"].startswith(
        "https://github.com/login/oauth/authorize?"
    ), setup_response.headers["location"]
    authorization_query = parse_qs(urlparse(setup_response.headers["location"]).query)
    oauth_state = authorization_query["state"][0]

    return user, oauth_state, authorization_query


@pytest.mark.asyncio
async def test_installation_callback_authorizes_and_persists_verified_installation(monkeypatch):
    db = FakeSession()
    github = FakeGitHubClient(
        [{"id": 123, "account": {"login": "alice", "type": "User"}}]
    )
    user, oauth_state, authorization_query = await _start_and_install(
        monkeypatch, db, github
    )

    verifier = db.state.code_verifier
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert authorization_query["code_challenge"] == [expected_challenge]
    assert authorization_query["code_challenge_method"] == ["S256"]

    response = await github_api.github_callback(
        request=_request(),
        db=db,
        code="single-use-code",
        installation_id=None,
        setup_action=None,
        state=oauth_state,
        error=None,
    )

    connection = db.connections[0]
    assert "github=connected" in response.headers["location"]
    assert connection.user_id == user.id
    assert connection.github_account_login == "alice"
    assert connection.github_app_installation_id == "123"
    assert not hasattr(connection, "access_token")
    assert github.code_verifier == verifier
    assert github.redirect_uri == "http://localhost:8000/api/v1/integrations/github/callback"
    assert db.state is None

    replay_response = await github_api.github_callback(
        request=_request(),
        db=db,
        code="single-use-code",
        installation_id=None,
        setup_action=None,
        state=oauth_state,
        error=None,
    )
    assert "reason=expired_state" in replay_response.headers["location"]


@pytest.mark.asyncio
async def test_installation_is_not_saved_unless_github_user_can_access_it(monkeypatch):
    db = FakeSession()
    github = FakeGitHubClient(
        [{"id": 456, "account": {"login": "mallory", "type": "User"}}]
    )
    _, oauth_state, _ = await _start_and_install(monkeypatch, db, github)

    response = await github_api.github_callback(
        request=_request(),
        db=db,
        code="single-use-code",
        installation_id=None,
        setup_action=None,
        state=oauth_state,
        error=None,
    )

    assert "reason=installation_not_authorized" in response.headers["location"]
    assert db.connections == []
    assert db.state is None


@pytest.mark.asyncio
async def test_callback_rejects_state_not_issued_by_authenticated_connect(monkeypatch):
    db = FakeSession()
    github = FakeGitHubClient([])
    _configure(monkeypatch, github)
    user = User(
        id=uuid.uuid4(),
        supabase_user_id=str(uuid.uuid4()),
        email="alice@example.com",
    )
    await github_api.start_github_connection(current_user=user, db=db)

    response = await github_api.github_callback(
        request=_request(),
        db=db,
        code=None,
        installation_id="123",
        setup_action="install",
        state="forged-state",
        error=None,
    )

    assert "reason=expired_state" in response.headers["location"]
    assert db.state is not None
    assert db.connections == []


@pytest.mark.asyncio
async def test_token_exchange_sends_pkce_and_redirect_uri(monkeypatch):
    request_data: dict[str, str] = {}

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def post(self, url: str, data: dict[str, str], headers: dict[str, str]):
            request_data.update(data)
            return FakeTokenResponse()

    monkeypatch.setattr(github_app.httpx, "AsyncClient", FakeAsyncClient)
    client = github_app.GitHubAppClient()
    client._settings = Settings(
        github_app_client_id="client-id",
        github_app_client_secret="client-secret",
    )

    await client.exchange_code_for_token(
        "single-use-code",
        "pkce-verifier",
        "https://api.example.com/api/v1/integrations/github/callback",
    )

    assert request_data == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "code": "single-use-code",
        "code_verifier": "pkce-verifier",
        "redirect_uri": "https://api.example.com/api/v1/integrations/github/callback",
    }
