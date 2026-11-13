from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base  # noqa: F401 — imports all models to populate metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    import re
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Configure it in .env before running migrations.")
    # asyncpg requires postgresql+asyncpg:// and no sslmode/channel_binding params
    url = re.sub(r"^postgresql://", "postgresql+asyncpg://", url)
    url = re.sub(r"[?&](sslmode|ssl|channel_binding)=[^&]*", "", url)
    url = re.sub(r"[?&]$", "", url)
    return url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_url(), connect_args={"ssl": "require"})
    async with engine.connect() as conn:
        await conn.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
