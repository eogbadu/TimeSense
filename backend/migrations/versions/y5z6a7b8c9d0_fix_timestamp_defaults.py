"""fix missing created_at/updated_at server defaults on hand-written tables

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-07-07

The TimestampMixin declares server_default=now() for created_at/updated_at, but the hand-written
migrations for these tables omitted it, so ORM INSERTs (which rely on the DB default) hit a
NOT NULL violation on Postgres. Add the defaults.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "y5z6a7b8c9d0"
down_revision = "x4y5z6a7b8c9"
branch_labels = None
depends_on = None

_TABLES = ["user_location_states", "user_places", "device_tokens", "push_notifications"]


def upgrade() -> None:
    for t in _TABLES:
        op.alter_column(t, "created_at", server_default=sa.text("now()"))
        op.alter_column(t, "updated_at", server_default=sa.text("now()"))


def downgrade() -> None:
    for t in _TABLES:
        op.alter_column(t, "created_at", server_default=None)
        op.alter_column(t, "updated_at", server_default=None)
