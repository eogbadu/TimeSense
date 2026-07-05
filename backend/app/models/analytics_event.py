from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AnalyticsEvent(UUIDMixin, TimestampMixin, Base):
    """
    A product analytics event. user_id is nullable so system-level events can be recorded without
    a user. user-attributed events are only written when that user has granted the 'analytics'
    consent (enforced in AnalyticsService). properties is a JSON string of non-PII product signals.
    """

    __tablename__ = "analytics_events"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    properties: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
