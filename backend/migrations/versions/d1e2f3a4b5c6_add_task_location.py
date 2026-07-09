"""add task location (name + coordinates)

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-07-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("location_name", sa.String(length=160), nullable=True))
    op.add_column("tasks", sa.Column("location_lat", sa.Float(), nullable=True))
    op.add_column("tasks", sa.Column("location_lng", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "location_lng")
    op.drop_column("tasks", "location_lat")
    op.drop_column("tasks", "location_name")
