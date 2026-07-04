"""add_referral_tables

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-03 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referral_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("uses", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "referral_conversions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("referral_code_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("referral_codes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("referred_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("rewarded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("referral_conversions")
    op.drop_table("referral_codes")
