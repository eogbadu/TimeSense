"""keep Notion sub-item and Blocked by relations on import items

TIME-326. A Notion database can already say that one row is a sub-item of another, and that a row is
blocked by others. Import used to keep only the title and the due date, so that structure was lost and
the user had to rebuild it in TimeSense. The page ids are stored here as Notion gave them, and are
linked to tasks as soon as both sides have been imported, in whichever order that happens.

Revision ID: d5e6f0a1b2c3
Revises: c4d5e6f0a1b2
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e6f0a1b2c3"
down_revision = "c4d5e6f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notion_import_items", sa.Column("external_parent_id", sa.String(length=64), nullable=True)
    )
    op.add_column("notion_import_items", sa.Column("external_prereq_ids", sa.JSON(), nullable=True))
    # "Which items are sub-items of this page" is asked on every import.
    op.create_index(
        "ix_notion_import_items_external_parent_id", "notion_import_items", ["external_parent_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_notion_import_items_external_parent_id", table_name="notion_import_items")
    op.drop_column("notion_import_items", "external_prereq_ids")
    op.drop_column("notion_import_items", "external_parent_id")
