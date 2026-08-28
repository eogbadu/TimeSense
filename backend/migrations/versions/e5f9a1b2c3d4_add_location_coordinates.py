"""add user_location_states.latitude/longitude

TIME-291. The CURRENT position only — the row is overwritten on every update, so there is still no
location history. Writes are gated on the `location_tracking` consent; without it these stay null
and behaviour is unchanged.

Needed because errand candidates need a real origin to compute travel time from. Previously
coordinates were only back-filled when the reported place name happened to match a saved UserPlace
exactly, so a user standing anywhere unsaved produced LOCATION_DATA_MISSING.

Revision ID: e5f9a1b2c3d4
Revises: d4e5f9a1b2c3
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "e5f9a1b2c3d4"
down_revision = "d4e5f9a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_location_states", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("user_location_states", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_location_states", "longitude")
    op.drop_column("user_location_states", "latitude")
