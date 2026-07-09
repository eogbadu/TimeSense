from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Float, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Task(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    scheduled_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    # True when TimeSense auto-placed this task into the day (vs. a user-set time) — drives the
    # "Scheduled · Undo" affordance on Today.
    auto_scheduled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    # An explicit place for the task (e.g. an errand), chosen from saved places / maps — more reliable
    # than parsing "the mall" from the title, and lets the engine compute real travel.
    location_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="tasks")
    reminders: Mapped[list[InternalReminder]] = relationship(
        "InternalReminder", back_populates="task", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status} title={self.title[:40]!r}>"


class InternalReminder(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "internal_reminders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="reminder")
    trigger_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    task: Mapped[Task | None] = relationship("Task", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<InternalReminder id={self.id} type={self.type} status={self.status}>"
