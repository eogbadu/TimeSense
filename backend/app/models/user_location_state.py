from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserLocationState(UUIDMixin, TimestampMixin, Base):
    """The user's current derived place — e.g. 'Home', 'Work', or None (out and about).

    ONE row per user, upserted from the app; used to shape recommendations.

    Coordinates (TIME-291): the current position is now stored alongside the name, but ONLY the
    current one. The row is overwritten on every update, so there is still no location HISTORY —
    the original "raw location points are never persisted" rule was about a trail of movement, and
    that remains true. Writing coordinates is additionally gated on the `location_tracking` consent;
    without it they stay null and behaviour is exactly as before.

    Why this is needed: errand candidates need a real origin to compute travel time from. Before
    this, coordinates were only ever back-filled when the reported place name happened to match a
    saved UserPlace exactly, so any user standing anywhere unsaved produced LOCATION_DATA_MISSING
    and location silently stopped influencing recommendations."""

    __tablename__ = "user_location_states"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    place_name: Mapped[str | None] = mapped_column(String(64), nullable=True)   # None = away
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Current position only — overwritten each update, never appended to. Null without consent.
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
