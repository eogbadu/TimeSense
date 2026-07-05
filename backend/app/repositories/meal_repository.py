from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meal import MEAL_TYPES, MealEvent
from app.repositories.routine_repository import RoutineAssumptionRepository


class MealRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        user_id: uuid.UUID,
        meal_type: str,
        status: str,
        occurred_at: datetime | None = None,
    ) -> MealEvent:
        event = MealEvent(
            user_id=user_id,
            meal_type=meal_type,
            status=status,
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def get_today_status(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> dict[str, str]:
        """Latest logged status per meal today, else inferred 'skipped'/'pending'
        from that meal's RoutineAssumption window (TIME-039)."""
        now = now or datetime.now(timezone.utc)
        day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        result = await self.db.execute(
            select(MealEvent)
            .where(
                MealEvent.user_id == user_id,
                MealEvent.occurred_at >= day_start,
                MealEvent.occurred_at < day_end,
            )
            .order_by(MealEvent.occurred_at.desc())
        )
        latest_by_meal: dict[str, str] = {}
        for event in result.scalars().all():
            latest_by_meal.setdefault(event.meal_type, event.status)

        routines = await RoutineAssumptionRepository(self.db).get_or_seed_defaults(user_id)
        routine_by_type = {r.routine_type: r for r in routines}

        status: dict[str, str] = {}
        for meal_type in MEAL_TYPES:
            if meal_type in latest_by_meal:
                status[meal_type] = latest_by_meal[meal_type]
                continue
            routine = routine_by_type.get(meal_type)
            if routine is None:
                status[meal_type] = "pending"
                continue
            window_end = day_start + timedelta(minutes=routine.end_minute)
            if routine.end_minute < routine.start_minute:
                window_end += timedelta(days=1)  # wraps past midnight
            status[meal_type] = "skipped" if now >= window_end else "pending"
        return status

    async def count_skipped_by_type_in_range(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict[str, int]:
        """Explicitly-logged skips only (status='skipped' rows) in [start, end) — does not
        backfill inferred-but-never-logged skips from get_today_status's live computation."""
        result = await self.db.execute(
            select(MealEvent.meal_type, func.count())
            .where(
                MealEvent.user_id == user_id,
                MealEvent.status == "skipped",
                MealEvent.occurred_at >= start,
                MealEvent.occurred_at < end,
            )
            .group_by(MealEvent.meal_type)
        )
        return {meal_type: count for meal_type, count in result.all()}
