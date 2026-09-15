"""add task steps (parent_task_id, position, steps_sequential) and task_prerequisites

TIME-320. A task can be a step of exactly one parent, and a task can wait for another. One level of
nesting is enforced in the service layer, because a CHECK constraint cannot look at another row.

Both features share one edge table: "task_id waits for prerequisite_task_id". Ordered steps write
origin='sequence' edges automatically and "Do this after…" writes origin='manual' ones, so the
engine has a single rule to apply and re-chaining a group never touches what the user set by hand.

Revision ID: c4d5e6f0a1b2
Revises: b2c3d4e5f0a1
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "c4d5e6f0a1b2"
down_revision = "b2c3d4e5f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("parent_task_id", UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("position", sa.Integer(), nullable=True))
    # NOT NULL on a populated table needs a server default, or the ALTER fails on every existing row.
    op.add_column(
        "tasks",
        sa.Column("steps_sequential", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_foreign_key(
        "fk_tasks_parent_task_id", "tasks", "tasks", ["parent_task_id"], ["id"], ondelete="CASCADE"
    )
    # Postgres does not index foreign keys on its own, and "steps of these parents" is read on every
    # Today and Now load.
    op.create_index("ix_tasks_parent_task_id", "tasks", ["parent_task_id"])
    op.create_check_constraint(
        "ck_tasks_parent_not_self", "tasks", "parent_task_id IS NULL OR parent_task_id <> id"
    )

    op.create_table(
        "task_prerequisites",
        sa.Column("task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prerequisite_task_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prerequisite_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "prerequisite_task_id"),
        sa.CheckConstraint("task_id <> prerequisite_task_id", name="ck_task_prerequisites_not_self"),
        sa.CheckConstraint("origin IN ('sequence', 'manual')", name="ck_task_prerequisites_origin"),
    )
    # The primary key already serves "what does X wait for"; this serves "what does finishing X unblock".
    op.create_index(
        "ix_task_prerequisites_prerequisite_task_id", "task_prerequisites", ["prerequisite_task_id"]
    )
    op.create_index("ix_task_prerequisites_user_id", "task_prerequisites", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_task_prerequisites_user_id", table_name="task_prerequisites")
    op.drop_index("ix_task_prerequisites_prerequisite_task_id", table_name="task_prerequisites")
    op.drop_table("task_prerequisites")
    op.drop_constraint("ck_tasks_parent_not_self", "tasks", type_="check")
    op.drop_index("ix_tasks_parent_task_id", table_name="tasks")
    op.drop_constraint("fk_tasks_parent_task_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "steps_sequential")
    op.drop_column("tasks", "position")
    op.drop_column("tasks", "parent_task_id")
