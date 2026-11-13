"""Phase 3: mcp_tool_calls table

Revision ID: 003
Revises: 002
Create Date: 2026-11-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_tool_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.Text, nullable=False),
        sa.Column("safe_args_summary", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("error_category", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mcp_tool_calls_task_id", "mcp_tool_calls", ["task_id"])
    op.create_index("ix_mcp_tool_calls_user_id", "mcp_tool_calls", ["user_id"])
    op.create_index("ix_mcp_tool_calls_tool_name", "mcp_tool_calls", ["tool_name"])


def downgrade() -> None:
    op.drop_index("ix_mcp_tool_calls_tool_name", "mcp_tool_calls")
    op.drop_index("ix_mcp_tool_calls_user_id", "mcp_tool_calls")
    op.drop_index("ix_mcp_tool_calls_task_id", "mcp_tool_calls")
    op.drop_table("mcp_tool_calls")
