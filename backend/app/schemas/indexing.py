from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.index_job import IndexJobMode, IndexJobStatus


class TaskResponse(BaseModel):
    """Generic response for agent workflow tasks."""
    task_id: uuid.UUID
    status: str
    task_type: str
    result: dict[str, Any] | None = None
    tokens_used: int | None = None


class IndexJobCreate(BaseModel):
    mode: IndexJobMode = IndexJobMode.full


class IndexJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    mode: IndexJobMode
    status: IndexJobStatus
    stage: str | None
    files_total: int | None
    files_processed: int
    files_failed: int
    files_skipped: int
    error_category: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class IndexJobStatus_(BaseModel):
    """Lightweight status poll response."""

    id: uuid.UUID
    status: IndexJobStatus
    stage: str | None
    files_total: int | None
    files_processed: int
    files_failed: int
    progress_pct: float | None

    @classmethod
    def from_job(cls, job: "IndexJob") -> "IndexJobStatus_":  # type: ignore[name-defined]
        pct = None
        if job.files_total and job.files_total > 0:
            pct = round(job.files_processed / job.files_total * 100, 1)
        return cls(
            id=job.id,
            status=job.status,
            stage=job.stage,
            files_total=job.files_total,
            files_processed=job.files_processed,
            files_failed=job.files_failed,
            progress_pct=pct,
        )
