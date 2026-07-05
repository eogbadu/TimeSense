from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SlackConnectIn(BaseModel):
    access_token: str = Field(..., min_length=1)
    team_id: str | None = None


class SlackIntegrationOut(BaseModel):
    id: uuid.UUID
    team_id: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class SlackScanIn(BaseModel):
    channel: str = Field(..., min_length=1)
    limit: int = Field(default=50, ge=1, le=200)


class SlackActionItemOut(BaseModel):
    id: uuid.UUID
    channel: str
    message_ts: str
    source_text: str
    detected_title: str
    detected_priority: int
    detected_estimated_minutes: int | None
    status: str
    created_task_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SlackScanResult(BaseModel):
    scanned: int
    detected: list[SlackActionItemOut]
