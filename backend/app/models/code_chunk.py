from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Text content (for small chunks) or object storage key (for large chunks)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Qdrant point ID for vector lookup
    qdrant_point_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Embedding model/version that produced the vector
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
