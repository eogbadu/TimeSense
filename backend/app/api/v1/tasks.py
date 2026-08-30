from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.scheduling_service import SchedulingService
from app.services.task_duration_service import TaskDurationEstimator
from app.services.task_library import is_known_type
from app.core.localtime import user_timezone_of
from app.services.task_service import TaskService
from app.services.user_service import UserService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db)


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> TaskResponse:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.create_task(user.id, body, user_timezone=user_timezone_of(user))
    return TaskResponse.model_validate(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
    date_filter: date | None = Query(default=None, alias="date"),
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> list[TaskResponse]:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    tasks = await task_svc.list_tasks(user.id, status=status_filter, for_date=date_filter)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> TaskResponse:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.get_task(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return TaskResponse.model_validate(task)


SLOT_SEARCH_DAYS = 3


class SuggestedSlotOut(BaseModel):
    fits: bool
    start: datetime | None = None
    end: datetime | None = None
    duration_minutes: int
    message: str
    day: str | None = None   # today | tomorrow | later this week


@router.get("/{task_id}/suggested-slot", response_model=SuggestedSlotOut)
async def suggested_slot(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> SuggestedSlotOut:
    """Propose the earliest free block for this task today — inside working hours and around both
    scheduled tasks AND the user's calendar events — so a suggested time never lands on a meeting.
    The user still approves the actual time in the native editor."""
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.get_task(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    now = datetime.now(timezone.utc)
    tz = user.profile.timezone if user.profile else "UTC"
    ws = user.preferences.work_start_hour if user.preferences else 8
    we = user.preferences.work_end_hour if user.preferences else 21
    duration = task.estimated_minutes or 30

    # Busy = OTHER scheduled tasks + timed calendar events over the search horizon.
    horizon = now + timedelta(days=SLOT_SEARCH_DAYS)
    all_pending = await TaskRepository(db).list_by_user(user_id=user.id, status="pending", limit=500)
    events = await SyncedCalendarEventRepository(db).list_window(user.id, now, horizon)
    busy = [t for t in all_pending if t.id != task.id and t.scheduled_start is not None]
    busy += [
        SimpleNamespace(scheduled_start=e.starts_at, scheduled_end=e.ends_at)
        for e in events if not e.all_day
    ]

    slot = SchedulingService(ws, we).find_slot_multiday(
        now, duration, busy, tz, not_before=now, max_days=SLOT_SEARCH_DAYS
    )
    if slot is None:
        return SuggestedSlotOut(
            fits=False, duration_minutes=duration,
            message="No open block in the next few days — try adjusting the time.",
        )
    day = "today" if slot.date() == now.date() else (
        "tomorrow" if slot.date() == (now + timedelta(days=1)).date() else "later this week"
    )
    return SuggestedSlotOut(
        fits=True, start=slot, end=slot + timedelta(minutes=duration),
        duration_minutes=duration, day=day,
        message=f"Found a free block {day} that avoids your calendar.",
    )


@router.post("/{task_id}/unschedule", response_model=TaskResponse)
async def unschedule_task(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Undo an auto-placed time — clears the scheduled slot so the task becomes untimed again."""
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.get_task(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    task.scheduled_start = None
    task.scheduled_end = None
    task.auto_scheduled = False
    await db.commit()
    await db.refresh(task)
    return TaskResponse.model_validate(task)


class DurationPromptResponse(BaseModel):
    ask: bool
    # `category` predates TIME-286 and is kept for existing clients; both fields now carry the
    # library task_type.
    category: str
    task_type: str


@router.get("/{task_id}/duration-prompt", response_model=DurationPromptResponse)
async def duration_prompt(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> DurationPromptResponse:
    """Whether to ask 'how long did that take?' after completing this task — only while the
    assistant is still learning this TYPE's typical duration, and never for a task it couldn't
    classify (an unclassified answer teaches nothing transferable)."""
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.get_task(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    ask, task_type = await TaskDurationEstimator(db).should_ask(user.id, task.title, task.task_type)
    return DurationPromptResponse(ask=ask, category=task_type, task_type=task_type)


class DurationFeedback(BaseModel):
    actual_minutes: int = Field(..., ge=1, le=1440)
    # Optional correction of a wrong classification, sent alongside the real duration (TIME-287).
    task_type: str | None = Field(default=None, max_length=40)


class DurationFeedbackResponse(BaseModel):
    # `category` is the pre-TIME-286 field name, kept so existing clients don't break; it now carries
    # the library task_type, which `task_type` also reports under the clearer name.
    category: str
    task_type: str
    estimated_minutes: int  # the updated blended estimate after this observation


@router.post("/{task_id}/duration-feedback", response_model=DurationFeedbackResponse)
async def duration_feedback(
    task_id: UUID,
    body: DurationFeedback,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> DurationFeedbackResponse:
    """Record how long a task actually took, teaching the per-user duration estimate."""
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.get_task(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    estimator = TaskDurationEstimator(db)
    # A client may also correct the classification at the same time — a wrong type would otherwise
    # teach the wrong bucket, so the correction is applied BEFORE the observation is recorded.
    if body.task_type and is_known_type(body.task_type):
        task.task_type = body.task_type
    task_type = await estimator.record_actual(
        user.id, task.title, body.actual_minutes, task.task_type,
        task_id=task.id, estimated_minutes=task.estimated_minutes,
    )
    minutes, task_type = await estimator.estimate(user.id, task.title, task.task_type)
    await db.commit()
    return DurationFeedbackResponse(
        category=task_type, task_type=task_type, estimated_minutes=minutes
    )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> TaskResponse:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.update_task(task_id, user.id, body, user_timezone=user_timezone_of(user))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> None:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    deleted = await task_svc.delete_task(task_id, user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
