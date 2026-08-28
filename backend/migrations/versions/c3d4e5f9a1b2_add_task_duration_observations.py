"""add task_duration_observations; move learned estimates onto task types

TIME-286. Two changes:

1. New task_duration_observations table — the raw "this actually took N minutes" evidence, which
   was previously discarded in favour of only the blended estimate.
2. task_duration_estimates gains a task_type column alongside the legacy category. Rows for the
   catch-all "general" category are DELETED rather than migrated: that bucket is the bug (most
   titles fell into it, so one learned number answered for every unclassified task). Rows for real
   categories are left in place with a null task_type; they simply stop being consulted, and the
   library seed answers until per-type observations accumulate.

Revision ID: c3d4e5f9a1b2
Revises: b2c3d4e5f9a1
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f9a1b2"
down_revision = "b2c3d4e5f9a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_duration_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_type", sa.String(length=40), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("actual_minutes", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_task_duration_observations_user_id", "task_duration_observations", ["user_id"])
    op.create_index("ix_task_duration_observations_task_type", "task_duration_observations", ["task_type"])

    op.add_column("task_duration_estimates",
                  sa.Column("task_type", sa.String(length=40), nullable=True))
    op.create_index("ix_task_duration_estimates_task_type", "task_duration_estimates", ["task_type"])

    # Drop the catch-all rows. These are precisely the "everything takes 23 minutes" values: because
    # most real titles fell through to "general", one learned number ended up answering for nearly
    # every task the user captured.
    op.execute("DELETE FROM task_duration_estimates WHERE category = 'general'")


def downgrade() -> None:
    op.drop_index("ix_task_duration_estimates_task_type", table_name="task_duration_estimates")
    op.drop_column("task_duration_estimates", "task_type")
    op.drop_index("ix_task_duration_observations_task_type", table_name="task_duration_observations")
    op.drop_index("ix_task_duration_observations_user_id", table_name="task_duration_observations")
    op.drop_table("task_duration_observations")
