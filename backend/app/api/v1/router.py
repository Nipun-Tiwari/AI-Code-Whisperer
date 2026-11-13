from __future__ import annotations

from fastapi import APIRouter

from .auth import router as auth_router
from .github import router as github_router
from .index_jobs import router as index_jobs_router
from .repositories import router as repositories_router
from .settings import router as settings_router
from .usage import router as usage_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(github_router)
v1_router.include_router(repositories_router)
v1_router.include_router(index_jobs_router)
v1_router.include_router(usage_router)
v1_router.include_router(settings_router)
