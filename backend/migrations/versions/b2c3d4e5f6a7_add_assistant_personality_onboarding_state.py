"""add assistant personality and onboarding state

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-03 01:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_personalities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("style", sa.String(length=40), nullable=False, server_default="calm_premium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_personalities_user_id", "assistant_personalities", ["user_id"], unique=True)

    op.create_table(
        "onboarding_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_step", sa.String(length=50), nullable=False, server_default="welcome"),
        sa.Column("chosen_path", sa.String(length=50), nullable=True),
        sa.Column("completed_steps", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("skipped_integrations", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("skipped_health", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("skipped_location", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("skipped_goals", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_onboarding_states_user_id", "onboarding_states", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("onboarding_states")
    op.drop_table("assistant_personalities")
