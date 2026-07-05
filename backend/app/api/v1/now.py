from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
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

    candidates = pending + overdue + unscheduled
    if not candidates:
        return NowResponse(greeting=_greeting(), usable_minutes=usable_minutes, best_task=None)

    ranked = TaskScorer().rank(candidates, usable_minutes, now)
    return NowResponse(
        greeting=_greeting(),
        usable_minutes=usable_minutes,
        best_task=TaskResponse.model_validate(ranked[0]),
    )
