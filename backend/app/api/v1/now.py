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
from app.models.recommendation_event import RecommendationEvent
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.recommendation_explainer import build_explanation, compute_confidence
from app.services.recommendation_service import RecommendationService
from app.services.scheduling_service import SchedulingService
from app.services.task_scorer import TaskScorer
from app.services.usable_time_service import UsableTimeService
from app.services.user_service import UserService

router = APIRouter(prefix="/now", tags=["now"])


class Feasibility(BaseModel):
    fits: bool
    message: str
    suggested_slot: datetime | None = None


class NowResponse(BaseModel):
    greeting: str
    usable_minutes: int
    best_task: TaskResponse | None
    reason: str | None = None
    alternatives: list[TaskResponse] = []
    # Inline confidence for the best task (0–1), matching the "Why This Recommendation?" sheet.
    confidence: float | None = None
    # A local-time-aware nudge (e.g. a gentle wind-down when it's late and nothing is urgent).
    moment: str | None = None
    # Set when the best task can't be finished before it's due (with a suggested slot).
    feasibility: Feasibility | None = None


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
    """Shared Now ranking: returns (ranked_tasks, usable_minutes, today_scheduled_tasks)."""
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

    user_tz = user.profile.timezone if user.profile else "UTC"
    usable_minutes = UsableTimeService().calculate(today_tasks, anchor=now, user_timezone=user_tz)

    # Respect recommendation feedback: hide snoozed (active) / "not now" (cooldown) tasks.
    suppressed = await RecommendationFeedbackRepository(db).get_suppressed_task_ids(user.id, now)
    candidates = [t for t in (pending + overdue + unscheduled) if t.id not in suppressed]
    if not candidates:
        return [], usable_minutes, today_tasks
    return TaskScorer().rank(candidates, usable_minutes, now), usable_minutes, today_tasks


def _fmt_local(dt: datetime, tz_name: str) -> str:
    from zoneinfo import ZoneInfo as _ZI
    try:
        local = dt.astimezone(_ZI(tz_name))
    except Exception:
        local = dt
    return local.strftime("%-I:%M %p")


def _feasibility(best, today_tasks, now: datetime, user_tz: str, work_hours: tuple[int, int]) -> "Feasibility | None":
    """Warn when the best task can't be finished before it's due within working hours, and suggest
    the next realistic slot."""
    if best.due_at is None or not best.estimated_minutes:
        return None
    due = best.due_at if best.due_at.tzinfo else best.due_at.replace(tzinfo=timezone.utc)
    if due <= now:
        return None  # already overdue — handled by ranking, not a feasibility warning
    sched = SchedulingService(work_start_hour=work_hours[0], work_end_hour=work_hours[1])
    free_before = sched.free_minutes_before(due, now, today_tasks, user_tz)
    if free_before >= best.estimated_minutes:
        return None
    slot = sched.find_slot(now, best.estimated_minutes, today_tasks, user_tz, not_before=due)
    due_str = _fmt_local(due, user_tz)
    if slot is not None:
        msg = (
            f"This needs about {best.estimated_minutes} min, but you only have {free_before} free "
            f"before it's due at {due_str}. Next realistic slot: {_fmt_local(slot, user_tz)}."
        )
    else:
        msg = (
            f"This needs about {best.estimated_minutes} min, but you only have {free_before} free "
            f"before it's due at {due_str}, and there's no open slot left today."
        )
    return Feasibility(fits=False, message=msg, suggested_slot=slot)


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

    ranked, usable_minutes, today_tasks = await _ranked_candidates(db, user, now)
    if not ranked:
        return NowResponse(
            greeting=_greeting(local_now), usable_minutes=usable_minutes, best_task=None
        )

    return NowResponse(
        greeting=_greeting(local_now),
        usable_minutes=usable_minutes,
        best_task=TaskResponse.model_validate(ranked[0]),
        alternatives=[TaskResponse.model_validate(t) for t in ranked[1:3]],
        confidence=compute_confidence(ranked[0], usable_minutes, len(ranked[1:3]), now),
        moment=_moment(local_now, ranked, now),
        feasibility=_feasibility(
            ranked[0], today_tasks, now, user_tz,
            (user.preferences.work_start_hour, user.preferences.work_end_hour)
            if user.preferences else (8, 21),
        ),
    )


class RecommendedAction(BaseModel):
    task_id: uuid.UUID
    title: str
    recommended_duration_minutes: int | None = None


class DecisionFactor(BaseModel):
    name: str
    rating: str


class AlternativeConsidered(BaseModel):
    task_id: uuid.UUID
    title: str
    reason_not_selected: str


class Signal(BaseModel):
    name: str          # Calendar / Time of day / Location / Priority / Energy
    detail: str
    available: bool     # True → we have the signal (green check); False → not connected yet


class WhyResponse(BaseModel):
    """Rich, structured 'Why This Recommendation?' explanation."""
    recommended_action: RecommendedAction
    confidence: float
    context_used: list[str]
    decision_factors: list[DecisionFactor]
    signals: list[Signal] = []
    alternatives_considered: list[AlternativeConsidered]
    summary: str
    # Backward-compatible one-liner (older clients read `reason`).
    reason: str


@router.get("/why", response_model=WhyResponse)
async def get_now_why(
    task_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> WhyResponse:
    """Lazily build the structured recommendation explanation for a task.

    Pipeline: pull context (calendar/time/health/location/tasks) → normalize → score the candidates →
    LLM summary (deterministic fallback) → return the explanation and store an audit event. Computed
    on demand so the main /now stays instant.
    """
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    now = datetime.now(timezone.utc)
    ranked, _usable, today_tasks = await _ranked_candidates(db, user, now)

    target = next((t for t in ranked if t.id == task_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Task not currently recommended")

    alternatives = [t for t in ranked if t.id != task_id][:2]
    user_tz = user.profile.timezone if user.profile else "UTC"

    explanation = await build_explanation(
        db, user, target, alternatives, today_tasks, now, user_tz, gateway
    )

    # Audit trail (best-effort — never block the response on it).
    try:
        db.add(RecommendationEvent(
            user_id=user.id, task_id=target.id,
            confidence=explanation["confidence"], explanation=explanation,
        ))
        await db.commit()
    except Exception:
        await db.rollback()

    return WhyResponse(reason=explanation["summary"], **explanation)
