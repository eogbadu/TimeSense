from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    channel: str
    title: str
    body: str
    payload: str | None
    status: str
    created_at: datetime
    sent_at: datetime | None
    read_at: datetime | None


class ReplanRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reason: str
    proposed_changes: str
    status: str
    expires_at: datetime
    applied_at: datetime | None
    notification_id: uuid.UUID | None


class ReplanApproveOut(BaseModel):
    applied_changes: list[dict]


class NotificationSendIn(BaseModel):
    type: str
    title: str
    body: str
    channel: str = "in_app"
    payload: dict | None = None


class ReplanProposeIn(BaseModel):
    reason: str
    proposed_changes: list[dict]
