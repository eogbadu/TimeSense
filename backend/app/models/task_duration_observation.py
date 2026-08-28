from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskDurationObservation(UUIDMixin, TimestampMixin, Base):
    """One real "this actually took N minutes" observation.

    Before TIME-286 only the blended estimate was stored, so the raw evidence behind it was thrown
    away. That made the learned number impossible to audit, impossible to recompute when the
    blending rule changed, and impossible to reason about ("is 23 minutes based on 2 samples or
    200?"). Keeping the observations makes the estimate a derived value rather than the only record.

    Also carries the estimate that was shown at the time, which is what estimate-accuracy reporting
    needs (TIME-292).
    """

    __tablename__ = "task_duration_observations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable: a task can be deleted without invalidating what it taught us.
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # What the assistant predicted when the task was shown (null if it had no estimate).
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
