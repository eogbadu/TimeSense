from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedString
from app.models.base import Base, TimestampMixin, UUIDMixin


class NotionIntegration(UUIDMixin, TimestampMixin, Base):
    """Stores a user's Notion OAuth token. Same token-storage shape as the other integrations."""

    __tablename__ = "notion_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_token: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class NotionImportItem(UUIDMixin, TimestampMixin, Base):
    """
    A candidate task read from a Notion database page, queued for user import.
    NEVER becomes a Task until the user imports it — the same approval gate as the message-source
    integrations, framed as import/dismiss since these are already-structured tasks.
    status: pending | imported | dismissed
    """

    __tablename__ = "notion_import_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    database_id: Mapped[str] = mapped_column(String(64), nullable=False)
    page_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
