"""add work_start_hour / work_end_hour to user_preferences

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-07-05

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "t0u1v2w3x4y5"
down_revision = "s9t0u1v2w3x4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("work_start_hour", sa.Integer(), nullable=False, server_default="8"),
    )
    op.add_column(
        "user_preferences",
        sa.Column("work_end_hour", sa.Integer(), nullable=False, server_default="21"),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "work_end_hour")
    op.drop_column("user_preferences", "work_start_hour")
