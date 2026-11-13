"""Phase 2 additions: embedding_records table and performance indexes

Revision ID: 002
Revises: 001
Create Date: 2026-11-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create embedding_records table
    op.create_table(
        "embedding_records",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "chunk_id",
            UUID(as_uuid=True),
            sa.ForeignKey("code_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("vector_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_embedding_records_chunk_id", "embedding_records", ["chunk_id"])
    op.create_index("ix_embedding_records_vector_id", "embedding_records", ["vector_id"])

    # Add chunk_type and symbol_name columns to code_chunks (needed by pipeline)
    op.add_column("code_chunks", sa.Column("chunk_type", sa.String(50), nullable=True))
    op.add_column("code_chunks", sa.Column("symbol_name", sa.String(512), nullable=True))

    # Performance indexes (IF NOT EXISTS — 001 may have created some already)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_file_records_repository_path ON file_records (repository_id, path)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_chunks_file_id ON code_chunks (file_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_symbol_records_file_id_kind ON symbol_records (file_id, symbol_kind)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_index_jobs_status_created ON index_jobs (status, created_at)"
    )

    # GitHub connections: store actual token (encrypted ref) — add access_token column
    op.add_column(
        "github_connections",
        sa.Column("access_token", sa.String(1024), nullable=True),
    )

    # Repositories: add description length bump and clone_url
    op.add_column(
        "repositories",
        sa.Column("clone_url", sa.String(1024), nullable=True),
    )

    # Repository versions: add tree_sha
    op.add_column(
        "repository_versions",
        sa.Column("tree_sha", sa.String(40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("repository_versions", "tree_sha")
    op.drop_column("repositories", "clone_url")
    op.drop_column("github_connections", "access_token")
    op.execute("DROP INDEX IF EXISTS ix_index_jobs_status_created")
    op.execute("DROP INDEX IF EXISTS ix_symbol_records_file_id_kind")
    op.execute("DROP INDEX IF EXISTS ix_code_chunks_file_id")
    op.execute("DROP INDEX IF EXISTS ix_file_records_repository_path")
    op.drop_column("code_chunks", "symbol_name")
    op.drop_column("code_chunks", "chunk_type")
    op.drop_index("ix_embedding_records_vector_id", table_name="embedding_records")
    op.drop_index("ix_embedding_records_chunk_id", table_name="embedding_records")
    op.drop_table("embedding_records")
