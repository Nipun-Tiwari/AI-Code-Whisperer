from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog.stdlib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import v1_router
from app.config import get_settings
from app.db.session import dispose_engine
from app.exceptions import AppException
from app.middleware import RequestLoggingMiddleware

structlog.configure(
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer() if get_settings().debug else structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("CodeWhisperer API starting", environment=get_settings().environment)
    yield
    await dispose_engine()
    logger.info("CodeWhisperer API shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-correlation-id"],
    )

    # Request logging (after CORS so preflight OPTIONS are still logged)
    app.add_middleware(RequestLoggingMiddleware)

    # Structured error handler for AppException subclasses
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "service": exc.service,
                    "retryable": exc.retryable,
                    "retry_after": None,
                    "correlation_id": correlation_id,
                }
            },
        )

    # Catch-all for unexpected errors — return JSON instead of plain text
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "")
        logger.error("Unhandled exception", exc_info=exc, path=request.url.path, correlation_id=correlation_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "service": None,
                    "retryable": False,
                    "retry_after": None,
                    "correlation_id": correlation_id,
                }
            },
        )

    # Mount v1 routes
    app.include_router(v1_router)

    # Health check (unauthenticated)
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.1.0"}

    # Version info (unauthenticated)
    @app.get("/api/v1/version", tags=["health"])
    async def version_info() -> dict[str, str]:
        return {
            "version": "0.1.0",
            "app": settings.app_name,
            "environment": settings.environment,
        }

    return app


app = create_app()
