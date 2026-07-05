from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.repositories.insight_repository import InsightRepository
from app.schemas.insight import WeeklyInsightResponse
from app.services.insights_service import InsightsService
from app.services.user_service import UserService

router = APIRouter(prefix="/insights", tags=["insights"])


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
