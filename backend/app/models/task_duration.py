from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TaskDurationEstimate(UUIDMixin, TimestampMixin, Base):
    """Per-user learned time estimate for one task TYPE — the personal "lookup table" the assistant
    refines as it sees how long the user's tasks actually take. When absent, the baseline library's
    typical_minutes is used.

    Keyed on task_type since TIME-286. It was keyed on a coarse category, and because most titles
    fell into the catch-all one, a single learned value ended up answering for nearly every task —
    the "everything takes 23 minutes" report."""

    __tablename__ = "task_duration_estimates"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_task_duration_user_category"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Legacy coarse category (the 15-entry seed table). Kept so old rows still read, but no longer
    # what learning is keyed on — see task_type.
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    # The baseline-library type this estimate belongs to (TIME-286). Learning is keyed here so a
    # learned value only ever applies to tasks genuinely like it. Null on pre-TIME-286 rows, which
    # are simply not consulted.
    task_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    # How many actual observations have shaped this estimate (0 = still seed-only).
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
