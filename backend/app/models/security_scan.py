from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SecurityScanStatus(str, enum.Enum):
    queued = "queued"
    scanning = "scanning"
    completed = "completed"
    incomplete = "incomplete"
    failed = "failed"


class FindingSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    unknown = "unknown"


class FindingCategory(str, enum.Enum):
    dependency_vulnerability = "dependency_vulnerability"
    insecure_pattern = "insecure_pattern"
    hardcoded_secret = "hardcoded_secret"


class SecurityScan(Base):
    __tablename__ = "security_scans"

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
    status: Mapped[SecurityScanStatus] = mapped_column(
        Enum(SecurityScanStatus, name="security_scan_status"),
        nullable=False,
        default=SecurityScanStatus.queued,
    )
    # {"dependency_scanner": "1.0", "static_analyzer": "semgrep/1.75"} etc.
    scanner_versions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[FindingCategory] = mapped_column(
        Enum(FindingCategory, name="finding_category"),
        nullable=False,
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity"),
        nullable=False,
        default=FindingSeverity.unknown,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    package_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    installed_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fixed_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    advisory_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    remediation_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
