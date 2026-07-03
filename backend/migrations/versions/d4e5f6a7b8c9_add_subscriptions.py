"""add subscriptions

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-03 03:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False, server_default="stripe"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="trialing"),
        sa.Column("platform_customer_id", sa.String(length=256), nullable=True),
        sa.Column("platform_subscription_id", sa.String(length=256), nullable=True),
        sa.Column("plan", sa.String(length=30), nullable=True),
        sa.Column("trial_start", sa.String(length=32), nullable=True),
        sa.Column("trial_end", sa.String(length=32), nullable=True),
        sa.Column("current_period_end", sa.String(length=32), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)
    op.create_index("ix_subscriptions_platform_customer_id", "subscriptions", ["platform_customer_id"])
    op.create_index("ix_subscriptions_platform_subscription_id", "subscriptions", ["platform_subscription_id"])


def downgrade() -> None:
    op.drop_table("subscriptions")
