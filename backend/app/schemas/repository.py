from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.repository import RepositoryStatus, RepositoryVisibility
from .common import PaginatedResponse


class RepositoryVersionSchema(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    branch: str
    commit_sha: str
    indexed_at: datetime
    index_version: int

    model_config = {"from_attributes": True}


class RepositorySchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    github_connection_id: uuid.UUID
    owner: str
    name: str
    full_name: str = ""
    github_repo_id: str
    visibility: RepositoryVisibility
    default_branch: str
    selected_branch: str
    description: str | None
    status: RepositoryStatus
    created_at: datetime
    updated_at: datetime
    latest_version: RepositoryVersionSchema | None = None

    model_config = {"from_attributes": True}

    @property
    def full_name_computed(self) -> str:
        return f"{self.owner}/{self.name}"


class AddRepositoryRequest(BaseModel):
    owner: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    branch: str = Field(default="main", min_length=1, max_length=255)
    github_connection_id: uuid.UUID


RepositoryListResponse = PaginatedResponse[RepositorySchema]
