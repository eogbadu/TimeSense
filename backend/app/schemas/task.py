import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "in_progress", "done", "cancelled"]
TaskSource = Literal["capture", "calendar", "manual", "slack", "teams", "notion"]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    due_at: datetime | None = None
    source: TaskSource = "manual"
    raw_input: str | None = None
    location_name: str | None = Field(default=None, max_length=160)
    location_lat: float | None = None
    location_lng: float | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
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
    auto_scheduled: bool = False
    raw_input: str | None
    location_name: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
