from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Attaches a correlation ID to every request and logs request/response metadata.
    Does not log Authorization headers or body content.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        start = time.monotonic()
        response: Response = await call_next(request)  # type: ignore[operator]
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

        response.headers["x-correlation-id"] = correlation_id
        return response
