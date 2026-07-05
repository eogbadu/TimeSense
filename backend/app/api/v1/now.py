from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.recommendation_service import RecommendationService
from app.services.task_scorer import TaskScorer
from app.services.usable_time_service import UsableTimeService
from app.services.user_service import UserService

router = APIRouter(prefix="/now", tags=["now"])


class NowResponse(BaseModel):
    greeting: str
    usable_minutes: int
    best_task: TaskResponse | None
    reason: str | None = None
    alternatives: list[TaskResponse] = []


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
    gateway: LLMGateway = Depends(get_llm_gateway),
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
    best = ranked[0]
    alternatives = ranked[1:3]

    # Richer "Why this?" — the LLM weighs the alternatives, time of day, likely energy, free time,
    # and deadlines; falls back to a deterministic explanation when the LLM is unavailable.
    user_tz = user.profile.timezone if user.profile else "UTC"
    reason = await RecommendationService(gateway).explain_choice(
        best, alternatives, usable_minutes, now, user_tz
    )

    return NowResponse(
        greeting=_greeting(),
        usable_minutes=usable_minutes,
        best_task=TaskResponse.model_validate(best),
        reason=reason,
        alternatives=[TaskResponse.model_validate(t) for t in alternatives],
    )
