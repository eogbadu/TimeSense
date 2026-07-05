from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.meal_repository import MealRepository
from app.schemas.meal import MealEventResponse, MealLogRequest, MealTodayResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("", response_model=MealEventResponse, status_code=201)
async def log_meal(
    body: MealLogRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MealEventResponse:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    event = await MealRepository(db).log(user.id, body.meal_type, body.status, body.occurred_at)
    return MealEventResponse.model_validate(event)


@router.get("/today", response_model=MealTodayResponse)
async def get_today_meals(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MealTodayResponse:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    status = await MealRepository(db).get_today_status(user.id, datetime.now(timezone.utc))
    return MealTodayResponse(**status)
