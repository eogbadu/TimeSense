"""add energy_checkins

TIME-289. A user's own report of how they feel, which overrides the inferred energy for a bounded
window. Also records what the model believed at the same instant, so the gap can be used to
calibrate the curve later.

Revision ID: d4e5f9a1b2c3
Revises: c3d4e5f9a1b2
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4e5f9a1b2c3"
down_revision = "c3d4e5f9a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "energy_checkins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported", sa.String(length=16), nullable=False),
        sa.Column("inferred", sa.String(length=16), nullable=True),
        sa.Column("inferred_score", sa.Integer(), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_energy_checkins_user_id", "energy_checkins", ["user_id"])
    op.create_index("ix_energy_checkins_reported_at", "energy_checkins", ["reported_at"])


def downgrade() -> None:
    op.drop_index("ix_energy_checkins_reported_at", table_name="energy_checkins")
    op.drop_index("ix_energy_checkins_user_id", table_name="energy_checkins")
    op.drop_table("energy_checkins")
