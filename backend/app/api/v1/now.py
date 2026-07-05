from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
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
    # A local-time-aware nudge (e.g. a gentle wind-down when it's late and nothing is urgent).
    moment: str | None = None


def _local_now(now: datetime, user_timezone: str) -> datetime:
    try:
        return now.astimezone(ZoneInfo(user_timezone))
    except Exception:
        return now


def _greeting(local_now: datetime) -> str:
    hour = local_now.hour
    if hour < 5:
        return "You're up late"
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


def _is_urgent(task, now: datetime) -> bool:
    """Something that shouldn't wait — so we don't suggest winding down over it."""
    if task.due_at is not None:
        due = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
        if due < now or (due - now) <= timedelta(hours=3):
            return True
    return task.priority == 1


def _moment(local_now: datetime, ranked, now: datetime) -> str | None:
    """A local-time-aware nudge. Right now: gently suggest winding down when it's late and nothing
    is urgent, so Now isn't always pushing a task at you at 11pm. Deterministic (no LLM) so it's
    instant and reliable — local time is something we always know, unlike energy."""
    hour = local_now.hour
    late = hour >= 21 or hour < 5
    if not late:
        return None
    if any(_is_urgent(t, now) for t in ranked):
        return None
    return (
        "It's getting late and nothing urgent is left on your plate — "
        "a good moment to wind down and rest. Tomorrow-you will thank you."
    )


async def _ranked_candidates(db: AsyncSession, user, now: datetime):
    """Shared Now ranking: returns (ranked_tasks, usable_minutes)."""
    repo = TaskRepository(db)
    today = now.date()

    today_tasks = await repo.list_by_user(user_id=user.id, for_date=today, limit=200)
    pending = [t for t in today_tasks if t.status in ("pending", "in_progress")]

    all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=200)
    already = {p.id for p in pending}

    overdue = [
        t for t in all_pending
        if t.due_at and t.due_at.replace(tzinfo=timezone.utc) < now and t.id not in already
    ]
    already |= {t.id for t in overdue}
    unscheduled = [t for t in all_pending if t.scheduled_start is None and t.id not in already]

    usable_minutes = UsableTimeService().calculate(today_tasks, anchor=now)

    # Respect recommendation feedback: hide snoozed (active) / "not now" (cooldown) tasks.
    suppressed = await RecommendationFeedbackRepository(db).get_suppressed_task_ids(user.id, now)
    candidates = [t for t in (pending + overdue + unscheduled) if t.id not in suppressed]
    if not candidates:
        return [], usable_minutes
    return TaskScorer().rank(candidates, usable_minutes, now), usable_minutes


@router.get("", response_model=NowResponse)
async def get_now(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NowResponse:
    """Fast Now payload — no LLM. The "Why this?" reason is fetched lazily via /now/why on tap."""
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    now = datetime.now(timezone.utc)
    user_tz = user.profile.timezone if user.profile else "UTC"
    local_now = _local_now(now, user_tz)

    ranked, usable_minutes = await _ranked_candidates(db, user, now)
    if not ranked:
        return NowResponse(
            greeting=_greeting(local_now), usable_minutes=usable_minutes, best_task=None
        )

    return NowResponse(
        greeting=_greeting(local_now),
        usable_minutes=usable_minutes,
        best_task=TaskResponse.model_validate(ranked[0]),
        alternatives=[TaskResponse.model_validate(t) for t in ranked[1:3]],
        moment=_moment(local_now, ranked, now),
    )


class WhyResponse(BaseModel):
    reason: str


@router.get("/why", response_model=WhyResponse)
async def get_now_why(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> WhyResponse:
    """Lazily generate the "Why this?" explanation for a task (LLM, deterministic fallback).

    Computed on demand so the main /now stays instant and we only spend an LLM call when the user
    actually taps "Why this?".
    """
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    now = datetime.now(timezone.utc)
    ranked, usable_minutes = await _ranked_candidates(db, user, now)

    target = next((t for t in ranked if t.id == task_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Task not currently recommended")

    alternatives = [t for t in ranked if t.id != task_id][:2]
    user_tz = user.profile.timezone if user.profile else "UTC"
    reason = await RecommendationService(gateway).explain_choice(
        target, alternatives, usable_minutes, now, user_tz
    )
    return WhyResponse(reason=reason)
