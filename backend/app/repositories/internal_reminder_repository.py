from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import InternalReminder


class InternalReminderRepository:
    """Ledger for scheduled per-task reminders (TIME-251). One row per appointment: the producer
    creates a `pending` row with a `trigger_at`, the consumer delivers it and marks it `delivered`
    (or `expired` if it's too stale to send). Existence of a row is the idempotency guard."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def task_ids_with_reminders(
        self, user_id: uuid.UUID, task_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        """Which of the given tasks already have a reminder (so we never schedule twice)."""
        if not task_ids:
            return set()
        rows = await self.db.execute(
            select(InternalReminder.task_id).where(
                InternalReminder.user_id == user_id,
                InternalReminder.task_id.in_(task_ids),
            )
        )
        return {tid for (tid,) in rows.all() if tid is not None}

    async def create_pending(
        self, user_id: uuid.UUID, task_id: uuid.UUID, reminder_type: str, trigger_at: datetime
    ) -> InternalReminder:
        row = InternalReminder(
            user_id=user_id, task_id=task_id, type=reminder_type,
            trigger_at=trigger_at, status="pending",
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def due_pending(self, now: datetime) -> list[InternalReminder]:
        """Pending reminders whose trigger time has arrived (oldest first)."""
        rows = await self.db.execute(
            select(InternalReminder)
            .where(InternalReminder.status == "pending", InternalReminder.trigger_at <= now)
            .order_by(InternalReminder.trigger_at)
        )
        return list(rows.scalars().all())

    async def mark_delivered(self, reminder: InternalReminder, now: datetime | None = None) -> None:
        reminder.status = "delivered"
        reminder.delivered_at = now or datetime.now(timezone.utc)
        await self.db.flush()

    async def mark_expired(self, reminder: InternalReminder) -> None:
        reminder.status = "expired"
        await self.db.flush()
