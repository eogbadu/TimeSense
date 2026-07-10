"""recommendation_events → impression/outcome log (typed columns + indexes)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recommendation_events", sa.Column("surface", sa.String(length=32), nullable=True))
    op.add_column("recommendation_events", sa.Column("action_type", sa.String(length=64), nullable=True))
    op.add_column("recommendation_events", sa.Column("domain", sa.String(length=32), nullable=True))
    op.add_column("recommendation_events", sa.Column("score", sa.Float(), nullable=True))
    op.add_column("recommendation_events", sa.Column("rank", sa.Integer(), nullable=True))
    op.add_column("recommendation_events", sa.Column("outcome", sa.String(length=32), nullable=True))
    op.add_column("recommendation_events", sa.Column("outcome_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("recommendation_events", sa.Column("feedback_id", UUID(as_uuid=True), nullable=True))
    op.create_index(
        "ix_recommendation_events_user_created", "recommendation_events", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_recommendation_events_user_action", "recommendation_events", ["user_id", "action_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_recommendation_events_user_action", table_name="recommendation_events")
    op.drop_index("ix_recommendation_events_user_created", table_name="recommendation_events")
    for col in ("feedback_id", "outcome_at", "outcome", "rank", "score", "domain", "action_type", "surface"):
        op.drop_column("recommendation_events", col)
