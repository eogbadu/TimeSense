from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from datetime import date

from app.repositories.insight_repository import InsightRepository
from app.schemas.insight import WeeklyInsightResponse
from app.services.behavioral_patterns_service import BehavioralPatternsService
from app.services.insights_series_service import InsightsSeriesService
from app.services.insights_service import InsightsService
from app.services.user_service import UserService

router = APIRouter(prefix="/insights", tags=["insights"])


class BehavioralPattern(BaseModel):
    category: str        # workouts | movement | driving
    icon: str            # SF Symbol name for the iOS surface
    title: str
    detail: str


class BehavioralPatternsResponse(BaseModel):
    patterns: list[BehavioralPattern]
    based_on_days: int


@router.get("/weekly", response_model=WeeklyInsightResponse)
async def get_latest_weekly_insight(
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> WeeklyInsightResponse:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    svc = InsightsService(db, gateway)
    insight = await svc.get_or_generate_latest(user.id)
    return WeeklyInsightResponse.model_validate(insight)


@router.get("/patterns", response_model=BehavioralPatternsResponse)
async def get_behavioral_patterns(
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BehavioralPatternsResponse:
    """What TimeSense has noticed about your activity — running, gym, sitting vs moving, and commute
    time — from Apple Health workouts/steps and confirmed commutes over the last 4 weeks."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user.profile.timezone if user.profile else "UTC"
    result = await BehavioralPatternsService(db).for_user(user.id, tz)
    return BehavioralPatternsResponse(**result)


@router.get("/history", response_model=list[WeeklyInsightResponse])
async def get_insight_history(
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=8, le=52),
) -> list[WeeklyInsightResponse]:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    insights = await InsightRepository(db).list_recent(user.id, limit=limit)
    return [WeeklyInsightResponse.model_validate(i) for i in insights]


# --- Chart-ready HealthKit series for the Insights charts (TIME-273) --------------------------


class DailyActivityPoint(BaseModel):
    day: date
    steps: int
    exercise_minutes: int


class ActivitySeriesResponse(BaseModel):
    points: list[DailyActivityPoint]


class WeeklyWorkoutPoint(BaseModel):
    week_start: date
    running_miles: float
    running_count: int
    total_count: int


class WorkoutSeriesResponse(BaseModel):
    points: list[WeeklyWorkoutPoint]


class HourlyStepsPoint(BaseModel):
    hour: int            # 0..23, local
    avg_steps: int


class HourlySeriesResponse(BaseModel):
    points: list[HourlyStepsPoint]
    days: int


@router.get("/activity", response_model=ActivitySeriesResponse)
async def get_activity_series(
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=1, le=90),
) -> ActivitySeriesResponse:
    """Daily steps + exercise minutes over the last `days` days (one point per day with data)."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user.profile.timezone if user.profile else "UTC"
    points = await InsightsSeriesService(db).daily_activity(user.id, days, tz)
    return ActivitySeriesResponse(points=[DailyActivityPoint(**p) for p in points])


@router.get("/workouts", response_model=WorkoutSeriesResponse)
async def get_workout_series(
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    weeks: int = Query(default=8, ge=1, le=52),
) -> WorkoutSeriesResponse:
    """Per-week running miles + run/total workout counts over the last `weeks` weeks."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user.profile.timezone if user.profile else "UTC"
    points = await InsightsSeriesService(db).weekly_workouts(user.id, weeks, tz)
    return WorkoutSeriesResponse(points=[WeeklyWorkoutPoint(**p) for p in points])


@router.get("/hourly", response_model=HourlySeriesResponse)
async def get_hourly_series(
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=7, ge=1, le=30),
) -> HourlySeriesResponse:
    """Average steps by hour-of-day (0-23) over the last `days` days — the sit-vs-move profile."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user.profile.timezone if user.profile else "UTC"
    points = await InsightsSeriesService(db).hourly_steps(user.id, days, tz)
    return HourlySeriesResponse(points=[HourlyStepsPoint(**p) for p in points], days=days)
