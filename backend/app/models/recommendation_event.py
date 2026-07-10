from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# JSONB on Postgres (real DB), plain JSON on SQLite (tests).
_JSON = JSON().with_variant(JSONB(), "postgresql")


class RecommendationEvent(UUIDMixin, TimestampMixin, Base):
    """An impression → outcome record: what recommendation was shown (surface, domain, action_type,
    score, confidence), and how the user reacted (outcome). The stable `id` is surfaced to clients so
    later feedback can be joined back. Powers acceptance-rate + confidence-calibration measurement."""

    __tablename__ = "recommendation_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # The full explanation payload (context_used, decision_factors, alternatives, summary).
    explanation: Mapped[dict] = mapped_column(_JSON, nullable=False)

    # Impression metadata — nullable so old rows and lightweight surfaces don't need all of it.
    surface: Mapped[str | None] = mapped_column(String(32), nullable=True)          # now / now_why / now_recommendation / push
    action_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(32), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)                 # 0 = best, 1.. = alternatives
    # Outcome — how the user reacted (agree/disagree/done/snooze/not_now), null while still just shown.
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    outcome_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_recommendation_events_user_created", "user_id", "created_at"),
        Index("ix_recommendation_events_user_action", "user_id", "action_type"),
    )
