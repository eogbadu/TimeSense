from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TeamsConnectIn(BaseModel):
    access_token: str = Field(..., min_length=1)
    tenant_id: str | None = None


class TeamsIntegrationOut(BaseModel):
    id: uuid.UUID
    tenant_id: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class TeamsScanIn(BaseModel):
    conversation_id: str = Field(..., min_length=1)
    limit: int = Field(default=50, ge=1, le=50)


class TeamsActionItemOut(BaseModel):
    id: uuid.UUID
    conversation_id: str
    message_id: str
    source_text: str
    detected_title: str
    detected_priority: int
    detected_estimated_minutes: int | None
    status: str
    created_task_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamsScanResult(BaseModel):
    scanned: int
    detected: list[TeamsActionItemOut]
