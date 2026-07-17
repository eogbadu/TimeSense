from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class HourlyActivity(UUIDMixin, TimestampMixin, Base):
    """Steps in one clock hour — read-only, synced from HealthKit. Powers the sit-vs-move pattern:
    an hour under a step threshold counts as sedentary, which gives the ratio and the times of day
    the user is usually sitting."""

    __tablename__ = "hourly_activity"
    __table_args__ = (
        UniqueConstraint("user_id", "hour_start", name="uq_hourly_user_hour"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    hour_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="healthkit")
