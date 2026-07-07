from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserPlace(UUIDMixin, TimestampMixin, Base):
    """A place the user deliberately saved (Home / Work / their Walmart …) WITH coordinates. Unlike a
    live location fix, these are named, user-chosen places — used as the travel origin (the place the
    user is currently at) and as preferred destinations for errands."""

    __tablename__ = "user_places"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_place_user_name"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    place_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # walmart/grocery_store/…
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    is_preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
