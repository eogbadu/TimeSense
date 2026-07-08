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
    task = await task_svc.create_task(user.id, body)
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


class SuggestedSlotOut(BaseModel):
    fits: bool
    start: datetime | None = None
    end: datetime | None = None
    duration_minutes: int
    message: str


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

    # Busy = today's OTHER scheduled tasks + timed calendar events.
    today_tasks = await TaskRepository(db).list_by_user(user_id=user.id, for_date=now.date(), limit=200)
    events = await SyncedCalendarEventRepository(db).list_window(user.id, now, now + timedelta(hours=16))
    busy = [t for t in today_tasks if t.id != task.id]
    busy += [
        SimpleNamespace(scheduled_start=e.starts_at, scheduled_end=e.ends_at)
        for e in events if not e.all_day
    ]

    slot = SchedulingService(ws, we).find_slot(now, duration, busy, tz, not_before=now)
    if slot is None:
        return SuggestedSlotOut(
            fits=False, duration_minutes=duration,
            message="No open block in your working hours today — try adjusting the time.",
        )
    return SuggestedSlotOut(
        fits=True, start=slot, end=slot + timedelta(minutes=duration),
        duration_minutes=duration, message="Found a free block that avoids your calendar.",
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
    category: str


@router.get("/{task_id}/duration-prompt", response_model=DurationPromptResponse)
async def duration_prompt(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
) -> DurationPromptResponse:
    """Whether to ask 'how long did that take?' after completing this task — only while the
    assistant is still learning this category's typical duration."""
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.get_task(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    ask, category = await TaskDurationEstimator(db).should_ask(user.id, task.title)
    return DurationPromptResponse(ask=ask, category=category)


class DurationFeedback(BaseModel):
    actual_minutes: int = Field(..., ge=1, le=1440)


class DurationFeedbackResponse(BaseModel):
    category: str
    estimated_minutes: int  # the updated learned estimate after this observation


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
    await estimator.record_actual(user.id, task.title, body.actual_minutes)
    minutes, category = await estimator.estimate(user.id, task.title)
    await db.commit()
    return DurationFeedbackResponse(category=category, estimated_minutes=minutes)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> TaskResponse:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.update_task(task_id, user.id, body)
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
