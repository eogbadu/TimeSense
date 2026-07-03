from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class AssistantPersonality(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assistant_personalities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    style: Mapped[str] = mapped_column(String(40), nullable=False, default="calm_premium")

    user: Mapped[User] = relationship("User", back_populates="assistant_personality")

    def __repr__(self) -> str:
        return f"<AssistantPersonality user_id={self.user_id} style={self.style}>"


class OnboardingState(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_states"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    current_step: Mapped[str] = mapped_column(String(50), nullable=False, default="welcome")
    chosen_path: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # JSON-serialized dict of completed step keys for resume support
    completed_steps: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    skipped_integrations: Mapped[bool] = mapped_column(default=False, nullable=False)
    skipped_health: Mapped[bool] = mapped_column(default=False, nullable=False)
    skipped_location: Mapped[bool] = mapped_column(default=False, nullable=False)
    skipped_goals: Mapped[bool] = mapped_column(default=False, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="onboarding_state")

    def __repr__(self) -> str:
        return f"<OnboardingState user_id={self.user_id} step={self.current_step}>"
