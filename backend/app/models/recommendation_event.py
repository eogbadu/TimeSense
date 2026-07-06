from __future__ import annotations

import uuid

from sqlalchemy import JSON, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# JSONB on Postgres (real DB), plain JSON on SQLite (tests).
_JSON = JSON().with_variant(JSONB(), "postgresql")


class RecommendationEvent(UUIDMixin, TimestampMixin, Base):
    """Audit trail of a rendered 'Why This Recommendation?' — what was recommended, the confidence,
    and the full structured explanation, for debugging and future learning."""

    __tablename__ = "recommendation_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # The full explanation payload (context_used, decision_factors, alternatives, summary).
    explanation: Mapped[dict] = mapped_column(_JSON, nullable=False)
