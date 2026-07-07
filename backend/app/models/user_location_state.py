from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserLocationState(UUIDMixin, TimestampMixin, Base):
    """The user's current derived place — e.g. 'Home', 'Work', or None (out and about). Only the
    place NAME is stored, never raw coordinates (per "raw location points are never persisted"). One
    row per user, upserted from the app on geofence transitions; used to shape recommendations."""

    __tablename__ = "user_location_states"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    place_name: Mapped[str | None] = mapped_column(String(64), nullable=True)   # None = away
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
