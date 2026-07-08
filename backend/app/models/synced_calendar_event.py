from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SyncedCalendarEvent(UUIDMixin, TimestampMixin, Base):
    """A calendar event the app synced up from the device (EventKit / Apple Calendar). Read-only
    mirror so the server-side engine can factor the user's schedule. Only what we need to reason
    about time is stored."""

    __tablename__ = "synced_calendar_events"
    __table_args__ = (
        UniqueConstraint("user_id", "source", "external_id", name="uq_synced_event"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="apple")  # apple | google
    external_id: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
