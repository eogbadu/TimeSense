from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class RecommendationFeedback(UUIDMixin, TimestampMixin, Base):
    """User reaction to a single recommendation — agree / disagree / done / snooze / not_now."""

    __tablename__ = "recommendation_feedback"

    VALID_SIGNALS = frozenset({"done", "snooze", "not_now", "agree", "disagree"})
    # Optional reason a user gives when they disagree — feeds reason-based learning (TIME-271).
    VALID_REASONS = frozenset({"wrong_time", "not_priority", "not_relevant", "too_big"})

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal: Mapped[str] = mapped_column(String(32), nullable=False)
    snooze_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Why the user disagreed (VALID_REASONS), when they told us — drives reason-based learning.
    reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
