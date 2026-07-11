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
from app.repositories.consent_repository import ConsentRepository
from app.repositories.recommendation_event_repository import RecommendationEventRepository
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.recommendation.candidate_gather import gather_candidate_tasks
from app.services.recommendation.candidates.generate import generate_candidate_actions
from app.services.recommendation.context_builder import build_user_context
from app.services.recommendation.engine import run_engine
from app.services.recommendation.feedback.apply_feedback import apply_feedback_adjustments
from app.services.recommendation.feedback.build_summary import build_feedback_summary
from app.services.recommendation.maps.factory import get_maps_provider
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.selection.rank import rank_candidates
from app.services.recommendation_explainer import build_explanation, compute_confidence
from app.services.recommendation_service import RecommendationService
from app.services.scheduling_service import SchedulingService
from app.services.usable_time_service import UsableTimeService
from app.services.user_service import UserService

router = APIRouter(prefix="/now", tags=["now"])


class Feasibility(BaseModel):
    fits: bool
    message: str
    suggested_slot: datetime | None = None


class NowContextCards(BaseModel):
    """Glanceable dashboard signals for the Now screen — real data only; any field may be null when
    we don't have that signal yet (the client hides those cards)."""
    next_event_title: str | None = None
    next_event_at: datetime | None = None
    next_event_in_minutes: int | None = None
    tasks_due_today: int = 0
    tasks_completed_today: int = 0
    energy_level: str | None = None   # high | moderate | low (from sleep)
    sleep_hours: float | None = None
    current_place: str | None = None
    steps: int | None = None          # HealthKit — today
    steps_goal: int = 10000
    active_energy_kcal: int | None = None
    exercise_minutes: int | None = None
    inactive_minutes: int | None = None   # minutes since last meaningful movement


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
    # Glanceable dashboard signals (calendar / tasks / energy / nearby).
    context: NowContextCards | None = None
    # The impression id for this shown best-task — echo it back on feedback to link the outcome.
    recommendation_event_id: uuid.UUID | None = None


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


async def _gather_candidate_tasks(db: AsyncSession, user, now: datetime):
    """Shared candidate gathering (also used by the proactive-push service)."""
    return await gather_candidate_tasks(db, user, now)


async def _ranked_candidates(db: AsyncSession, user, now: datetime):
    """Shared Now ranking: returns (ranked_tasks, usable_minutes, today_scheduled_tasks)."""
    candidates, usable_minutes, today_tasks = await _gather_candidate_tasks(db, user, now)
    if not candidates:
        return [], usable_minutes, today_tasks, None
    ranked, best_meta = await _engine_rank_tasks(db, user, candidates, now, usable_minutes)
    return ranked, usable_minutes, today_tasks, best_meta


async def _engine_rank_tasks(
    db: AsyncSession, user, candidates: list, now: datetime, usable_minutes: int
) -> tuple[list, dict | None]:
    """Order candidate Tasks using the deterministic recommendation engine (task + location domains),
    then map the engine's ranked candidates back to the ORM Tasks. Any candidate the engine didn't
    surface is safety-appended so best_task is never dropped."""
    ctx, task_map = await build_user_context(db, user, candidates, now, usable_minutes)
    maps = MapsSkillService(get_maps_provider())
    actions = await generate_candidate_actions(ctx, maps, now)
    # Personalize: boost/penalize action types the user consistently accepts/rejects (from telemetry).
    summary = await build_feedback_summary(db, user.id, now)
    actions = [apply_feedback_adjustments(a, summary) for a in actions]
    ranked = rank_candidates(actions, ctx)

    ordered: list = []
    seen: set = set()
    best_meta: dict | None = None
    for scored in ranked:
        c = scored.candidate
        if c.domain not in ("task", "location") or not c.related_entity_ids:
            continue
        tid = c.related_entity_ids[0]
        if tid in task_map and tid not in seen:
            if best_meta is None:  # metadata of the top-ranked pick, for the impression log
                best_meta = {"action_type": c.type, "domain": c.domain, "score": scored.score}
            ordered.append(task_map[tid])
            seen.add(tid)
    for t in candidates:  # safety net — keep any task the engine didn't rank
        if str(t.id) not in seen:
            ordered.append(t)
    return ordered, best_meta


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


def _u(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _context_cards(db, user, now: datetime, user_tz: str) -> NowContextCards:
    """Populate the glanceable dashboard from real signals — calendar, tasks, sleep, location."""
    from datetime import time as _time
    from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
    from app.repositories.user_location_repository import UserLocationRepository
    from app.repositories.sleep_wake_repository import SleepWakeRepository

    try:
        tz = ZoneInfo(user_tz)
    except Exception:
        tz = timezone.utc
    local = now.astimezone(tz)
    start_utc = datetime.combine(local.date(), _time(0, 0), tzinfo=tz).astimezone(timezone.utc)
    end_utc = start_utc + timedelta(days=1)

    # Next timed calendar event
    events = await SyncedCalendarEventRepository(db).list_window(user.id, now, now + timedelta(hours=24))
    upcoming = sorted((e for e in events if not e.all_day and _u(e.starts_at) > now),
                      key=lambda e: _u(e.starts_at))
    nxt = upcoming[0] if upcoming else None

    # Tasks due today (pending, due or scheduled today) + completions today
    pending = await TaskRepository(db).list_by_user(user_id=user.id, status="pending", limit=500)
    def _today(dt) -> bool:
        return dt is not None and start_utc <= _u(dt) < end_utc
    due_today = sum(1 for t in pending if _today(t.due_at) or _today(t.scheduled_start))
    completed = await TaskRepository(db).count_completed_in_range(user.id, start_utc, end_utc)

    # Energy from last night's sleep
    sleep = await SleepWakeRepository(db).get_latest_today(user.id)
    hours = None
    energy = None
    if sleep is not None:
        if sleep.sleep_start is not None:
            hours = round((_u(sleep.wake_time) - _u(sleep.sleep_start)).total_seconds() / 3600, 1)
        energy = ("high" if (hours or 0) >= 7.5 else "moderate" if (hours or 0) >= 6 else "low") \
            if hours is not None else "moderate"

    # Current place
    place = await UserLocationRepository(db).get_current(user.id, now)
    place_name = place.place_name if place is not None else None

    # Today's HealthKit activity (steps / active energy / exercise)
    from app.repositories.daily_activity_repository import DailyActivityRepository
    activity = await DailyActivityRepository(db).get_for_day(user.id, local.date())

    return NowContextCards(
        next_event_title=nxt.title if nxt else None,
        next_event_at=_u(nxt.starts_at) if nxt else None,
        next_event_in_minutes=int((_u(nxt.starts_at) - now).total_seconds() / 60) if nxt else None,
        tasks_due_today=due_today,
        tasks_completed_today=completed,
        energy_level=energy,
        sleep_hours=hours,
        current_place=place_name,
        steps=activity.steps if activity is not None else None,
        active_energy_kcal=activity.active_energy_kcal if activity is not None else None,
        exercise_minutes=activity.exercise_minutes if activity is not None else None,
        inactive_minutes=activity.inactive_minutes if activity is not None else None,
    )


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

    ranked, usable_minutes, today_tasks, best_meta = await _ranked_candidates(db, user, now)
    context = await _context_cards(db, user, now, user_tz)
    if not ranked:
        return NowResponse(
            greeting=_greeting(local_now), usable_minutes=usable_minutes, best_task=None,
            context=context,
        )

    confidence = compute_confidence(ranked[0], usable_minutes, len(ranked[1:3]), now)
    event_id = await _record_now_impression(db, user, ranked[0], confidence, best_meta)
    return NowResponse(
        greeting=_greeting(local_now),
        usable_minutes=usable_minutes,
        context=context,
        best_task=TaskResponse.model_validate(ranked[0]),
        alternatives=[TaskResponse.model_validate(t) for t in ranked[1:3]],
        confidence=confidence,
        moment=_moment(local_now, ranked, now),
        feasibility=_feasibility(
            ranked[0], today_tasks, now, user_tz,
            (user.preferences.work_start_hour, user.preferences.work_end_hour)
            if user.preferences else (8, 21),
        ),
        recommendation_event_id=event_id,
    )


async def _record_now_impression(db, user, best_task, confidence: float, best_meta: dict | None):
    """Best-effort, consent-gated impression of the shown best task. Never blocks /now; returns the
    impression id (or None) so the client can echo it on feedback to link the outcome."""
    try:
        effective = await ConsentRepository(db).get_effective(user.id)
        if not effective.get("analytics"):
            return None
        meta = best_meta or {}
        event = await RecommendationEventRepository(db).record_impression(
            user_id=user.id, task_id=best_task.id, surface="now", confidence=confidence,
            action_type=meta.get("action_type"), domain=meta.get("domain"),
            score=meta.get("score"), rank=0,
        )
        await db.commit()
        return event.id
    except Exception:
        await db.rollback()
        return None


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
    ranked, _usable, today_tasks, _meta = await _ranked_candidates(db, user, now)

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
        await RecommendationEventRepository(db).record_impression(
            user_id=user.id, task_id=target.id, surface="now_why",
            confidence=explanation["confidence"], explanation=explanation,
        )
        await db.commit()
    except Exception:
        await db.rollback()

    return WhyResponse(reason=explanation["summary"], **explanation)


# --- Full engine recommendation (any domain, with LLM text) ------------------------------------


class PlaceOut(BaseModel):
    name: str
    type: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    open_now: bool | None = None


class TravelOut(BaseModel):
    distance_miles: float
    duration_minutes: float
    mode: str
    total_required_minutes: float | None = None
    fits_free_block: bool | None = None


class AlternativeOut(BaseModel):
    title: str
    action_type: str
    domain: str
    reason_codes: list[str]
    related_task_id: uuid.UUID | None = None


class NowRecommendationResponse(BaseModel):
    """The complete engine decision — any domain (task, health, routine, planning, location, …),
    with LLM-phrased text. `related_task_id` is set when the pick is backed by a real task."""
    id: str
    timestamp: str
    title: str
    message: str
    explanation: str
    action_type: str
    domain: str
    confidence: float
    score: float
    urgency: str
    estimated_minutes: int
    reason_codes: list[str]
    eligible_for_push: bool
    related_task_id: uuid.UUID | None = None
    destination_place: PlaceOut | None = None
    travel: TravelOut | None = None
    alternatives: list[AlternativeOut] = []


def _task_id_in(entity_ids: list[str], task_map: dict) -> uuid.UUID | None:
    for tid in entity_ids:
        if tid in task_map:
            return task_map[tid].id
    return None


@router.get("/recommendation", response_model=NowRecommendationResponse)
async def get_now_recommendation(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> NowRecommendationResponse:
    """Run the full deterministic engine (all domains) and phrase the result with the LLM. Unlike
    /now (task-centric, fast, no LLM), this can recommend cross-domain actions like prep-for-meeting
    or wind-down. The LLM only writes the text — it never changes the chosen action."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    now = datetime.now(timezone.utc)

    candidates, usable_minutes, _ = await _gather_candidate_tasks(db, user, now)
    ctx, task_map = await build_user_context(db, user, candidates, now, usable_minutes)
    maps = MapsSkillService(get_maps_provider())
    summary = await build_feedback_summary(db, user.id, now)
    rec = await run_engine(ctx, maps=maps, now=now, feedback=summary, gateway=gateway)

    place = None
    if rec.destination_place is not None:
        p = rec.destination_place
        place = PlaceOut(name=p.name, type=p.type, address=p.address,
                         latitude=p.coordinates.latitude, longitude=p.coordinates.longitude,
                         open_now=p.open_now)
    travel = None
    if rec.travel_estimate is not None:
        te = rec.travel_estimate
        feas = rec.travel_feasibility
        travel = TravelOut(distance_miles=te.distance_miles, duration_minutes=te.duration_minutes,
                           mode=te.mode,
                           total_required_minutes=feas.total_required_minutes if feas else None,
                           fits_free_block=feas.fits_in_current_free_block if feas else None)

    alternatives = [
        AlternativeOut(title=a.title, action_type=a.type, domain=a.domain,
                       reason_codes=list(a.reason_codes),
                       related_task_id=_task_id_in(a.related_entity_ids, task_map))
        for a in rec.alternatives
    ]

    related_task_id = _task_id_in(rec.related_entity_ids, task_map)

    # Audit only task-backed picks (the audit model requires a task_id).
    if related_task_id is not None:
        await RecommendationEventRepository(db).record_impression(
            user_id=user.id, task_id=related_task_id, surface="now_recommendation",
            confidence=rec.confidence, action_type=rec.action_type, domain=rec.domain,
            score=rec.score, explanation={"reason_codes": list(rec.reason_codes)},
        )
        await db.commit()

    return NowRecommendationResponse(
        id=rec.id, timestamp=rec.timestamp, title=rec.title, message=rec.message,
        explanation=rec.explanation, action_type=rec.action_type, domain=rec.domain,
        confidence=rec.confidence, score=rec.score, urgency=rec.urgency,
        estimated_minutes=rec.estimated_minutes, reason_codes=list(rec.reason_codes),
        eligible_for_push=rec.eligible_for_push, related_task_id=related_task_id,
        destination_place=place, travel=travel, alternatives=alternatives,
    )
