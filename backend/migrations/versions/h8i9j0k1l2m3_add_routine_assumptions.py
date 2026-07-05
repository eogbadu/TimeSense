"""add_routine_assumptions

Revision ID: h8i9j0k1l2m3
Revises: e55970716568
Create Date: 2026-07-05 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "h8i9j0k1l2m3"
down_revision = "e55970716568"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routine_assumptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("routine_type", sa.String(32), nullable=False),
        sa.Column("start_minute", sa.Integer, nullable=False),
        sa.Column("end_minute", sa.Integer, nullable=False),
        sa.Column("is_customized", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("routine_assumptions")
