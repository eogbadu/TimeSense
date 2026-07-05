from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.sleep_wake_repository import SleepWakeRepository
from app.schemas.sleep_wake import SleepWakeEventResponse, SleepWakeLogRequest
from app.services.morning_replan import MorningReplanService
from app.services.user_service import UserService

router = APIRouter(prefix="/sleep-wake", tags=["sleep-wake"])


@router.post("", response_model=SleepWakeEventResponse, status_code=201)
async def log_sleep_wake(
    body: SleepWakeLogRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SleepWakeEventResponse:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    event = await SleepWakeRepository(db).create(
        user_id=user.id,
        wake_time=body.wake_time,
        sleep_start=body.sleep_start,
        source=body.source,
    )
    await MorningReplanService(db).check_and_propose(user.id, body.wake_time)
    return SleepWakeEventResponse.model_validate(event)


@router.get("/today", response_model=SleepWakeEventResponse | None)
async def get_today_sleep_wake(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SleepWakeEventResponse | None:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    event = await SleepWakeRepository(db).get_latest_for_today(user.id, datetime.now(timezone.utc))
    return SleepWakeEventResponse.model_validate(event) if event else None
