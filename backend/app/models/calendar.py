from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class CalendarIntegration(UUIDMixin, TimestampMixin, Base):
    """Stores OAuth tokens for a user's connected calendar provider."""
    __tablename__ = "calendar_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # google | apple
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calendar_id: Mapped[str] = mapped_column(String(256), nullable=False, default="primary")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    user: Mapped[User] = relationship("User", back_populates="calendar_integrations")


class PendingCalendarAction(UUIDMixin, TimestampMixin, Base):
    """
    A calendar write queued for user approval.
    Approval is required before any event is written — enforced at the service layer.
    """
    __tablename__ = "pending_calendar_actions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    calendar_id: Mapped[str] = mapped_column(String(256), nullable=False, default="primary")
    # JSON-serialised CalendarEventCreate fields
    event_payload: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | approved | rejected | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Set after approval
    created_event_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="pending_calendar_actions")
