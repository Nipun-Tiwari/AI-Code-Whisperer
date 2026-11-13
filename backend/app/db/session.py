from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _make_asyncpg_url(raw_url: str) -> str:
    """
    Normalise a Neon connection string for asyncpg:
    - Ensure scheme is postgresql+asyncpg://
    - Strip sslmode, ssl, and channel_binding query params (asyncpg ignores them
      and channel_binding causes a connection error with asyncpg).
    SSL is applied via connect_args instead.
    """
    url = re.sub(r"^postgresql://", "postgresql+asyncpg://", raw_url)
    url = re.sub(r"[?&](sslmode|ssl|channel_binding)=[^&]*", "", url)
    url = re.sub(r"[?&]$", "", url)
    return url


def get_engine():  # type: ignore[return]
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not configured. Set it in your .env file."
            )
        db_url = _make_asyncpg_url(settings.database_url)
        _engine = create_async_engine(
            db_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"ssl": "require"},
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
