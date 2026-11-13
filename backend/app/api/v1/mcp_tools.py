from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.dependencies import DbDep, UserDep
from app.models import MCPToolCall

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPToolInfo(BaseModel):
    name: str
    description: str
    required_permission: str


class MCPToolCallRecord(BaseModel):
    tool_name: str
    success: bool
    duration_ms: int | None
    error_category: str | None
    created_at: str

    class Config:
        from_attributes = True


_AVAILABLE_TOOLS: list[MCPToolInfo] = [
    MCPToolInfo(
        name="get_repository_structure",
        description="Get directory and file structure of an indexed repository.",
        required_permission="repository:read",
    ),
    MCPToolInfo(
        name="search_code",
        description="Search for code using semantic + lexical hybrid search.",
        required_permission="repository:read",
    ),
    MCPToolInfo(
        name="get_file_content",
        description="Get the indexed content of a specific file.",
        required_permission="repository:read",
    ),
    MCPToolInfo(
        name="get_symbols",
        description="Get extracted code symbols (functions, classes, methods).",
        required_permission="repository:read",
    ),
    MCPToolInfo(
        name="get_commit_history",
        description="Get indexed commit/version history for a repository.",
        required_permission="repository:read",
    ),
]


@router.get("/tools", response_model=list[MCPToolInfo])
async def list_mcp_tools(current_user: UserDep) -> list[MCPToolInfo]:
    """List available MCP tools and their required permissions."""
    return _AVAILABLE_TOOLS


@router.get("/tool-calls", response_model=list[MCPToolCallRecord])
async def get_mcp_tool_calls(
    current_user: UserDep,
    db: DbDep,
) -> list[MCPToolCallRecord]:
    """Get recent MCP tool call history for the current user."""
    result = await db.execute(
        select(MCPToolCall)
        .where(MCPToolCall.user_id == current_user.id)
        .order_by(MCPToolCall.created_at.desc())
        .limit(50)
    )
    calls = result.scalars().all()
    return [
        MCPToolCallRecord(
            tool_name=c.tool_name,
            success=c.success,
            duration_ms=c.duration_ms,
            error_category=c.error_category,
            created_at=c.created_at.isoformat() if c.created_at else "",
        )
        for c in calls
    ]
