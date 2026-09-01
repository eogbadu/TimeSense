from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.localtime import local_today, user_timezone_of
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.models.recommendation_feedback import RecommendationFeedback
from app.repositories.meal_repository import MealRepository
from app.repositories.recommendation_event_repository import RecommendationEventRepository
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.learned_preferences_service import LearnedPreferencesService
from app.services.recommendation_service import RecommendationService
from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
from app.services.recommendation.swap_context import ORIGIN_EXPLICIT, build_swap_context
from app.services.user_service import UserService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendationItem(BaseModel):
    task: TaskResponse
    why: str


class RecommendationResponse(BaseModel):
    best: RecommendationItem | None
    alternatives: list[TaskResponse]
    usable_minutes: int
    skipped_meals: list[str]


@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> RecommendationResponse:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")

    repo = TaskRepository(db)
    now = datetime.now(timezone.utc)
    # "Today" is the user's local day, not the server's UTC day (TIME-283).
    user_tz = user_timezone_of(user)
    today = local_today(user_tz, now)

    all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=500)
    today_tasks = await repo.list_by_user(user_id=user.id, for_date=today, limit=200,
                                          user_timezone=user_tz)

    suppressed_ids = await RecommendationFeedbackRepository(db).get_suppressed_task_ids(user.id, now)
    # Calendar meetings are commitments, not to-dos — drop them from the candidate pool (they still
    # block time via today_tasks / the synced events below).
    all_pending = [t for t in all_pending if t.id not in suppressed_ids and t.source != "calendar"]

    # Calendar meetings block usable time alongside scheduled tasks.
    events = await SyncedCalendarEventRepository(db).list_window(user.id, now, now + timedelta(days=1))

    svc = RecommendationService(gateway)
    best_task, alternatives, usable_minutes, why = await svc.recommend(
        tasks=all_pending,
        scheduled_tasks=today_tasks,
        now=now,
        user_timezone=user_tz,
        events=events,
    )

    meal_status = await MealRepository(db).get_today_status(user.id, now, user_timezone=user_tz)
    skipped_meals = [meal for meal, status in meal_status.items() if status == "skipped"]

    return RecommendationResponse(
        best=RecommendationItem(
            task=TaskResponse.model_validate(best_task),
            why=why or "",
        ) if best_task else None,
        alternatives=[TaskResponse.model_validate(t) for t in alternatives],
        usable_minutes=usable_minutes,
        skipped_meals=skipped_meals,
    )


class LearnedPreference(BaseModel):
    kind: Literal["prefers", "avoids", "avoids_at_time"]
    label: str
    detail: str
    part_of_day: str | None = None


class LearnedPreferencesResponse(BaseModel):
    preferences: list[LearnedPreference]
    based_on: int          # how many of your reactions this is drawn from


@router.get("/learned", response_model=LearnedPreferencesResponse, summary="What TimeSense has learned")
async def get_learned_preferences(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> LearnedPreferencesResponse:
    """Plain-language learned preferences from your accept/reject history — a transparency surface."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user.profile.timezone if user.profile else "UTC"
    result = await LearnedPreferencesService(db).for_user(user.id, tz)
    return LearnedPreferencesResponse(**result)


class FeedbackRequest(BaseModel):
    task_id: uuid.UUID
    # agree = "yes, this is the right next thing" (positive, non-suppressing).
    # disagree = "not this one" → the task is demoted (not hidden) so a different rec surfaces.
    signal: Literal["done", "snooze", "not_now", "agree", "disagree"]
    snooze_until: datetime | None = None
    # Optional reason for a disagree — drives reason-based learning (TIME-271).
    reason: Literal["wrong_time", "not_priority", "not_relevant", "too_big"] | None = None
    # Optional: the impression this feedback reacts to (from NowResponse). Links outcome→impression.
    recommendation_event_id: uuid.UUID | None = None


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    signal: str


@router.post("/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Record user reaction (agree/disagree/done/snooze/not_now) to a recommendation."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")

    # Validate task belongs to user
    repo = TaskRepository(db)
    task = await repo.get_by_id(body.task_id, user_id=user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if body.signal == "done":
        await repo.update(body.task_id, user.id, status="done")

    # Acting on a pinned task means the user's choice has been honoured — the pin has done its job
    # and shouldn't keep overriding the engine for the rest of its window (TIME-294).
    if body.signal in ("done", "not_now", "snooze", "disagree"):
        await RecommendationSwapRepository(db).release_pin(user.id, body.task_id)

    fb = RecommendationFeedback(
        user_id=user.id,
        task_id=body.task_id,
        signal=body.signal,
        snooze_until=body.snooze_until,
        reason=body.reason if body.signal == "disagree" else None,
    )
    db.add(fb)
    await db.flush()

    # Link the outcome back to the impression it reacted to, if the client sent one.
    if body.recommendation_event_id is not None:
        await RecommendationEventRepository(db).set_outcome(
            body.recommendation_event_id, user.id, outcome=body.signal, feedback_id=fb.id
        )

    await db.commit()
    await db.refresh(fb)

    return FeedbackResponse(id=fb.id, signal=fb.signal)


class SwapRequest(BaseModel):
    """"Not that — this instead." The user rejects the recommendation AND names the replacement."""

    rejected_task_id: uuid.UUID
    chosen_task_id: uuid.UUID
    reason: Literal["wrong_time", "not_priority", "not_relevant", "too_big"] | None = None
    recommendation_event_id: uuid.UUID | None = None


class SwapResponse(BaseModel):
    id: uuid.UUID
    chosen_task_id: uuid.UUID
    pinned_until: datetime | None


@router.post("/swap", response_model=SwapResponse, status_code=201)
async def submit_swap(
    body: SwapRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SwapResponse:
    """Record a swap and make the user's choice the recommendation.

    This is additive: the ordinary disagree+reason feedback is still written exactly as before, so
    every existing learning path keeps working. What the swap adds is the PAIR — a rejection says a
    pick was wrong, a swap says what would have been right, in a known context (TIME-294).

    The chosen task is pinned for a few hours. Recording the preference without honouring it would
    be the worst of both worlds: the user tells the app what they want and watches it argue back.
    """
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")

    repo = TaskRepository(db)
    rejected = await repo.get_by_id(body.rejected_task_id, user_id=user.id)
    chosen = await repo.get_by_id(body.chosen_task_id, user_id=user.id)
    if rejected is None or chosen is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if rejected.id == chosen.id:
        raise HTTPException(status_code=400, detail="Cannot swap a task for itself")

    now = datetime.now(timezone.utc)
    tz = user_timezone_of(user)

    # The disagree is recorded through the existing path, unchanged.
    fb = RecommendationFeedback(
        user_id=user.id, task_id=rejected.id, signal="disagree", reason=body.reason,
    )
    db.add(fb)
    await db.flush()
    if body.recommendation_event_id is not None:
        await RecommendationEventRepository(db).set_outcome(
            body.recommendation_event_id, user.id, outcome="disagree", feedback_id=fb.id
        )

    # Shared with the silent completion path (TIME-316) so the two can never drift apart on the
    # exact keys `_swap_signals` reads.
    snapshot = await build_swap_context(
        db, user, rejected, chosen, now, tz, origin=ORIGIN_EXPLICIT
    )

    swap = await RecommendationSwapRepository(db).create(
        user_id=user.id,
        rejected_task_id=rejected.id,
        chosen_task_id=chosen.id,
        reason=body.reason,
        context_snapshot=snapshot,
        now=now,
    )
    await db.commit()
    await db.refresh(swap)
    return SwapResponse(id=swap.id, chosen_task_id=chosen.id, pinned_until=swap.pinned_until)
