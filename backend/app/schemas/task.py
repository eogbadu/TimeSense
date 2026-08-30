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
    # Baseline-library classification (TIME-284/285). Callers rarely set these by hand — capture and
    # the import paths fill them in — but they're accepted so a client can correct a wrong guess.
    task_type: str | None = Field(default=None, max_length=40)
    difficulty: str | None = Field(default=None, max_length=16)
    # The LLM's own guess at how long this specific task will take (TIME-305). Transient: it seeds
    # the estimate as a PRIOR and is not stored as a column of its own.
    predicted_minutes: int | None = Field(default=None, ge=1, le=1440)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    due_at: datetime | None = None
    # A user correcting a wrong classification is a real signal, not just a display fix — it feeds
    # the per-type duration learning (TIME-286).
    task_type: str | None = Field(default=None, max_length=40)
    difficulty: str | None = Field(default=None, max_length=16)


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
    task_type: str | None = None
    difficulty: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
