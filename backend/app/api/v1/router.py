from __future__ import annotations

from fastapi import APIRouter

from .agent_activity import router as agent_activity_router
from .auth import router as auth_router
from .evaluation import router as evaluation_router
from .chat import router as chat_router
from .documentation import router as documentation_router
from .github import router as github_router
from .index_jobs import router as index_jobs_router
from .investigations import router as investigations_router
from .mcp_tools import router as mcp_tools_router
from .repositories import router as repositories_router
from .security_scan import router as security_scan_router
from .settings import router as settings_router
from .usage import router as usage_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(github_router)
v1_router.include_router(repositories_router)
v1_router.include_router(index_jobs_router)
v1_router.include_router(chat_router)
v1_router.include_router(investigations_router)
v1_router.include_router(security_scan_router)
v1_router.include_router(documentation_router)
v1_router.include_router(agent_activity_router)
v1_router.include_router(mcp_tools_router)
v1_router.include_router(usage_router)
v1_router.include_router(settings_router)
v1_router.include_router(evaluation_router)
