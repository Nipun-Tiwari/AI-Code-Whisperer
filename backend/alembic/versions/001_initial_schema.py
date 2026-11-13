"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-11-13 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supabase_user_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supabase_user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_supabase_user_id", "users", ["supabase_user_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── github_connections ────────────────────────────────────────────────────
    op.create_table(
        "github_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_app_installation_id", sa.String(64), nullable=True),
        sa.Column("github_account_login", sa.String(255), nullable=False),
        sa.Column("github_account_type", sa.String(50), nullable=False, server_default="User"),
        sa.Column("token_reference", sa.String(512), nullable=True),
        sa.Column("scopes", sa.String(1024), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "revoked", "expired", name="github_connection_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_github_connections_user_id", "github_connections", ["user_id"])

    # ── repositories ─────────────────────────────────────────────────────────
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("github_repo_id", sa.String(64), nullable=False),
        sa.Column(
            "visibility",
            sa.Enum("public", "private", name="repository_visibility"),
            nullable=False,
            server_default="private",
        ),
        sa.Column("default_branch", sa.String(255), nullable=False, server_default="main"),
        sa.Column("selected_branch", sa.String(255), nullable=False, server_default="main"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "indexing", "indexed", "failed", "stale", "removed", name="repository_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["github_connection_id"], ["github_connections.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repositories_user_id", "repositories", ["user_id"])

    # ── repository_versions ───────────────────────────────────────────────────
    op.create_table(
        "repository_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("branch", sa.String(255), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("index_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_versions_repository_id", "repository_versions", ["repository_id"])

    # ── index_jobs ────────────────────────────────────────────────────────────
    op.create_table(
        "index_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "mode",
            sa.Enum("full", "incremental", name="index_job_mode"),
            nullable=False,
            server_default="full",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued", "fetching", "classifying", "parsing", "summarizing",
                "embedding", "persisting", "completed", "partial", "failed", "paused",
                name="index_job_status",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("stage", sa.String(100), nullable=True),
        sa.Column("checkpoint", sa.Text, nullable=True),
        sa.Column("files_total", sa.Integer, nullable=True),
        sa.Column("files_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("files_skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_category", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["repository_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_index_jobs_repository_id", "index_jobs", ["repository_id"])
    op.create_index("ix_index_jobs_status", "index_jobs", ["status"])

    # ── file_records ──────────────────────────────────────────────────────────
    op.create_table(
        "file_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(4096), nullable=False),
        sa.Column("language", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "parse_status",
            sa.Enum("parsed", "partial", "unsupported", "failed", name="parse_status"),
            nullable=False,
            server_default="unsupported",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_records_repository_id", "file_records", ["repository_id"])
    op.create_index("ix_file_records_version_id", "file_records", ["version_id"])

    # ── symbol_records ────────────────────────────────────────────────────────
    op.create_table(
        "symbol_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "symbol_kind",
            sa.Enum("class", "function", "method", "module", "import", name="symbol_kind"),
            nullable=False,
        ),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("qualified_name", sa.String(1024), nullable=False),
        sa.Column("line_start", sa.Integer, nullable=False),
        sa.Column("line_end", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_symbol_records_file_id", "symbol_records", ["file_id"])

    # ── code_chunks ───────────────────────────────────────────────────────────
    op.create_table(
        "code_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("object_key", sa.String(1024), nullable=True),
        sa.Column("line_start", sa.Integer, nullable=True),
        sa.Column("line_end", sa.Integer, nullable=True),
        sa.Column("qdrant_point_id", sa.String(64), nullable=True),
        sa.Column("embedding_model", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["file_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["repository_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_chunks_file_id", "code_chunks", ["file_id"])
    op.create_index("ix_code_chunks_version_id", "code_chunks", ["version_id"])

    # ── conversations ─────────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_repository_id", "conversations", ["repository_id"])

    # ── agent_tasks ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "task_type",
            sa.Enum("repository_qa", "investigation", "security_scan", "documentation", name="task_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("queued", "planning", "running", "completed", "partial", "failed", "paused", name="task_status"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("plan", postgresql.JSONB, nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("token_budget", sa.Integer, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_tasks_user_id", "agent_tasks", ["user_id"])
    op.create_index("ix_agent_tasks_conversation_id", "agent_tasks", ["conversation_id"])
    op.create_index("ix_agent_tasks_repository_id", "agent_tasks", ["repository_id"])
    op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"])

    # ── security_scans ────────────────────────────────────────────────────────
    op.create_table(
        "security_scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("queued", "scanning", "completed", "incomplete", "failed", name="security_scan_status"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("scanner_versions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["repository_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_scans_repository_id", "security_scans", ["repository_id"])

    # ── security_findings ─────────────────────────────────────────────────────
    op.create_table(
        "security_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "dependency_vulnerability", "insecure_pattern", "hardcoded_secret",
                name="finding_category",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("critical", "high", "medium", "low", "unknown", name="finding_severity"),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("package_name", sa.String(512), nullable=True),
        sa.Column("file_path", sa.String(4096), nullable=True),
        sa.Column("installed_version", sa.String(128), nullable=True),
        sa.Column("fixed_version", sa.String(128), nullable=True),
        sa.Column("advisory_id", sa.String(256), nullable=True),
        sa.Column("rule_id", sa.String(256), nullable=True),
        sa.Column("evidence", sa.Text, nullable=False, server_default=""),
        sa.Column("remediation_guidance", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["security_scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_findings_scan_id", "security_findings", ["scan_id"])

    # ── usage_events ──────────────────────────────────────────────────────────
    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("service_key", sa.String(100), nullable=False),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("unit", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="codewhisperer_tracked"),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["agent_tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_service_key", "usage_events", ["service_key"])

    # ── quota_snapshots ───────────────────────────────────────────────────────
    op.create_table(
        "quota_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("service_key", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("usage_value", sa.Float, nullable=True),
        sa.Column("usage_unit", sa.String(64), nullable=True),
        sa.Column("limit_value", sa.Float, nullable=True),
        sa.Column("remaining", sa.Float, nullable=True),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="codewhisperer_tracked"),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("freshness", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quota_snapshots_service_key", "quota_snapshots", ["service_key"])


def downgrade() -> None:
    op.drop_table("quota_snapshots")
    op.drop_table("usage_events")
    op.drop_table("security_findings")
    op.drop_table("security_scans")
    op.drop_table("agent_tasks")
    op.drop_table("conversations")
    op.drop_table("code_chunks")
    op.drop_table("symbol_records")
    op.drop_table("file_records")
    op.drop_table("index_jobs")
    op.drop_table("repository_versions")
    op.drop_table("repositories")
    op.drop_table("github_connections")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS quota_snapshots_freshness CASCADE")
    op.execute("DROP TYPE IF EXISTS finding_severity CASCADE")
    op.execute("DROP TYPE IF EXISTS finding_category CASCADE")
    op.execute("DROP TYPE IF EXISTS security_scan_status CASCADE")
    op.execute("DROP TYPE IF EXISTS task_status CASCADE")
    op.execute("DROP TYPE IF EXISTS task_type CASCADE")
    op.execute("DROP TYPE IF EXISTS parse_status CASCADE")
    op.execute("DROP TYPE IF EXISTS symbol_kind CASCADE")
    op.execute("DROP TYPE IF EXISTS index_job_status CASCADE")
    op.execute("DROP TYPE IF EXISTS index_job_mode CASCADE")
    op.execute("DROP TYPE IF EXISTS repository_status CASCADE")
    op.execute("DROP TYPE IF EXISTS repository_visibility CASCADE")
    op.execute("DROP TYPE IF EXISTS github_connection_status CASCADE")
