from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Point at a non-existent DB for unit tests that don't need the DB
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_cw")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci-only")
os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c
