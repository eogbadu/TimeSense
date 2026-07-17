from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.repositories.insight_repository import InsightRepository
from app.schemas.insight import WeeklyInsightResponse
from app.services.behavioral_patterns_service import BehavioralPatternsService
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
