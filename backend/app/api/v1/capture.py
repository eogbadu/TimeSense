import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import capture_rate_limit
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.analytics_service import AnalyticsService
from app.services.capture_service import CaptureService
from app.services.scheduling_service import SchedulingService
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
        return TaskResponse.model_validate(duplicate)

    parser = CaptureService(gateway)
    task_create = await parser.parse(body.raw_input, user_timezone=body.user_timezone, type_hint=body.type_hint)

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
        minutes, _category = await TaskDurationEstimator(db).estimate(user.id, task_create.title)
        task_create.estimated_minutes = minutes

    # A user-set time gets an end block from its duration (so it lands on the timeline correctly).
    if task_create.scheduled_start is not None and task_create.scheduled_end is None and task_create.estimated_minutes:
        task_create.scheduled_end = task_create.scheduled_start + timedelta(minutes=task_create.estimated_minutes)

    # Auto-place the task into the day: if it isn't already timed and is meant for today (or has no
    # date), find the next open slot within working hours. The user can Undo on Today.
    auto_scheduled = False
    now = datetime.now(timezone.utc)
    today = now.date()
    due_today_or_none = (
        task_create.due_at is None
        or (task_create.due_at if task_create.due_at.tzinfo else task_create.due_at.replace(tzinfo=timezone.utc)).date() == today
    )
    if task_create.scheduled_start is None and task_create.estimated_minutes and due_today_or_none:
        today_scheduled = await TaskRepository(db).list_by_user(user_id=user.id, for_date=today, limit=200)
        user_tz = user.profile.timezone if user.profile else "UTC"
        prefs = user.preferences
        scheduler = SchedulingService(
            work_start_hour=prefs.work_start_hour if prefs else 8,
            work_end_hour=prefs.work_end_hour if prefs else 21,
        )
        slot = scheduler.find_slot(
            now, task_create.estimated_minutes, today_scheduled, user_tz
        )
        if slot is not None:
            task_create.scheduled_start = slot
            task_create.scheduled_end = slot + timedelta(minutes=task_create.estimated_minutes)
            auto_scheduled = True

    task = await TaskService(db).create_task(user.id, task_create, auto_scheduled=auto_scheduled)
    await AnalyticsService(db).track(
        "task_captured", user_id=user.id,
        properties={
            "source": task_create.source,
            "had_type_hint": body.type_hint is not None,
            "had_explicit_time": body.scheduled_at is not None or body.due_at is not None,
            "had_location": body.location_name is not None,
            "auto_scheduled": auto_scheduled,
            "was_deduped": False,
        },
    )
    return TaskResponse.model_validate(task)
