from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedString
from app.models.base import Base, TimestampMixin, UUIDMixin


class EmailIntegration(UUIDMixin, TimestampMixin, Base):
    """A user's read-only email OAuth connection (Gmail first). Same encrypted token-storage shape as
    CalendarIntegration/SlackIntegration, plus refresh + a sync_cursor for incremental dedup."""

    __tablename__ = "email_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="gmail")
    access_token: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Provider cursor (e.g. Gmail historyId) for future incremental fetch; unused in the on-demand v1.
    sync_cursor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class EmailActionItem(UUIDMixin, TimestampMixin, Base):
    """A task detected from an email, queued for user approval. NEVER becomes a Task until the user
    confirms — mirrors SlackActionItem / PendingCalendarAction's approval gate.
    status: pending | confirmed | rejected. We store only subject + sender + snippet, never the body."""

    __tablename__ = "email_action_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[str] = mapped_column(String(128), nullable=False)   # provider id, dedup key
    thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    sender: Mapped[str | None] = mapped_column(String(320), nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)          # the snippet only
    detected_title: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    detected_estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
