"""Secure GitHub App installation handoff

Revision ID: 004
Revises: 003
Create Date: 2026-11-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "github_install_states",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state_hash", sa.String(64), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("installation_id", sa.String(64), nullable=True),
        sa.Column("code_verifier", sa.String(128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("state_hash", name="uq_github_install_states_state_hash"),
    )
    op.create_index("ix_github_install_states_user_id", "github_install_states", ["user_id"])
    op.create_index("ix_github_install_states_expires_at", "github_install_states", ["expires_at"])
    op.drop_column("github_connections", "access_token")


def downgrade() -> None:
    op.add_column(
        "github_connections",
        sa.Column("access_token", sa.String(1024), nullable=True),
    )
    op.drop_index("ix_github_install_states_expires_at", table_name="github_install_states")
    op.drop_index("ix_github_install_states_user_id", table_name="github_install_states")
    op.drop_table("github_install_states")
