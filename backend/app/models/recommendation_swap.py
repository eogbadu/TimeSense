from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# JSONB on Postgres, JSON on SQLite (tests build their schema with create_all against SQLite; a
# bare postgresql type deadlocks there rather than erroring — see known_issues.md).
_JSONMap = JSON().with_variant(JSONB(), "postgresql")


class RecommendationSwap(UUIDMixin, TimestampMixin, Base):
    """"Not that — THIS instead."

    The richest feedback the product can collect. A rejection alone says a pick was wrong; a swap
    says what would have been right, in a known context. It is a PAIRED preference, which is worth
    far more for learning than either half on its own (TIME-294/296).

    The context snapshot is stored with it because the pairing is only meaningful in context: "chose
    an errand over deep work" means something different at 9am on good sleep than at 8pm when
    depleted, and the surrounding state cannot be reconstructed after the fact.
    """

    __tablename__ = "recommendation_swaps"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Both nullable on delete: a deleted task must not erase what the swap taught us.
    rejected_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    chosen_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    # Why the user disagreed, when they said (same vocabulary as RecommendationFeedback.reason).
    reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # part_of_day, energy, location_category, free_minutes, and both tasks' types/categories.
    context_snapshot: Mapped[dict | None] = mapped_column(_JSONMap, nullable=True)
    # How long the chosen task stays pinned as the recommendation.
    pinned_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
