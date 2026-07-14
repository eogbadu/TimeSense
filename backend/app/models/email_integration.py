from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import EncryptedString
from app.models.base import Base, TimestampMixin, UUIDMixin


class EmailIntegration(UUIDMixin, TimestampMixin, Base):
    """A user's read-only email OAuth connection (Gmail first). Same encrypted token-storage shape as
    CalendarIntegration/SlackIntegration, plus refresh + a sync_cursor for incremental dedup."""

    __tablename__ = "email_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="gmail")
    access_token: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Provider cursor (e.g. Gmail historyId) for future incremental fetch; unused in the on-demand v1.
    sync_cursor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
