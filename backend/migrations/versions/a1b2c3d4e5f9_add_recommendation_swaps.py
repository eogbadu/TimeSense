"""add recommendation_swaps

TIME-294. "Not that — THIS instead": a paired preference in a known context, which is far more
informative than a bare rejection. The context snapshot is stored with it because the pairing only
means anything in context, and the surrounding state can't be reconstructed afterwards.

Revision ID: a1b2c3d4e5f9
Revises: f9a1b2c3d4e5
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f9"
down_revision = "f9a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_swaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rejected_task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chosen_task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("context_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("pinned_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_recommendation_swaps_user_id", "recommendation_swaps", ["user_id"])
    op.create_index("ix_recommendation_swaps_pinned_until", "recommendation_swaps", ["pinned_until"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_swaps_pinned_until", table_name="recommendation_swaps")
    op.drop_index("ix_recommendation_swaps_user_id", table_name="recommendation_swaps")
    op.drop_table("recommendation_swaps")
