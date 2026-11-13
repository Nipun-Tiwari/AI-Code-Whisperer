from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.index_job import IndexJobMode, IndexJobStatus


class IndexJobSchema(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    version_id: uuid.UUID | None
    mode: IndexJobMode
    status: IndexJobStatus
    stage: str | None
    checkpoint: str | None
    files_total: int | None
    files_processed: int
    files_failed: int
    files_skipped: int
    error_category: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StartIndexJobRequest(BaseModel):
    mode: IndexJobMode = IndexJobMode.full
