"""add tasks.completed_at

TIME-316. Until now the only record of when a task was finished was `updated_at`, which any later
edit moves — `TaskRepository.count_completed_in_range` said so in its own docstring. Knowing what
was recommended when a task was actually completed needs a real instant, so completion gets its own
column, stamped on the pending→done edge only.

Nullable with NO backfill: copying `updated_at` would invent completion instants for rows that were
edited after they were finished. Historic rows stay null and are honestly unknown, per the
"null, not zero, below every sample floor" rule.

Revision ID: b2c3d4e5f0a1
Revises: a1b2c3d4e5f9
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f0a1"
down_revision = "a1b2c3d4e5f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tasks_completed_at", "tasks", ["completed_at"])


def downgrade() -> None:
    op.drop_index("ix_tasks_completed_at", table_name="tasks")
    op.drop_column("tasks", "completed_at")
