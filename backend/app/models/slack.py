from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SlackIntegration(UUIDMixin, TimestampMixin, Base):
    """Stores a user's Slack OAuth token. Same token-storage shape as CalendarIntegration."""

    __tablename__ = "slack_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    team_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class SlackActionItem(UUIDMixin, TimestampMixin, Base):
    """
    An action item detected from a Slack message, queued for user approval.
    NEVER becomes a Task until the user confirms — mirrors PendingCalendarAction's approval gate.
    status: pending | confirmed | rejected
    """

    __tablename__ = "slack_action_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    message_ts: Mapped[str] = mapped_column(String(64), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_title: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    detected_estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
