"""
Pre-appointment push notifications (TIME-251).

For each upcoming timed appointment we send exactly one push:
- if it has a location and we can compute drive time → 10 minutes before the user needs to leave;
- otherwise → 10 minutes before it starts.

Producer/consumer over the InternalReminder ledger, driven by a Celery poller (see
app/workers/reminder_tasks.py). The producer computes the trigger time once (bounding maps calls)
and stores a pending row; the consumer delivers due rows via APNs. One reminder per appointment,
which makes the whole thing idempotent across polls.

Origin for drive time is the user's current saved place (if we know it) else their Home place; if we
can't compute drive time (no maps key, un-geocodable address, or no origin) we fall back to the
start reminder. The backend never stores live GPS, so this is deliberately best-effort.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import InternalReminder, Task
from app.repositories.device_token_repository import DeviceTokenRepository
from app.repositories.internal_reminder_repository import InternalReminderRepository
from app.repositories.push_notification_repository import PushNotificationRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_location_repository import UserLocationRepository
from app.repositories.user_place_repository import UserPlaceRepository
from app.repositories.user_repository import UserRepository
from app.services.push.factory import get_push_sender
from app.services.recommendation.maps.factory import get_maps_provider
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.types import Coordinates, TravelEstimateRequest

_ACTION_TYPE = "appointment_reminder"


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class AppointmentReminderService:
    LOOKAHEAD = timedelta(hours=3)      # how far ahead we schedule reminders
    LEAD = timedelta(minutes=10)        # notify this long before start / departure
    GRACE = timedelta(minutes=15)       # a due reminder older than this is dropped, not sent

    def __init__(self, db: AsyncSession, sender=None, maps: MapsSkillService | None = None) -> None:
        self.db = db
        self.sender = sender or get_push_sender()
        self.maps = maps or MapsSkillService(get_maps_provider())

    async def run(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        await self._schedule(now)
        return await self._deliver(now)

    # ── Producer: create one pending reminder per new upcoming appointment ─────────

    async def _schedule(self, now: datetime) -> None:
        user_ids = await DeviceTokenRepository(self.db).distinct_user_ids()
        for uid in user_ids:
            user = await UserRepository(self.db).get_by_id(uid)
            if user is None:
                continue
            appts = await TaskRepository(self.db).upcoming_appointments(
                uid, now, now + self.LOOKAHEAD
            )
            if not appts:
                continue
            reminders = InternalReminderRepository(self.db)
            existing = await reminders.task_ids_with_reminders(uid, [t.id for t in appts])
            for task in appts:
                if task.id in existing:
                    continue
                await self._schedule_one(user, task, reminders)
        await self.db.commit()

    async def _schedule_one(self, user, task: Task, reminders: InternalReminderRepository) -> None:
        start = _utc(task.scheduled_start)
        located = bool(task.location_name) or (
            task.location_lat is not None and task.location_lng is not None
        )
        if located:
            travel = await self._travel_minutes(user, task)
            if travel is not None:
                trigger = start - timedelta(minutes=travel) - self.LEAD
                await reminders.create_pending(user.id, task.id, "appointment_departure", trigger)
                return
        await reminders.create_pending(user.id, task.id, "appointment_start", start - self.LEAD)

    async def _travel_minutes(self, user, task: Task) -> float | None:
        if not self.maps.available:
            return None
        dest = await self._destination(task)
        if dest is None:
            return None
        origin = await self._origin(user)
        if origin is None:
            return None
        est = await self.maps.get_travel_estimate(
            TravelEstimateRequest(origin=origin, destination=dest, mode="driving", departure_time="now")
        )
        return est.duration_minutes if est is not None else None

    async def _destination(self, task: Task) -> Coordinates | None:
        if task.location_lat is not None and task.location_lng is not None:
            return Coordinates(latitude=task.location_lat, longitude=task.location_lng)
        if not task.location_name:
            return None
        coords = await self.maps.geocode_address(task.location_name)
        if coords is not None:
            # Persist so future polls (and the engine) don't re-geocode the same address.
            task.location_lat = coords.latitude
            task.location_lng = coords.longitude
            await self.db.flush()
        return coords

    async def _origin(self, user) -> Coordinates | None:
        places = await UserPlaceRepository(self.db).list_for_user(user.id)
        by_name = {p.name.lower(): p for p in places}
        state = await UserLocationRepository(self.db).get_current(user.id)
        if state is not None and state.place_name:
            here = by_name.get(state.place_name.lower())
            if here is not None:
                return Coordinates(latitude=here.latitude, longitude=here.longitude)
        home = by_name.get("home")
        if home is not None:
            return Coordinates(latitude=home.latitude, longitude=home.longitude)
        return None

    # ── Consumer: deliver due reminders ───────────────────────────────────────────

    async def _deliver(self, now: datetime) -> int:
        if not self.sender.available:
            return 0  # APNs not configured — leave rows pending until it is
        reminders = InternalReminderRepository(self.db)
        pushes = PushNotificationRepository(self.db)
        tokens_repo = DeviceTokenRepository(self.db)
        sent = 0
        for reminder in await reminders.due_pending(now):
            if _utc(reminder.trigger_at) < now - self.GRACE:
                await reminders.mark_expired(reminder)
                continue
            task = await self.db.get(Task, reminder.task_id) if reminder.task_id else None
            if task is None or task.status in ("done", "cancelled") or task.scheduled_start is None:
                await reminders.mark_delivered(reminder, now)  # nothing to send; don't retry
                continue
            user = await UserRepository(self.db).get_by_id(reminder.user_id)
            tz = user.profile.timezone if user and user.profile else "UTC"
            title, body = self._copy(reminder, task, tz)
            collapse = f"appt-{reminder.task_id}"[:64]
            data = {"type": _ACTION_TYPE, "task_id": str(reminder.task_id)}
            delivered = 0
            for token in await tokens_repo.list_tokens(reminder.user_id):
                if await self.sender.send(token, title, body, collapse_id=collapse, data=data):
                    delivered += 1
            await pushes.record(reminder.user_id, _ACTION_TYPE, title, body, now, delivered)
            await reminders.mark_delivered(reminder, now)
            sent += 1
        await self.db.commit()
        return sent

    def _copy(self, reminder: InternalReminder, task: Task, tz: str) -> tuple[str, str]:
        start = _utc(task.scheduled_start)
        when = self._fmt(start, tz)
        if reminder.type == "appointment_departure":
            # travel = (start - trigger) - lead, reconstructed so we don't have to store it.
            drive = max(1, round((start - _utc(reminder.trigger_at)).total_seconds() / 60 - self.LEAD.total_seconds() / 60))
            where = task.location_name or "your destination"
            return (
                f"Time to leave for {task.title}",
                f"Head out now — about {drive} min to {where}. Starts {when}.",
            )
        where = f" · {task.location_name}" if task.location_name else ""
        return (f"{task.title} in 10 minutes", f"Starts at {when}{where}.")

    @staticmethod
    def _fmt(dt: datetime, tz: str) -> str:
        try:
            return _utc(dt).astimezone(ZoneInfo(tz)).strftime("%-I:%M %p")
        except Exception:
            return _utc(dt).strftime("%-I:%M %p")
