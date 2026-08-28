from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sleep_wake import SleepWakeEvent
from app.core.localtime import resolve_zone, user_timezone_of
from app.repositories.consent_repository import ConsentRepository
from app.repositories.routine_repository import RoutineAssumptionRepository
from app.repositories.sleep_wake_repository import SleepWakeRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService

LATE_WAKE_THRESHOLD_MINUTES = 45


class HealthConsentRequired(Exception):
    """Raised when the user hasn't granted health_data consent."""


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _minute_of_day(dt: datetime, user_timezone: str | None = None) -> int:
    """Minute-of-day in the USER's timezone.

    RoutineAssumption stores minutes since LOCAL midnight, so comparing a UTC minute-of-day against
    it offset late-wake detection by the user's whole UTC offset — a 7am wake in Tokyo read as 22:00
    the previous day. Now resolved against the stored profile timezone (TIME-283)."""
    local = _utc(dt).astimezone(resolve_zone(user_timezone))
    return local.hour * 60 + local.minute


def _late_wake_minutes(
    wake_time: datetime, assumed_wake_minute: int, user_timezone: str | None = None
) -> int:
    """How many minutes past the assumed wake time this wake_time falls, treating
    the sleep block's end_minute < start_minute wraparound as the normal case."""
    actual = _minute_of_day(wake_time, user_timezone)
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

        user = await UserRepository(self.db).get_by_id(user_id)
        user_tz = user_timezone_of(user) if user is not None else "UTC"

        late_by = _late_wake_minutes(event.wake_time, sleep_routine.end_minute, user_tz)
        if late_by < LATE_WAKE_THRESHOLD_MINUTES:
            return

        # The once-per-day guard also has to be the user's day, not the UTC one.
        wake_day = _utc(event.wake_time).astimezone(resolve_zone(user_tz)).date()
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
