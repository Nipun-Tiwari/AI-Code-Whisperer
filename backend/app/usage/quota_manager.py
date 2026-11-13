from __future__ import annotations

from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import QuotaSnapshot

logger = structlog.get_logger(__name__)

# In-memory cache: service_key -> expiry of the exhaustion block
# A service is considered blocked until this timestamp passes.
_exhausted_until: dict[str, datetime] = {}

# Default block duration when no reset time is known
_DEFAULT_BLOCK_MINUTES = 60


class QuotaManager:
    """
    Tracks service quota exhaustion in-memory (fast path) and in DB (persistence).

    Usage: call check_service_available() before expensive provider operations.
    On quota error from the provider, call record_quota_exhaustion().
    """

    async def check_service_available(self, service_key: str) -> bool:
        """Return False if the service is currently blocked due to quota exhaustion."""
        blocked_until = _exhausted_until.get(service_key)
        if blocked_until and datetime.now(timezone.utc) < blocked_until:
            return False
        # Clear expired in-memory block
        if blocked_until:
            del _exhausted_until[service_key]
        return True

    async def is_exhausted(self, service_key: str) -> bool:
        return not await self.check_service_available(service_key)

    async def record_quota_exhaustion(
        self,
        db: AsyncSession,
        service_key: str,
        error_msg: str,
        reset_at: datetime | None = None,
    ) -> None:
        """Record that a service quota is exhausted. Blocks further requests until reset."""
        now = datetime.now(timezone.utc)
        block_until = reset_at or (now + timedelta(minutes=_DEFAULT_BLOCK_MINUTES))
        _exhausted_until[service_key] = block_until

        snapshot = QuotaSnapshot(
            service_key=service_key,
            status="quota_exhausted",
            source_type="codewhisperer_tracked",
            freshness="current",
            reset_at=reset_at,
            measured_at=now,
        )
        db.add(snapshot)
        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.warning("Failed to persist quota exhaustion snapshot", service=service_key, error=str(exc))

        logger.warning(
            "Service quota exhausted",
            service=service_key,
            blocked_until=block_until.isoformat(),
            error=error_msg,
        )

    async def record_rate_limit(
        self,
        db: AsyncSession,
        service_key: str,
        retry_after: int | None,
    ) -> None:
        """Record a temporary rate limit (not full exhaustion)."""
        now = datetime.now(timezone.utc)
        # For temporary rate limits, block for retry_after seconds (or 60s default)
        block_seconds = retry_after if retry_after and retry_after > 0 else 60
        block_until = now + timedelta(seconds=block_seconds)
        _exhausted_until[service_key] = block_until

        snapshot = QuotaSnapshot(
            service_key=service_key,
            status="rate_limited",
            source_type="codewhisperer_tracked",
            freshness="current",
            measured_at=now,
        )
        db.add(snapshot)
        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.warning("Failed to persist rate limit snapshot", service=service_key, error=str(exc))

        logger.info("Service rate limited", service=service_key, retry_after_seconds=block_seconds)

    async def clear_exhaustion(self, db: AsyncSession, service_key: str) -> None:
        """Manually clear a quota block (e.g. after user retry)."""
        _exhausted_until.pop(service_key, None)

        # Update the latest snapshot status to unknown (no longer confirmed exhausted)
        result = await db.execute(
            select(QuotaSnapshot)
            .where(QuotaSnapshot.service_key == service_key)
            .order_by(QuotaSnapshot.measured_at.desc())
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot and snapshot.status in ("quota_exhausted", "rate_limited"):
            snapshot.status = "unknown"
            snapshot.freshness = "stale"
            try:
                await db.commit()
            except Exception:
                await db.rollback()

        logger.info("Cleared quota block", service=service_key)


_quota_manager = QuotaManager()


def get_quota_manager() -> QuotaManager:
    return _quota_manager
