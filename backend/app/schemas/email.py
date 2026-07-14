from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EmailScanIn(BaseModel):
    max_results: int = Field(default=25, ge=1, le=50)


class EmailActionItemOut(BaseModel):
    id: uuid.UUID
    message_id: str
    thread_id: str | None
    subject: str
    sender: str | None
    source_text: str
    detected_title: str
    detected_priority: int
    detected_estimated_minutes: int | None
    status: str
    created_task_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailScanResult(BaseModel):
    scanned: int
    detected: list[EmailActionItemOut]
