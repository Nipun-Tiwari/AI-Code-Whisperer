from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class QuotaSnapshot(Base):
    __tablename__ = "quota_snapshots"

    service_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # "operational" | "degraded" | "rate_limited" | "quota_exhausted" | "auth_error"
    # | "unavailable" | "usage_unavailable" | "unknown" | "not_configured"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    usage_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    usage_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    limit_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    remaining: Mapped[float | None] = mapped_column(Float, nullable=True)
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # "provider_reported" | "codewhisperer_tracked" | "estimated"
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="codewhisperer_tracked")
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # "current" | "stale" | "unknown"
    freshness: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
