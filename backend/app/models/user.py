from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.calendar import CalendarIntegration, PendingCalendarAction
    from app.models.consent import ConsentRecord
    from app.models.notification import Notification, ReplanRequest
    from app.models.onboarding import AssistantPersonality, OnboardingState
    from app.models.referral import ReferralCode
    from app.models.subscription import Subscription


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    profile: Mapped[UserProfile] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    preferences: Mapped[UserPreferences] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    assistant_personality: Mapped[AssistantPersonality | None] = relationship(
        "AssistantPersonality", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    onboarding_state: Mapped[OnboardingState | None] = relationship(
        "OnboardingState", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    consent_records: Mapped[list[ConsentRecord]] = relationship(
        "ConsentRecord", back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped[Subscription | None] = relationship(
        "Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    calendar_integrations: Mapped[list[CalendarIntegration]] = relationship(
        "CalendarIntegration", back_populates="user", cascade="all, delete-orphan"
    )
    pending_calendar_actions: Mapped[list[PendingCalendarAction]] = relationship(
        "PendingCalendarAction", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    replan_requests: Mapped[list[ReplanRequest]] = relationship(
        "ReplanRequest", back_populates="user", cascade="all, delete-orphan"
    )
    referral_code: Mapped[ReferralCode | None] = relationship(
        "ReferralCode", back_populates="owner", foreign_keys="ReferralCode.owner_id",
        uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class UserProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    onboarding_path: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} display_name={self.display_name}>"


class UserPreferences(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    notification_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="active_coach")
    capture_auto_create: Mapped[str] = mapped_column(String(10), nullable=False, default="ask")
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default="light")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    user: Mapped[User] = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        return f"<UserPreferences user_id={self.user_id}>"
