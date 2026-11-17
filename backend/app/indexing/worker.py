from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory
from app.indexing.pipeline import IndexingPipeline
from app.models import IndexJob, IndexJobStatus

logger = structlog.get_logger(__name__)

_POLL_INTERVAL = 5  # seconds
_PAUSE_COOLDOWN = timedelta(minutes=15)


async def claim_next_job(db: AsyncSession) -> IndexJob | None:
    """Atomically claim the oldest queued job, or requeue a cooled-down paused job."""
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

    # Daily/hard quota pauses: reclaim after cooldown so resume can continue.
    cutoff = datetime.now(timezone.utc) - _PAUSE_COOLDOWN
    paused_result = await db.execute(
        select(IndexJob)
        .where(IndexJob.status == IndexJobStatus.paused)
        .where(IndexJob.error_category == "quota_exhausted")
        .where(IndexJob.completed_at.is_not(None))
        .where(IndexJob.completed_at <= cutoff)
        .order_by(IndexJob.completed_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    paused = paused_result.scalar_one_or_none()
    if paused:
        logger.info(
            "Requeueing paused quota_exhausted job after cooldown",
            job_id=str(paused.id),
            paused_at=str(paused.completed_at),
        )
        paused.status = IndexJobStatus.queued
        paused.completed_at = None
        await db.flush()
        paused.status = IndexJobStatus.fetching
        await db.commit()
        return paused

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
