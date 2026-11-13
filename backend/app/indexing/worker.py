from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory
from app.indexing.pipeline import IndexingPipeline
from app.models import IndexJob, IndexJobStatus

logger = structlog.get_logger(__name__)

_POLL_INTERVAL = 5  # seconds


async def claim_next_job(db: AsyncSession) -> IndexJob | None:
    """Atomically claim the oldest queued job using SELECT FOR UPDATE SKIP LOCKED."""
    result = await db.execute(
        select(IndexJob)
        .where(IndexJob.status == IndexJobStatus.queued)
        .order_by(IndexJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = result.scalar_one_or_none()
    if job:
        job.status = IndexJobStatus.fetching
        await db.commit()
        return job
    return None


async def run_worker() -> None:
    """Poll for queued IndexJobs and process them one at a time."""
    logger.info("Indexing worker started")
    factory = get_session_factory()

    while True:
        try:
            async with factory() as db:
                job = await claim_next_job(db)

            if job:
                logger.info("Processing job", job_id=str(job.id))
                pipeline = IndexingPipeline(job_id=str(job.id))
                await pipeline.run()
            else:
                await asyncio.sleep(_POLL_INTERVAL)

        except asyncio.CancelledError:
            logger.info("Worker shutting down")
            return
        except Exception as exc:
            logger.error("Worker loop error", error=str(exc), exc_info=True)
            await asyncio.sleep(10)
