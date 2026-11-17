from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SymbolKind(str, enum.Enum):
    cls = "class"
    function = "function"
    method = "method"
    module = "module"
    import_ = "import"


class SymbolRecord(Base):
    __tablename__ = "symbol_records"

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("file_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_kind: Mapped[SymbolKind] = mapped_column(
        Enum(
            SymbolKind,
            name="symbol_kind",
            # Persist enum values ("import", "class") — not member names
            # ("import_", "cls") — so they match the Postgres enum labels.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    qualified_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int] = mapped_column(Integer, nullable=False)
