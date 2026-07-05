from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WeeklyInsight(UUIDMixin, TimestampMixin, Base):
    """A retrospective summary of one completed Monday-Sunday week. One row per
    (user_id, week_start) — generated once and cached, never silently regenerated."""

    __tablename__ = "weekly_insights"
    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_weekly_insights_user_week"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    most_skipped_meal: Mapped[str | None] = mapped_column(String(16), nullable=True)
    late_wake_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    commute_confirmed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback_done_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feedback_not_now_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
