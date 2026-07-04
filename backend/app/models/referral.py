from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


def _generate_code() -> str:
    return secrets.token_urlsafe(8).upper()[:10]


class ReferralCode(UUIDMixin, TimestampMixin, Base):
    """A user's shareable referral code. One active code per user."""
    __tablename__ = "referral_codes"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    uses: Mapped[int] = mapped_column(nullable=False, default=0)

    owner: Mapped[User] = relationship("User", back_populates="referral_code", foreign_keys=[owner_id])
    conversions: Mapped[list[ReferralConversion]] = relationship(
        "ReferralConversion", back_populates="referral_code", cascade="all, delete-orphan"
    )


class ReferralConversion(UUIDMixin, TimestampMixin, Base):
    """
    Records when a referred user converts to paid.
    Both referrer and referred get 1 month of premium at conversion.
    No double-reward: one conversion record per referred user.
    """
    __tablename__ = "referral_conversions"

    referral_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("referral_codes.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    referred_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,  # unique prevents double-reward
    )
    # pending → rewarded → failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    referral_code: Mapped[ReferralCode] = relationship("ReferralCode", back_populates="conversions")
    referred_user: Mapped[User] = relationship("User", foreign_keys=[referred_user_id])
