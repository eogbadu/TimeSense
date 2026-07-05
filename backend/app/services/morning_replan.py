from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import ReplanRequest
from app.repositories.routine_repository import RoutineAssumptionRepository
from app.services.notification_service import NotificationService

LATE_WAKE_THRESHOLD_MINUTES = 45


class MorningReplanService:
    """Proposes a replan when the user wakes up meaningfully later than their usual
    sleep RoutineAssumption window. Does not compute an actual new schedule — that's
    future work; this only wires the trigger through the existing approval flow."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.routine_repo = RoutineAssumptionRepository(db)
        self.notification_service = NotificationService(db)

    async def check_and_propose(
        self, user_id: uuid.UUID, wake_time: datetime
    ) -> ReplanRequest | None:
        wake_time = wake_time if wake_time.tzinfo else wake_time.replace(tzinfo=timezone.utc)

        routines = await self.routine_repo.get_or_seed_defaults(user_id)
        sleep_routine = next((r for r in routines if r.routine_type == "sleep"), None)
        if sleep_routine is None:
            return None

        day_start = datetime(wake_time.year, wake_time.month, wake_time.day, tzinfo=timezone.utc)
        expected_wake_time = day_start + timedelta(minutes=sleep_routine.end_minute)

        late_by_minutes = int((wake_time - expected_wake_time).total_seconds() / 60)
        if late_by_minutes <= LATE_WAKE_THRESHOLD_MINUTES:
            return None

        return await self.notification_service.propose_replan(
            user_id=user_id,
            reason=(
                f"You woke up about {late_by_minutes} minutes later than usual. "
                "Want me to adjust today's plan?"
            ),
            proposed_changes=[{"type": "shift_schedule", "delta_minutes": late_by_minutes}],
        )
