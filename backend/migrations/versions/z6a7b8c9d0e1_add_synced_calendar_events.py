"""add synced_calendar_events

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-07-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "z6a7b8c9d0e1"
down_revision = "y5z6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "synced_calendar_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="apple"),
        sa.Column("external_id", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(length=256), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        # created_at/updated_at WITH server_default (TIME-125 lesson).
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source", "external_id", name="uq_synced_event"),
    )
    op.create_index("ix_synced_calendar_events_user_id", "synced_calendar_events", ["user_id"])
    op.create_index("ix_synced_calendar_events_starts_at", "synced_calendar_events", ["starts_at"])


def downgrade() -> None:
    op.drop_index("ix_synced_calendar_events_starts_at", table_name="synced_calendar_events")
    op.drop_index("ix_synced_calendar_events_user_id", table_name="synced_calendar_events")
    op.drop_table("synced_calendar_events")
