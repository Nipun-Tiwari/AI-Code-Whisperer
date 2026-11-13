from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RepositoryVisibility(str, enum.Enum):
    public = "public"
    private = "private"


class RepositoryStatus(str, enum.Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"
    stale = "stale"
    removed = "removed"


class Repository(Base):
    __tablename__ = "repositories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    github_connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("github_connections.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # GitHub's numeric repository ID as a string for portability
    github_repo_id: Mapped[str] = mapped_column(String(64), nullable=False)
    visibility: Mapped[RepositoryVisibility] = mapped_column(
        Enum(RepositoryVisibility, name="repository_visibility"),
        nullable=False,
        default=RepositoryVisibility.private,
    )
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    selected_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RepositoryStatus] = mapped_column(
        Enum(RepositoryStatus, name="repository_status"),
        nullable=False,
        default=RepositoryStatus.pending,
    )
