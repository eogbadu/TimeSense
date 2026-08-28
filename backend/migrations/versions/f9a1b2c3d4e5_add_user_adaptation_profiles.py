"""add user_adaptation_profiles

TIME-292. The first table whose purpose is adaptation: a nightly rollup of what TimeSense has
learned about one person, cheap enough for the engine to read on every /now request.

Every metric column is nullable on purpose — null means "not enough evidence yet", which is
different from zero, and lets consumers stay neutral for a new user rather than scoring them on
noise.

Revision ID: f9a1b2c3d4e5
Revises: e5f9a1b2c3d4
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f9a1b2c3d4e5"
down_revision = "e5f9a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_adaptation_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("days_observed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_by_hour", postgresql.JSONB(), nullable=True),
        sa.Column("completion_by_weekday", postgresql.JSONB(), nullable=True),
        sa.Column("acceptance_by_category", postgresql.JSONB(), nullable=True),
        sa.Column("acceptance_by_action_type", postgresql.JSONB(), nullable=True),
        sa.Column("estimate_ratio_by_type", postgresql.JSONB(), nullable=True),
        sa.Column("completions_by_energy", postgresql.JSONB(), nullable=True),
        sa.Column("energy_bias", sa.Float(), nullable=True),
        sa.Column("typical_wake_minute", sa.Integer(), nullable=True),
        sa.Column("typical_first_task_minute", sa.Integer(), nullable=True),
        sa.Column("typical_wind_down_minute", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_adaptation_profiles_user_id", "user_adaptation_profiles",
                    ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_adaptation_profiles_user_id", table_name="user_adaptation_profiles")
    op.drop_table("user_adaptation_profiles")
