import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


TaskStatus = Literal["pending", "in_progress", "done", "cancelled"]
TaskSource = Literal["capture", "calendar", "manual", "slack", "teams", "notion"]

MAX_STEPS_PER_TASK = 12


class StepDraft(BaseModel):
    """A step to create. It has no steps of its own, so this schema enforces one level by itself."""

    title: str = Field(..., min_length=1, max_length=500)
    estimated_minutes: int | None = Field(default=None, ge=1, le=1440)


class StepsCreate(BaseModel):
    steps: list[StepDraft] = Field(..., min_length=1, max_length=MAX_STEPS_PER_TASK)
    # Whether the group's steps happen in order. Omitted keeps the group's current setting.
    sequential: bool | None = None


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
    # Steps (TIME-321). A new task either joins an existing group or arrives with steps of its own.
    # It can't do both, because a step can't have steps.
    parent_task_id: uuid.UUID | None = None
    steps: list[StepDraft] = Field(default_factory=list, max_length=MAX_STEPS_PER_TASK)
    steps_sequential: bool = True

    @model_validator(mode="after")
    def _one_level_only(self) -> "TaskCreate":
        if self.parent_task_id is not None and self.steps:
            raise ValueError("A step can't have steps of its own.")
        return self


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
    # Joining a group, or leaving it with an explicit null (TIME-321). Leaving the field out keeps the
    # task where it is; the service tells the two apart from the fields actually sent.
    parent_task_id: uuid.UUID | None = None
    # Where in its group the task goes, 0-based. Out-of-range values are clamped to the ends.
    position: int | None = Field(default=None, ge=0)


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
    # Derived, not client-settable — deliberately absent from TaskUpdate (TIME-316).
    completed_at: datetime | None = None

    # Steps and prerequisites (TIME-320). Derived and additive: a client that ignores them sees the
    # task it always saw. Filled by TaskGraphService; `steps` only where a response nests them.
    parent_task_id: uuid.UUID | None = None
    parent_title: str | None = None
    position: int | None = None
    step_count: int = 0
    open_step_count: int = 0
    blocked_by: list["TaskRef"] = []
    steps: list["TaskResponse"] = []
    suggested_parent: "TaskRef | None" = None

    model_config = {"from_attributes": True}


class TaskRef(BaseModel):
    """Just enough of another task to name it: what this one waits for, or where it may belong."""

    id: uuid.UUID
    title: str


TaskResponse.model_rebuild()
