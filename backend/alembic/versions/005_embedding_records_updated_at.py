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
    # Safe if the column was already added manually (e.g. Neon ALTER).
    op.execute(
        """
        ALTER TABLE embedding_records
        ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE embedding_records DROP COLUMN IF EXISTS updated_at")
