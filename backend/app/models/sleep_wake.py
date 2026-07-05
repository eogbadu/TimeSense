from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class SleepWakeEvent(UUIDMixin, TimestampMixin, Base):
    """
    A single sleep/wake signal, initially submitted by the mobile app (e.g. from
    HealthKit sleep analysis or manual entry).
    source: healthkit | manual
    replan_request_id is set once a late wake has triggered a pending morning replan,
    so a second wake event the same day doesn't propose a duplicate.
    """

    __tablename__ = "sleep_wake_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wake_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sleep_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    replan_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("replan_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
