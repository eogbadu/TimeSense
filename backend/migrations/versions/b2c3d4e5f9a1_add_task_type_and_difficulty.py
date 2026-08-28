"""add tasks.task_type and tasks.difficulty

Baseline task library (TIME-284): tasks gain a library type and a difficulty level. Both nullable —
existing rows stay null and readers fall back to classifying the title, so no backfill is needed.

Revision ID: b2c3d4e5f9a1
Revises: a1b2c3d4e5f8
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f9a1"
down_revision = "a1b2c3d4e5f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("task_type", sa.String(length=40), nullable=True))
    op.add_column("tasks", sa.Column("difficulty", sa.String(length=16), nullable=True))
    op.create_index("ix_tasks_task_type", "tasks", ["task_type"])


def downgrade() -> None:
    op.drop_index("ix_tasks_task_type", table_name="tasks")
    op.drop_column("tasks", "difficulty")
    op.drop_column("tasks", "task_type")
