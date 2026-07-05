from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sleep_wake import SleepWakeEvent
from app.repositories.consent_repository import ConsentRepository
from app.repositories.routine_repository import RoutineAssumptionRepository
from app.repositories.sleep_wake_repository import SleepWakeRepository
from app.services.notification_service import NotificationService

LATE_WAKE_THRESHOLD_MINUTES = 45


class HealthConsentRequired(Exception):
    """Raised when the user hasn't granted health_data consent."""


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _minute_of_day(dt: datetime) -> int:
    """UTC-only simplification: treats UTC minute-of-day as local minute-of-day,
    matching RoutineAssumption/UsableTimeService/CommuteService until real
    per-user timezone handling exists (see known_issues.md)."""
    local = _utc(dt)
    return local.hour * 60 + local.minute


def _late_wake_minutes(wake_time: datetime, assumed_wake_minute: int) -> int:
    """How many minutes past the assumed wake time this wake_time falls, treating
    the sleep block's end_minute < start_minute wraparound as the normal case."""
    actual = _minute_of_day(wake_time)
    delta = actual - assumed_wake_minute
    if delta < -12 * 60:
        # actual wrapped past midnight relative to the assumed minute-of-day
        delta += 24 * 60
    return delta


class MorningReplanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sleep_repo = SleepWakeRepository(db)
        self.consent_repo = ConsentRepository(db)
        self.routine_repo = RoutineAssumptionRepository(db)
        self.notification_service = NotificationService(db)

    async def record_wake_event(
        self,
        user_id: uuid.UUID,
        wake_time: datetime,
        sleep_start: datetime | None = None,
        source: str = "manual",
    ) -> SleepWakeEvent:
        effective_consent = await self.consent_repo.get_effective(user_id)
        if not effective_consent.get("health_data"):
            raise HealthConsentRequired("health_data consent not granted")

        event = await self.sleep_repo.create(
            user_id=user_id, wake_time=wake_time, sleep_start=sleep_start, source=source
        )

        await self._maybe_propose_replan(user_id, event)
        return event

    async def _maybe_propose_replan(self, user_id: uuid.UUID, event: SleepWakeEvent) -> None:
        sleep_routine = await self.routine_repo.get_one(user_id, "sleep")
        if sleep_routine is None:
            routines = await self.routine_repo.get_or_seed_defaults(user_id)
            sleep_routine = next(r for r in routines if r.routine_type == "sleep")

        late_by = _late_wake_minutes(event.wake_time, sleep_routine.end_minute)
        if late_by < LATE_WAKE_THRESHOLD_MINUTES:
            return

        wake_day = _utc(event.wake_time).date()
        if await self.sleep_repo.has_replan_on_date(user_id, wake_day):
            return

        replan = await self.notification_service.propose_replan(
            user_id=user_id,
            reason=(
                f"You woke up about {late_by} minutes later than usual — "
                "want to shift your morning schedule?"
            ),
            proposed_changes=[{"type": "shift_morning_tasks", "delay_minutes": late_by}],
        )
        await self.sleep_repo.set_replan_request(event.id, replan.id)
