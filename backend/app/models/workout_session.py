from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkoutSession(UUIDMixin, TimestampMixin, Base):
    """One Apple Health workout — a run, a gym session, a ride … Read-only, synced from HealthKit
    (TimeSense never writes to Health). Powers the running/gym behavioral patterns on Insights."""

    __tablename__ = "workout_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_workout_user_external"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # HealthKit workout UUID — dedup key so re-syncs don't duplicate.
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    # Normalized: running / walking / cycling / strength / hiit / functional / other.
    workout_type: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_energy_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="healthkit")
