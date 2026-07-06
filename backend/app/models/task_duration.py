from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskDurationEstimate(UUIDMixin, TimestampMixin, Base):
    """Per-user learned time estimate for a task category — the personal "lookup table" the
    assistant refines as it sees how long the user's tasks actually take. When absent, the seed
    DEFAULT_DURATIONS are used."""

    __tablename__ = "task_duration_estimates"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_task_duration_user_category"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # How many actual observations have shaped this estimate (0 = still seed-only).
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
