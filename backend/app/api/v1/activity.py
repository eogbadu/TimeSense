from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.consent_repository import ConsentRepository
from app.repositories.daily_activity_repository import DailyActivityRepository
from app.repositories.hourly_activity_repository import HourlyActivityRepository
from app.repositories.workout_session_repository import WorkoutSessionRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/activity", tags=["activity"])

# Normalized workout types we store (anything else → "other").
_VALID_WORKOUT_TYPES = {"running", "walking", "cycling", "strength", "hiit", "functional", "other"}


async def _require_health_consent(user_id, db: AsyncSession) -> None:
    """Behavioral-data ingest requires health_data consent (mirrors the sleep/events gate)."""
    effective = await ConsentRepository(db).get_effective(user_id)
    if not effective.get("health_data"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Health access requires consent (health_data).",
        )


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


# ── Behavioral data (workouts + hourly steps) — health_data consent required ──────

class WorkoutIn(BaseModel):
    external_id: str
    workout_type: str
    started_at: datetime
    ended_at: datetime
    duration_minutes: int = Field(ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    active_energy_kcal: int | None = Field(default=None, ge=0)


class WorkoutsIn(BaseModel):
    workouts: list[WorkoutIn] = Field(default_factory=list)


class HourlyBucketIn(BaseModel):
    hour_start: datetime
    steps: int = Field(ge=0)


class HourlyIn(BaseModel):
    hours: list[HourlyBucketIn] = Field(default_factory=list)


class IngestResult(BaseModel):
    accepted: int


@router.post("/workouts", response_model=IngestResult)
async def sync_workouts(
    body: WorkoutsIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """Upsert Apple Health workouts (runs, gym sessions …), deduped by their HealthKit id."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    await _require_health_consent(user.id, db)
    repo = WorkoutSessionRepository(db)
    for w in body.workouts:
        wtype = w.workout_type if w.workout_type in _VALID_WORKOUT_TYPES else "other"
        await repo.upsert(
            user_id=user.id, external_id=w.external_id, workout_type=wtype,
            started_at=w.started_at, ended_at=w.ended_at, duration_minutes=w.duration_minutes,
            distance_meters=w.distance_meters, active_energy_kcal=w.active_energy_kcal,
        )
    await db.commit()
    return IngestResult(accepted=len(body.workouts))


@router.post("/hourly", response_model=IngestResult)
async def sync_hourly(
    body: HourlyIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """Upsert per-hour step counts (for the sit-vs-move pattern)."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    await _require_health_consent(user.id, db)
    repo = HourlyActivityRepository(db)
    for h in body.hours:
        await repo.upsert(user_id=user.id, hour_start=h.hour_start, steps=h.steps)
    await db.commit()
    return IngestResult(accepted=len(body.hours))


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
