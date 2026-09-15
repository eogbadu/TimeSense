import re
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import capture_rate_limit
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.core.localtime import local_today, resolve_zone, user_timezone_of
from app.repositories.task_repository import OPEN_STATUSES, TaskRepository
from app.schemas.task import TaskRef, TaskResponse
from app.services.task_graph import TaskGraphService
from app.services.analytics_service import AnalyticsService
from app.services.capture_service import CaptureService
from app.services.scheduling_service import SchedulingService
from app.services.step_service import MAX_STEPS, StepError, StepService
from app.services.task_autoschedule import autoschedule_task
from app.services.task_duration_service import TaskDurationEstimator
from app.services.task_service import TaskService
from app.services.user_service import UserService

router = APIRouter(prefix="/capture", tags=["capture"])

# Control characters (except tab/newline/CR, which we collapse to a space) — stripped from input.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
# The Capture chips — the only accepted type hints.
_VALID_TYPE_HINTS = {"task", "reminder", "schedule", "errand", "idea"}
# A captured task shouldn't be scheduled/due absurdly far out (or before this millennium).
_MAX_FUTURE_YEARS = 5
# Identical captures within this window are treated as one (double-tap / retry idempotency).
_DEDUPE_WINDOW = timedelta(seconds=60)


class CaptureRequest(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=2000)
    user_timezone: str = Field(default="UTC", max_length=64)
    type_hint: str | None = Field(default=None, max_length=20)
    # Explicit refinements from the Capture inputs — these OVERRIDE whatever the text parsed.
    scheduled_at: datetime | None = None          # a specific date+time (Reminder / timed Schedule)
    due_at: datetime | None = None                # a date without a time (date-only Schedule)
    location_name: str | None = Field(default=None, max_length=160)
    location_lat: float | None = None
    location_lng: float | None = None
    # The "Part of…" chip: the user picked the task this capture belongs to. It wins over anything the
    # text itself suggests (TIME-325).
    parent_task_id: uuid.UUID | None = None

    @field_validator("raw_input")
    @classmethod
    def _clean_raw_input(cls, v: str) -> str:
        """Strip control chars, collapse whitespace, and reject blank-after-strip input
        (min_length=1 alone lets a string of only spaces through)."""
        cleaned = _WHITESPACE.sub(" ", _CONTROL_CHARS.sub("", v)).strip()
        if not cleaned:
            raise ValueError("raw_input cannot be blank")
        return cleaned

    @field_validator("user_timezone")
    @classmethod
    def _valid_timezone(cls, v: str) -> str:
        """Fall back to UTC for an unknown timezone rather than failing the whole capture later."""
        try:
            ZoneInfo(v)
            return v
        except Exception:
            return "UTC"

    @field_validator("type_hint")
    @classmethod
    def _normalize_type_hint(cls, v: str | None) -> str | None:
        """Lower-case and whitelist against the 5 chips; unknown hints are ignored (None)."""
        if v is None:
            return None
        v = v.strip().lower()
        return v if v in _VALID_TYPE_HINTS else None

    @field_validator("location_lat")
    @classmethod
    def _valid_lat(cls, v: float | None) -> float | None:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError("location_lat must be between -90 and 90")
        return v

    @field_validator("location_lng")
    @classmethod
    def _valid_lng(cls, v: float | None) -> float | None:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError("location_lng must be between -180 and 180")
        return v

    @model_validator(mode="after")
    def _sanitize_dates(self) -> "CaptureRequest":
        # Both set → keep the more specific scheduled_at (matches the endpoint's precedence).
        if self.scheduled_at is not None and self.due_at is not None:
            self.due_at = None
        max_year = datetime.now(timezone.utc).year + _MAX_FUTURE_YEARS
        for field in ("scheduled_at", "due_at"):
            dt = getattr(self, field)
            if dt is not None and not (2000 <= dt.year <= max_year):
                raise ValueError(f"{field} is out of a sensible range")
        return self


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(capture_rate_limit)],
)
async def capture(
    body: CaptureRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> TaskResponse:
    user, _ = await UserService(db).get_or_create_user(
        current_user.uid, current_user.email or ""
    )

    # Idempotency: a rapid double-tap / retry with identical text returns the same task rather than
    # creating a duplicate (and skips a needless LLM call).
    duplicate = await TaskRepository(db).find_recent_duplicate(
        user.id, body.raw_input, datetime.now(timezone.utc) - _DEDUPE_WINDOW
    )
    if duplicate is not None:
        await AnalyticsService(db).track(
            "task_captured", user_id=user.id,
            properties={"source": "capture", "was_deduped": True},
        )
        return await TaskGraphService(db).response(duplicate)

    repo = TaskRepository(db)
    # The model may only name one of the user's own open tasks as this capture's parent. When the chip
    # has already picked one, there is nothing left to match (TIME-325).
    open_tasks = [] if body.parent_task_id is not None else await repo.open_tasks_for_matching(user.id)
    parser = CaptureService(gateway)
    task_create = await parser.parse(
        body.raw_input, user_timezone=body.user_timezone, type_hint=body.type_hint,
        open_tasks=open_tasks,
    )
    if body.parent_task_id is not None:
        task_create.parent_task_id = body.parent_task_id
        task_create.steps = []
        task_create.suggested_parent_task_id = None
    if task_create.parent_task_id is not None:
        refusal = await _refusal_to_join(repo, user.id, task_create.parent_task_id)
        if refusal is not None:
            if body.parent_task_id is not None:
                raise HTTPException(status_code=refusal.status_code, detail=refusal.detail)
            # The model named a task that can't take another step (finished, or full). The words are
            # still worth keeping, as a plain task.
            task_create.parent_task_id = None
    grouped = task_create.parent_task_id is not None or bool(task_create.steps)

    # Explicit refinements from the Capture inputs win over the parsed text.
    if body.scheduled_at is not None:
        task_create.scheduled_start = body.scheduled_at
        task_create.scheduled_end = None   # recomputed below once the duration is known
        task_create.due_at = None
    elif body.due_at is not None:
        task_create.due_at = body.due_at
    if body.location_name is not None:
        task_create.location_name = body.location_name
        task_create.location_lat = body.location_lat
        task_create.location_lng = body.location_lng

    # Every task gets a realistic duration: the LLM's explicit estimate wins; otherwise fall back to
    # the duration lookup table (seed defaults, refined by what we've learned about this user).
    if task_create.estimated_minutes is None:
        minutes, _type = await TaskDurationEstimator(db).estimate(
            user.id, task_create.title, task_create.task_type,
            predicted_minutes=task_create.predicted_minutes)
        task_create.estimated_minutes = minutes

    # A user-set time gets an end block from its duration (so it lands on the timeline correctly).
    if task_create.scheduled_start is not None and task_create.scheduled_end is None and task_create.estimated_minutes:
        task_create.scheduled_end = task_create.scheduled_start + timedelta(minutes=task_create.estimated_minutes)

    # Auto-place the task into the day: if it isn't already timed and is meant for today (or has no
    # date), find the next open slot within working hours. The user can Undo on Today.
    auto_scheduled = False
    now = datetime.now(timezone.utc)
    user_tz = user_timezone_of(user)
    today = local_today(user_tz, now)   # the user's local day (TIME-283)
    # Compare the deadline in the user's own zone — see the note in task_autoschedule (TIME-283).
    due_today_or_none = (
        task_create.due_at is None
        or (task_create.due_at if task_create.due_at.tzinfo
            else task_create.due_at.replace(tzinfo=timezone.utc))
        .astimezone(resolve_zone(user_tz)).date() == today
    )
    # A step, or a new group, is placed after it is created instead: only then are its group and what it
    # waits for known, and a parent never takes a slot of its own (TIME-325).
    if (not grouped and task_create.scheduled_start is None and task_create.estimated_minutes
            and due_today_or_none):
        today_scheduled = await TaskRepository(db).list_by_user(
            user_id=user.id, for_date=today, limit=200, user_timezone=user_tz)
        # Calendar meetings are busy too — otherwise a capture can be auto-placed on top of a meeting
        # (mirrors the suggested-slot + push flows, which already avoid the calendar).
        events = await SyncedCalendarEventRepository(db).list_window(user.id, now, now + timedelta(days=1))
        busy = list(today_scheduled) + [
            SimpleNamespace(scheduled_start=e.starts_at, scheduled_end=e.ends_at)
            for e in events if not e.all_day
        ]
        prefs = user.preferences
        scheduler = SchedulingService(
            work_start_hour=prefs.work_start_hour if prefs else 8,
            work_end_hour=prefs.work_end_hour if prefs else 21,
        )
        slot = scheduler.find_slot(
            now, task_create.estimated_minutes, busy, user_tz
        )
        if slot is not None:
            task_create.scheduled_start = slot
            task_create.scheduled_end = slot + timedelta(minutes=task_create.estimated_minutes)
            auto_scheduled = True

    task = await TaskService(db).create_task(
        user.id, task_create, auto_scheduled=auto_scheduled, user_timezone=user_timezone_of(user)
    )
    if grouped:
        # A joining step, or the first step of a new group, is placed like any other capture. It happens
        # only now that the group exists, so auto-placement can respect what the step waits for.
        first = task
        if task_create.steps:
            first = next(
                (s for s in (await repo.steps_for([task.id])).get(task.id, [])
                 if s.status in OPEN_STATUSES),
                None,
            )
        if first is not None:
            await autoschedule_task(db, first)
    await AnalyticsService(db).track(
        "task_captured", user_id=user.id,
        properties={
            "source": task_create.source,
            "had_type_hint": body.type_hint is not None,
            "had_explicit_time": body.scheduled_at is not None or body.due_at is not None,
            "had_location": body.location_name is not None,
            "auto_scheduled": auto_scheduled,
            "was_deduped": False,
            "joined_group": task_create.parent_task_id is not None,
            "step_count": len(task_create.steps),
        },
    )
    graph = TaskGraphService(db)
    response = await (graph.response_with_steps(task) if task_create.steps else graph.response(task))
    if task_create.suggested_parent_task_id is not None and not grouped:
        # Only ever offered. The user taps it to join; nothing is attached here.
        suggested = await repo.get_by_id(task_create.suggested_parent_task_id, user.id)
        if suggested is not None:
            response = response.model_copy(
                update={"suggested_parent": TaskRef(id=suggested.id, title=suggested.title)}
            )
    return response


async def _refusal_to_join(
    repo: TaskRepository, user_id: uuid.UUID, parent_id: uuid.UUID
) -> StepError | None:
    """Why a capture can't become a step of `parent_id`, or None if it can.

    Checked before anything is created, so a refused chip leaves no stray task behind, and a refused
    model match can quietly fall back to a plain task."""
    parent = await repo.get_by_id(parent_id, user_id)
    if parent is None:
        return StepError(404, "Task not found.")
    try:
        StepService.check_can_hold_steps(parent)
    except StepError as exc:
        return exc
    live, _open = (await repo.step_counts([parent.id])).get(parent.id, (0, 0))
    if live >= MAX_STEPS:
        return StepError(422, f"A task can have at most {MAX_STEPS} steps.")
    return None
