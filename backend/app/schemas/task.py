import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "in_progress", "done", "cancelled"]
TaskSource = Literal["capture", "calendar", "manual", "slack", "teams"]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    estimated_minutes: int | None = Field(default=None, ge=1)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    due_at: datetime | None = None
    source: TaskSource = "manual"
    raw_input: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    estimated_minutes: int | None = Field(default=None, ge=1)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    due_at: datetime | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    status: str
    priority: int
    estimated_minutes: int | None
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    due_at: datetime | None
    source: str
    raw_input: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
