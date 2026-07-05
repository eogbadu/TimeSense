"""merge parallel migration heads

Revision ID: e55970716568
Revises: a1b2c3d4e5f7, a7b8c9d0e1f2, b8c9d0e1f2a3, g7h8i9j0k1l2
Create Date: 2026-07-04 17:58:09.823425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e55970716568'
# a1b2c3d4e5f7 (tasks) is no longer a head — g7h8i9j0k1l2 now descends from it (TIME-063) — so it
# drops out of this merge tuple; merging the remaining three heads still reaches all of them.
down_revision: Union[str, None] = ('a7b8c9d0e1f2', 'b8c9d0e1f2a3', 'g7h8i9j0k1l2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
