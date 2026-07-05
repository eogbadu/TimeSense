"""add_weekly_insights

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-07-05 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "m3n4o5p6q7r8"
down_revision = "l2m3n4o5p6q7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("tasks_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=True),
        sa.Column("most_skipped_meal", sa.String(16), nullable=True),
        sa.Column("late_wake_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commute_confirmed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feedback_done_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feedback_not_now_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_insights_user_week"),
    )


def downgrade() -> None:
    op.drop_table("weekly_insights")
