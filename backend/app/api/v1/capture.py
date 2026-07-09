from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
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


class CaptureRequest(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=2000)
    user_timezone: str = Field(default="UTC", max_length=64)
    type_hint: str | None = Field(default=None, max_length=20)


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
    parser = CaptureService(gateway)
    task_create = await parser.parse(body.raw_input, user_timezone=body.user_timezone, type_hint=body.type_hint)

    # Every task gets a realistic duration: the LLM's explicit estimate wins; otherwise fall back to
    # the duration lookup table (seed defaults, refined by what we've learned about this user).
    if task_create.estimated_minutes is None:
        minutes, _category = await TaskDurationEstimator(db).estimate(user.id, task_create.title)
        task_create.estimated_minutes = minutes

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
        "task_captured", user_id=user.id, properties={"source": task_create.source}
    )
    return TaskResponse.model_validate(task)
