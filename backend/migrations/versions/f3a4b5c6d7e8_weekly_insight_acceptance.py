"""weekly_insights → per-user recommendation acceptance columns

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "weekly_insights",
        sa.Column("recommendations_shown", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "weekly_insights",
        sa.Column("recommendations_accepted", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "weekly_insights",
        sa.Column("recommendation_acceptance_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "weekly_insights",
        sa.Column("mean_confidence", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("weekly_insights", "mean_confidence")
    op.drop_column("weekly_insights", "recommendation_acceptance_rate")
    op.drop_column("weekly_insights", "recommendations_accepted")
    op.drop_column("weekly_insights", "recommendations_shown")
