"""add recommendation_feedback.reason (disagree reason → reason-based learning)

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-07-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f9a0b1c2d3e4"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recommendation_feedback", sa.Column("reason", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("recommendation_feedback", "reason")
