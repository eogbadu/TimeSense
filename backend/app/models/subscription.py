from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Subscription(UUIDMixin, TimestampMixin, Base):
    """
    Unified subscription record — one per user regardless of platform.
    status values: trialing | active | canceled | expired | past_due
    platform values: stripe | apple | google
    """
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="stripe")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="trialing")
    # Stripe: stripe_customer_id | Apple: original_transaction_id | Google: purchase_token
    platform_customer_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    # Active subscription/product ID on the platform
    platform_subscription_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    # Plan: monthly | annual | annual_founder
    plan: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # ISO8601 datetimes stored as strings for cross-platform compat
    trial_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trial_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_period_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(nullable=False, default=False)

    user: Mapped[User] = relationship("User", back_populates="subscription")

    def __repr__(self) -> str:
        return f"<Subscription user_id={self.user_id} status={self.status} platform={self.platform}>"

    @property
    def is_premium(self) -> bool:
        return self.status in ("trialing", "active")
