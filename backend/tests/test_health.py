from __future__ import annotations

import pytest


def test_health_endpoint_returns_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_version_endpoint(client) -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "CodeWhisperer"
    assert "version" in data


def test_session_requires_auth(client) -> None:
    response = client.get("/api/v1/auth/session")
    # Must return 401 (no auth header) or 500 if Supabase not configured
    assert response.status_code in (401, 500, 503)


def test_repositories_requires_auth(client) -> None:
    response = client.get("/api/v1/repositories")
    assert response.status_code in (401, 500, 503)
