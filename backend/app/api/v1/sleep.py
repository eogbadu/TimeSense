from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.sleep_wake import SleepWakeEventIn, SleepWakeEventResponse
from app.services.morning_replan import HealthConsentRequired, MorningReplanService
from app.services.user_service import UserService

router = APIRouter(prefix="/sleep", tags=["sleep"])


async def _resolve_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.post("/events", response_model=SleepWakeEventResponse)
async def record_sleep_wake_event(
    body: SleepWakeEventIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SleepWakeEventResponse:
    user_id = await _resolve_user_id(current_user, db)
    svc = MorningReplanService(db)
    try:
        event = await svc.record_wake_event(
            user_id=user_id,
            wake_time=body.wake_time,
            sleep_start=body.sleep_start,
            source=body.source,
        )
    except HealthConsentRequired as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return SleepWakeEventResponse.from_event(event)


@router.get("/today", response_model=SleepWakeEventResponse | None)
async def get_today_sleep_wake_event(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SleepWakeEventResponse | None:
    user_id = await _resolve_user_id(current_user, db)
    svc = MorningReplanService(db)
    event = await svc.sleep_repo.get_latest_today(user_id)
    return SleepWakeEventResponse.from_event(event) if event else None
