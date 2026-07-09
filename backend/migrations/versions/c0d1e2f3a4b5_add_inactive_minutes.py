"""add daily_activity.inactive_minutes (sedentary inference)

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-07-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("daily_activity", sa.Column("inactive_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("daily_activity", "inactive_minutes")
