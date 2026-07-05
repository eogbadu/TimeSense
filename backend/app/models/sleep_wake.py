from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

SLEEP_WAKE_SOURCES = ("healthkit", "manual")


class SleepWakeEvent(UUIDMixin, TimestampMixin, Base):
    """A logged sleep period, used to detect late wake-ups for morning replan suggestions."""

    __tablename__ = "sleep_wake_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sleep_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wake_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="healthkit")
