from __future__ import annotations

"""
CodeWhisperer MCP server using mcp 2.x MCPServer.

Provides read-only repository intelligence tools for agents.
Mounted at /mcp on the FastAPI app via SSE transport.
"""

import time
from typing import Any

import structlog
from mcp.server.mcpserver import MCPServer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory
from app.models import CodeChunk, FileRecord, Repository, SymbolRecord

logger = structlog.get_logger(__name__)

_MAX_RESPONSE_BYTES = 50 * 1024  # 50KB

mcp_server = MCPServer(
    name="CodeWhisperer",
    title="CodeWhisperer Repository Tools",
    description="Read-only repository intelligence tools: structure, search, file content, symbols, commits.",
    version="0.1.0",
)


async def _get_db() -> AsyncSession:
    factory = get_session_factory()
    return factory()


def _truncate(data: Any, max_bytes: int = _MAX_RESPONSE_BYTES) -> Any:
    """Truncate list responses to stay within size limits."""
    if isinstance(data, list):
        import json
        while data and len(json.dumps(data).encode()) > max_bytes:
            data = data[: len(data) // 2]
    return data


@mcp_server.tool()
async def get_repository_structure(repository_id: str, path: str = "") -> dict:
    """Get the directory and file structure of an indexed repository.

    Args:
        repository_id: UUID of the repository
        path: Optional path prefix to filter results (e.g. "src/")
    """
    start = time.monotonic()
    async with await _get_db() as db:
        try:
            stmt = select(FileRecord).where(
                FileRecord.repository_id == repository_id  # type: ignore[arg-type]
            )
            if path:
                stmt = stmt.where(FileRecord.path.like(f"{path}%"))  # type: ignore[union-attr]

            result = await db.execute(stmt.limit(500))
            files = result.scalars().all()

            # Build tree structure
            tree: dict[str, Any] = {}
            for f in files:
                parts = f.path.replace("\\", "/").split("/")
                node = tree
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = {
                    "type": "file",
                    "language": f.language,
                    "size_bytes": f.size_bytes,
                    "parse_status": f.parse_status.value if f.parse_status else None,
                }

            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("mcp_tool_call", tool="get_repository_structure", duration_ms=duration_ms, success=True)
            return {"repository_id": repository_id, "path": path, "tree": tree, "file_count": len(files)}

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("mcp_tool_call", tool="get_repository_structure", duration_ms=duration_ms, success=False, error=str(exc))
            return {"error": str(exc), "repository_id": repository_id}


@mcp_server.tool()
async def search_code(
    repository_id: str,
    query: str,
    language: str = "",
    top_k: int = 10,
) -> list[dict]:
    """Search for code using semantic + lexical hybrid search.

    Args:
        repository_id: UUID of the repository
        query: Natural language or keyword search query
        language: Optional language filter (e.g. "python", "typescript")
        top_k: Maximum number of results to return (max 20)
    """
    from app.retrieval.service import RetrievalService

    start = time.monotonic()
    top_k = min(top_k, 20)

    async with await _get_db() as db:
        try:
            retrieval = RetrievalService(db)
            filters = {"language": language} if language else None
            items = await retrieval.search(
                query=query,
                repository_id=repository_id,
                top_k=top_k,
                filters=filters,
            )
            results = [
                {
                    "file_path": item.file_path,
                    "line_start": item.line_start,
                    "line_end": item.line_end,
                    "symbol_name": item.symbol_name,
                    "language": item.language,
                    "text": item.text[:400],
                    "score": round(item.score, 4),
                    "retrieval_method": item.retrieval_method,
                }
                for item in items
            ]
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("mcp_tool_call", tool="search_code", duration_ms=duration_ms, success=True, count=len(results))
            return _truncate(results)

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("mcp_tool_call", tool="search_code", duration_ms=duration_ms, success=False, error=str(exc))
            return [{"error": str(exc)}]


@mcp_server.tool()
async def get_file_content(repository_id: str, file_path: str) -> dict:
    """Get the indexed content of a specific file from the repository.

    Args:
        repository_id: UUID of the repository
        file_path: Path to the file within the repository
    """
    start = time.monotonic()
    async with await _get_db() as db:
        try:
            # Find file record
            fr_result = await db.execute(
                select(FileRecord).where(
                    FileRecord.repository_id == repository_id,  # type: ignore[arg-type]
                    FileRecord.path == file_path,
                )
            )
            file_record = fr_result.scalar_one_or_none()
            if not file_record:
                return {"error": f"File not found: {file_path}", "repository_id": repository_id}

            # Get chunks for this file
            chunks_result = await db.execute(
                select(CodeChunk)
                .where(CodeChunk.file_id == file_record.id)
                .order_by(CodeChunk.line_start)
                .limit(50)
            )
            chunks = chunks_result.scalars().all()

            # Reconstruct content from chunks
            content_parts = [chunk.content or "" for chunk in chunks if chunk.content]
            content = "\n".join(content_parts)

            if len(content.encode()) > _MAX_RESPONSE_BYTES:
                content = content[:_MAX_RESPONSE_BYTES // 2] + "\n…[truncated]"

            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("mcp_tool_call", tool="get_file_content", duration_ms=duration_ms, success=True)
            return {
                "file_path": file_path,
                "language": file_record.language,
                "size_bytes": file_record.size_bytes,
                "parse_status": file_record.parse_status.value if file_record.parse_status else None,
                "content": content,
                "chunk_count": len(chunks),
            }

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("mcp_tool_call", tool="get_file_content", duration_ms=duration_ms, success=False, error=str(exc))
            return {"error": str(exc), "file_path": file_path}


@mcp_server.tool()
async def get_symbols(
    repository_id: str,
    file_path: str = "",
    symbol_kind: str = "",
) -> list[dict]:
    """Get extracted code symbols (functions, classes, methods) from repository files.

    Args:
        repository_id: UUID of the repository
        file_path: Optional file path filter
        symbol_kind: Optional symbol kind filter (function, class, method, import)
    """
    start = time.monotonic()
    async with await _get_db() as db:
        try:
            stmt = (
                select(SymbolRecord, FileRecord)
                .join(FileRecord, SymbolRecord.file_id == FileRecord.id)
                .where(FileRecord.repository_id == repository_id)  # type: ignore[arg-type]
            )
            if file_path:
                stmt = stmt.where(FileRecord.path == file_path)
            if symbol_kind:
                stmt = stmt.where(SymbolRecord.symbol_kind == symbol_kind)  # type: ignore[arg-type]

            result = await db.execute(stmt.limit(200))
            rows = result.all()

            symbols = [
                {
                    "name": sym.name,
                    "qualified_name": sym.qualified_name,
                    "kind": sym.symbol_kind.value if sym.symbol_kind else None,
                    "file_path": fr.path,
                    "line_start": sym.line_start,
                    "line_end": sym.line_end,
                }
                for sym, fr in rows
            ]

            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("mcp_tool_call", tool="get_symbols", duration_ms=duration_ms, success=True, count=len(symbols))
            return _truncate(symbols)

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("mcp_tool_call", tool="get_symbols", duration_ms=duration_ms, success=False, error=str(exc))
            return [{"error": str(exc)}]


@mcp_server.tool()
async def get_commit_history(
    repository_id: str,
    file_path: str = "",
    limit: int = 10,
) -> list[dict]:
    """Get recent commit history for a repository or specific file.

    Note: Returns available metadata from the index; full Git history requires GitHub API access.

    Args:
        repository_id: UUID of the repository
        file_path: Optional file path to get file-specific history
        limit: Maximum number of commits to return (max 20)
    """
    from app.models import RepositoryVersion

    start = time.monotonic()
    limit = min(limit, 20)

    async with await _get_db() as db:
        try:
            # Get indexed versions/commits for this repository
            stmt = (
                select(RepositoryVersion)
                .where(RepositoryVersion.repository_id == repository_id)  # type: ignore[arg-type]
                .order_by(RepositoryVersion.indexed_at.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            versions = result.scalars().all()

            commits = [
                {
                    "commit_sha": v.commit_sha,
                    "branch": v.branch,
                    "indexed_at": v.indexed_at.isoformat() if v.indexed_at else None,
                    "index_version": v.index_version,
                }
                for v in versions
            ]

            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info("mcp_tool_call", tool="get_commit_history", duration_ms=duration_ms, success=True)
            return commits

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("mcp_tool_call", tool="get_commit_history", duration_ms=duration_ms, success=False, error=str(exc))
            return [{"error": str(exc)}]
