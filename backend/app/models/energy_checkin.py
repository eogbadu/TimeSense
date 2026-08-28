from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

VALID_REPORTED_LEVELS = frozenset({"low", "medium", "high"})


class EnergyCheckIn(UUIDMixin, TimestampMixin, Base):
    """A user telling us how they actually feel, overriding what we inferred.

    Inferred energy will always be approximate — it reads sleep, activity and the clock, not the
    person. One tap should be able to correct it, and that correction should actually drive
    recommendations rather than being cosmetic.

    Also stores what the model believed at that moment. The gap between reported and inferred is the
    only real feedback the energy model has, and it's what would let the curve be calibrated later
    (deliberately not done in this ticket — collect first, tune on evidence).
    """

    __tablename__ = "energy_checkins"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reported: Mapped[str] = mapped_column(String(16), nullable=False)
    # What compute_energy said at the same instant — null only if the estimate was unavailable.
    inferred: Mapped[str | None] = mapped_column(String(16), nullable=True)
    inferred_score: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 0-100
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
