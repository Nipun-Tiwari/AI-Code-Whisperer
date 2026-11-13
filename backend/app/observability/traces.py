from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

_MAX_EXCERPT_CHARS = 200


class TaskTrace:
    """In-memory trace accumulator for a single agent task execution.

    Traces are accumulated during execution and persisted at the end.
    Sensitive data (source code > 200 chars, keys, tokens) is never logged.
    """

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self._events: list[dict[str, Any]] = []
        self._start_time = time.monotonic()

    def _elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start_time) * 1000)

    def _safe_excerpt(self, text: str) -> str:
        """Truncate text to prevent leaking large source code in traces."""
        if len(text) > _MAX_EXCERPT_CHARS:
            return text[:_MAX_EXCERPT_CHARS] + "…[truncated]"
        return text

    def record_step(
        self,
        agent: str,
        action: str,
        duration_ms: int,
        outcome: str,
        tokens: int = 0,
    ) -> None:
        self._events.append({
            "event_type": "agent_step",
            "task_id": self.task_id,
            "agent": agent,
            "action": action,
            "duration_ms": duration_ms,
            "outcome": outcome,
            "tokens": tokens,
            "elapsed_ms": self._elapsed_ms(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_tool_call(
        self,
        tool: str,
        args_summary: dict,
        duration_ms: int,
        success: bool,
    ) -> None:
        # Mask any value that looks like a secret
        safe_args = {
            k: "[masked]" if any(s in k.lower() for s in ("key", "token", "secret", "password")) else v
            for k, v in args_summary.items()
        }
        self._events.append({
            "event_type": "tool_call",
            "task_id": self.task_id,
            "tool": tool,
            "args_summary": safe_args,
            "duration_ms": duration_ms,
            "success": success,
            "elapsed_ms": self._elapsed_ms(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_retrieval(
        self,
        query: str,
        chunks_returned: int,
        duration_ms: int,
    ) -> None:
        self._events.append({
            "event_type": "retrieval",
            "task_id": self.task_id,
            "query": self._safe_excerpt(query),
            "chunks_returned": chunks_returned,
            "duration_ms": duration_ms,
            "elapsed_ms": self._elapsed_ms(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_trace(self) -> list[dict[str, Any]]:
        return list(self._events)

    async def persist(self, db: AsyncSession) -> None:
        """Persist trace events to the database (future: structured trace table)."""
        # For now, log structured events — a dedicated trace table is a Phase 4 addition
        for event in self._events:
            logger.info("task_trace_event", **{k: v for k, v in event.items() if k != "task_id"}, task_id=self.task_id)
