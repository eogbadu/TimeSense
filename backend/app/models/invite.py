from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class WaitlistEntry(UUIDMixin, TimestampMixin, Base):
    """Email waitlist. Status: waiting | invited | joined | removed."""
    __tablename__ = "waitlist_entries"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    referral_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InviteCode(UUIDMixin, TimestampMixin, Base):
    """Admin-issued invite codes required for signup. max_uses=0 means unlimited."""
    __tablename__ = "invite_codes"

    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_by: Mapped[User | None] = relationship("User", foreign_keys=[created_by_id])

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.max_uses > 0 and self.uses >= self.max_uses:
            return False
        return not (self.expires_at and datetime.utcnow() > self.expires_at.replace(tzinfo=None))
