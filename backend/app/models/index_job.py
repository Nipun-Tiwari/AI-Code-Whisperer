from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class IndexJobMode(str, enum.Enum):
    full = "full"
    incremental = "incremental"


class IndexJobStatus(str, enum.Enum):
    queued = "queued"
    fetching = "fetching"
    classifying = "classifying"
    parsing = "parsing"
    summarizing = "summarizing"
    embedding = "embedding"
    persisting = "persisting"
    completed = "completed"
    partial = "partial"
    failed = "failed"
    paused = "paused"


class IndexJob(Base):
    __tablename__ = "index_jobs"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[IndexJobMode] = mapped_column(
        Enum(IndexJobMode, name="index_job_mode"),
        nullable=False,
        default=IndexJobMode.full,
    )
    status: Mapped[IndexJobStatus] = mapped_column(
        Enum(IndexJobStatus, name="index_job_status"),
        nullable=False,
        default=IndexJobStatus.queued,
        index=True,
    )
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checkpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    files_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
