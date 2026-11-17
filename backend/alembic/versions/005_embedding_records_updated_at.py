"""Add updated_at to embedding_records to match Base ORM timestamps

Revision ID: 005
Revises: 004
Create Date: 2026-11-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # EmbeddingRecord inherits Base.updated_at, but migration 002 omitted the column.
    op.add_column(
        "embedding_records",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("embedding_records", "updated_at")
