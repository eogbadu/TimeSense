"""add tasks.calendar_event_id (dedup key for imported calendar events)

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-07-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("calendar_event_id", sa.String(300), nullable=True))
    op.create_index("ix_tasks_calendar_event_id", "tasks", ["calendar_event_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_calendar_event_id", table_name="tasks")
    op.drop_column("tasks", "calendar_event_id")
