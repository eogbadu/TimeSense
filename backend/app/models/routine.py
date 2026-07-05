from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

ROUTINE_TYPES = (
    "sleep",
    "breakfast",
    "lunch",
    "dinner",
    "morning_hygiene",
    "evening_hygiene",
)

# start_minute/end_minute are minutes since local midnight (0-1439).
# end < start means the block wraps past midnight (e.g. sleep 23:00 -> 07:00).
DEFAULT_ROUTINES: dict[str, tuple[int, int]] = {
    "sleep": (23 * 60, 7 * 60),
    "morning_hygiene": (7 * 60, 7 * 60 + 30),
    "breakfast": (7 * 60 + 30, 7 * 60 + 50),
    "lunch": (12 * 60, 12 * 60 + 30),
    "dinner": (18 * 60 + 30, 19 * 60 + 15),
    "evening_hygiene": (22 * 60 + 30, 23 * 60),
}


class RoutineAssumption(UUIDMixin, TimestampMixin, Base):
    """A recurring daily time block (sleep, meal, hygiene) not on the calendar."""

    __tablename__ = "routine_assumptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    routine_type: Mapped[str] = mapped_column(String(32), nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    is_customized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
