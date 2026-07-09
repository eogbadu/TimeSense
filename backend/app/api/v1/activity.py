from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.daily_activity_repository import DailyActivityRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/activity", tags=["activity"])


class DailyActivityIn(BaseModel):
    steps: int = Field(ge=0, default=0)
    active_energy_kcal: int | None = Field(default=None, ge=0)
    exercise_minutes: int | None = Field(default=None, ge=0)
    inactive_minutes: int | None = Field(default=None, ge=0)
    day: date | None = None   # defaults to the user's local today


class DailyActivityOut(BaseModel):
    day: date
    steps: int
    active_energy_kcal: int | None = None
    exercise_minutes: int | None = None
    inactive_minutes: int | None = None


def _local_today(user_tz: str) -> date:
    try:
        return datetime.now(ZoneInfo(user_tz)).date()
    except Exception:
        return datetime.now(timezone.utc).date()


@router.post("", response_model=DailyActivityOut)
async def sync_activity(
    body: DailyActivityIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DailyActivityOut:
    """Upsert today's HealthKit activity (steps, active energy, exercise minutes)."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user.profile.timezone if user.profile else "UTC"
    day = body.day or _local_today(tz)
    row = await DailyActivityRepository(db).upsert(
        user_id=user.id, day=day, steps=body.steps,
        active_energy_kcal=body.active_energy_kcal, exercise_minutes=body.exercise_minutes,
        inactive_minutes=body.inactive_minutes,
    )
    await db.commit()
    return DailyActivityOut(
        day=row.day, steps=row.steps,
        active_energy_kcal=row.active_energy_kcal, exercise_minutes=row.exercise_minutes,
        inactive_minutes=row.inactive_minutes,
    )


@router.get("/today", response_model=DailyActivityOut | None)
async def get_today_activity(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DailyActivityOut | None:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user.profile.timezone if user.profile else "UTC"
    row = await DailyActivityRepository(db).get_for_day(user.id, _local_today(tz))
    if row is None:
        return None
    return DailyActivityOut(
        day=row.day, steps=row.steps,
        active_energy_kcal=row.active_energy_kcal, exercise_minutes=row.exercise_minutes,
        inactive_minutes=row.inactive_minutes,
    )
