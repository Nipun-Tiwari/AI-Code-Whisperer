from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class GitHubConnectionStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class GitHubConnection(Base):
    __tablename__ = "github_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # GitHub App installation ID (null until installed)
    github_app_installation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    github_account_login: Mapped[str] = mapped_column(String(255), nullable=False)
    # "User" or "Organization"
    github_account_type: Mapped[str] = mapped_column(String(50), nullable=False, default="User")
    # Reference to secret store (not the token itself)
    token_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scopes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[GitHubConnectionStatus] = mapped_column(
        Enum(GitHubConnectionStatus, name="github_connection_status"),
        nullable=False,
        default=GitHubConnectionStatus.active,
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
