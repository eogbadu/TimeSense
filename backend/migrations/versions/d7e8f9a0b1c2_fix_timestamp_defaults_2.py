"""fix missing created_at/updated_at server defaults on more hand-written tables

TimestampMixin declares server_default=now() for created_at/updated_at, so the ORM omits them from
INSERTs and relies on the DB default. Several hand-written migrations created these columns NOT NULL
*without* a server_default — harmless on SQLite (tests use create_all, which honors the mixin) but a
NotNullViolation on real Postgres (e.g. the calendar-integration OAuth callback insert). The earlier
`fix_timestamp_defaults` migration only patched four tables; this covers the rest.

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-07-17
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d7e8f9a0b1c2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None

_TABLES = [
    "calendar_integrations",
    "pending_calendar_actions",
    "recommendation_events",
    "notifications",
    "replan_requests",
    "waitlist_entries",
    "invite_codes",
    "referral_codes",
    "referral_conversions",
    "task_duration_estimates",
]


def upgrade() -> None:
    for t in _TABLES:
        op.alter_column(t, "created_at", server_default=sa.text("now()"))
        op.alter_column(t, "updated_at", server_default=sa.text("now()"))


def downgrade() -> None:
    for t in _TABLES:
        op.alter_column(t, "created_at", server_default=None)
        op.alter_column(t, "updated_at", server_default=None)
