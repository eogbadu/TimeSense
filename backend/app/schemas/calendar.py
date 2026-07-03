from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CalendarEventOut(BaseModel):
    event_id: str | None
    title: str
    start: datetime
    end: datetime
    calendar_id: str
    location: str | None
    description: str | None
    provider: str


class CalendarEventCreateIn(BaseModel):
    title: str
    start: datetime
    end: datetime
    calendar_id: str = "primary"
    location: str | None = None
    description: str | None = None


class CalendarIntegrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    calendar_id: str
    is_active: bool
    token_expires_at: datetime | None


class PendingCalendarActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    calendar_id: str
    event_payload: str
    status: str
    expires_at: datetime
    created_event_id: str | None


class CalendarConnectIn(BaseModel):
    provider: str
    access_token: str
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    calendar_id: str = "primary"
