from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class ConsentRecord(UUIDMixin, TimestampMixin, Base):
    """
    Immutable record of a user's consent decision for a specific data type.
    One row per consent_type per decision event (append-only for audit trail).
    The latest record per consent_type is the effective consent state.

    consent_type values:
      - audio_storage       : store raw audio captures
      - audio_training      : use audio/transcripts for anonymized model improvement
      - location_tracking   : precise GPS location
      - health_data         : Apple Health / Google Fit data
      - calendar_details    : full calendar event details (vs free/busy only)
      - analytics           : anonymous usage analytics
      - email_content       : read recent email (subject/snippet) to detect tasks
    """
    __tablename__ = "consent_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    granted: Mapped[bool] = mapped_column(nullable=False)
    # Optional context: which screen/flow triggered this consent decision
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Optional freeform notes (e.g. platform, app version)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="consent_records")

    def __repr__(self) -> str:
        return f"<ConsentRecord user_id={self.user_id} type={self.consent_type} granted={self.granted}>"
