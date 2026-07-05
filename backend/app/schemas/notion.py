from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class NotionConnectIn(BaseModel):
    access_token: str = Field(..., min_length=1)
    workspace_id: str | None = None


class NotionIntegrationOut(BaseModel):
    id: uuid.UUID
    workspace_id: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class NotionScanIn(BaseModel):
    database_id: str = Field(..., min_length=1)
    limit: int = Field(default=50, ge=1, le=100)


class NotionImportItemOut(BaseModel):
    id: uuid.UUID
    database_id: str
    page_id: str
    title: str
    notes: str | None
    due_at: datetime | None
    status: str
    created_task_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotionScanResult(BaseModel):
    scanned: int
    items: list[NotionImportItemOut]
