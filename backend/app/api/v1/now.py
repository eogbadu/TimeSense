from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.task_scorer import TaskScorer
from app.services.usable_time_service import UsableTimeService
from app.services.user_service import UserService

router = APIRouter(prefix="/now", tags=["now"])


class NowResponse(BaseModel):
    greeting: str
    usable_minutes: int
    best_task: TaskResponse | None
    reason: str | None = None


def _build_reason(task, usable_minutes: int, now: datetime) -> str:
    """A calm, human explanation of why this task is recommended — deterministic, no LLM."""
    parts: list[str] = []
    if task.due_at is not None:
        due = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
        if due < now:
            parts.append("it's overdue")
        elif due.date() == now.date():
            parts.append("it's due today")
        elif (due.date() - now.date()).days <= 6:
            parts.append(f"it's due {due.strftime('%A')}")
    if task.priority and task.priority <= 2:
        parts.append("it's high priority")
    if task.estimated_minutes and usable_minutes and task.estimated_minutes <= usable_minutes:
        parts.append(f"it fits your {usable_minutes} free minutes")

    if not parts:
        return "It's your best next step right now."
    if len(parts) == 1:
        body = parts[0]
    elif len(parts) == 2:
        body = f"{parts[0]} and {parts[1]}"
    else:
        body = ", ".join(parts[:-1]) + f", and {parts[-1]}"
    return "Recommended because " + body + "."


def _greeting() -> str:
    hour = datetime.now(timezone.utc).hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@router.get("", response_model=NowResponse)
async def get_now(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NowResponse:
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    repo = TaskRepository(db)
    today = datetime.now(timezone.utc).date()

    # Candidates: today's pending/in_progress tasks + overdue tasks
    today_tasks = await repo.list_by_user(user_id=user.id, for_date=today, limit=200)
    pending = [t for t in today_tasks if t.status in ("pending", "in_progress")]

    all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=200)
    now = datetime.now(timezone.utc)
    already = {p.id for p in pending}

    # Overdue: past due_at, still pending.
    overdue = [
        t for t in all_pending
        if t.due_at and t.due_at.replace(tzinfo=timezone.utc) < now and t.id not in already
    ]
    already |= {t.id for t in overdue}

    # Unscheduled pending tasks (e.g. just captured — no scheduled_start, no due date) are valid
    # "do it whenever" candidates; otherwise a freshly captured task would never surface in Now.
    unscheduled = [t for t in all_pending if t.scheduled_start is None and t.id not in already]

    usable_minutes = UsableTimeService().calculate(today_tasks, anchor=now)

    # Respect recommendation feedback: hide tasks the user snoozed (still active) or dismissed with
    # "not now" (within cooldown), so those actions actually change the best task.
    suppressed = await RecommendationFeedbackRepository(db).get_suppressed_task_ids(user.id, now)
    candidates = [t for t in (pending + overdue + unscheduled) if t.id not in suppressed]
    if not candidates:
        return NowResponse(greeting=_greeting(), usable_minutes=usable_minutes, best_task=None)

    ranked = TaskScorer().rank(candidates, usable_minutes, now)
    return NowResponse(
        greeting=_greeting(),
        usable_minutes=usable_minutes,
        best_task=TaskResponse.model_validate(ranked[0]),
        reason=_build_reason(ranked[0], usable_minutes, now),
    )
