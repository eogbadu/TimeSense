"""add users.entitlement_override

Durable Premium grant (comped/staff) that doesn't depend on a Subscription row, account age, or an
email allowlist. Replaces email-string matching as the way to keep an account entitled (TIME-282).

Revision ID: a1b2c3d4e5f8
Revises: f9a0b1c2d3e4
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f8"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("entitlement_override", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "entitlement_override")
