from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

NOTIFICATION_EVENT_TYPES = ("morning_checkin", "evening_checkout", "learning_prompt")


class NotificationEvent(UUIDMixin, TimestampMixin, Base):
    """
    Audit trail of orchestrated check-in/check-out/learning-prompt notifications sent to a
    user. created_at also drives once-per-day dedup (no separate sent_date column needed).
    """

    __tablename__ = "notification_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    notification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="SET NULL"),
        nullable=True,
    )
