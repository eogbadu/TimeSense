from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.task import TaskRef


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
    # Notion structure (TIME-326). All additive.
    external_parent_id: str | None = None
    # The title of the page this item is a sub-item of, when TimeSense knows that page.
    parent_title_hint: str | None = None
    # That page's own pending import, when it hasn't been imported yet ("Import both").
    parent_pending_item_id: uuid.UUID | None = None
    # After an import: an open task this looks like part of. Offered, never applied.
    suggested_parent: TaskRef | None = None

    model_config = {"from_attributes": True}


class NotionScanResult(BaseModel):
    scanned: int
    items: list[NotionImportItemOut]
