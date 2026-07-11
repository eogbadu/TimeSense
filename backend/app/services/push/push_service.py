"""Decide whether to proactively push, and send it.

Rules (from the spec):
  * Only push a recommendation that is `eligible_for_push` (score >= 75 and confidence >= 0.75).
  * Never let the LLM choose — we push the deterministic engine's pick; the LLM only phrases it.
  * Cooldown: don't push within 45 minutes of the last push, and never repeat the same action type
    back-to-back. A high-urgency recommendation of a *different* type may override the cooldown.
  * Never push a fallback ("nothing to do") recommendation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.gateway import LLMGateway
from app.repositories.device_token_repository import DeviceTokenRepository
from app.repositories.push_notification_repository import PushNotificationRepository
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.repositories.task_repository import TaskRepository
from app.services.push.sender import PushSender
from app.services.recommendation.candidate_gather import gather_candidate_tasks
from app.services.recommendation.context_builder import build_user_context
from app.services.recommendation.engine import run_engine
from app.services.recommendation.feedback.build_summary import build_feedback_summary
from app.services.recommendation.maps.factory import get_maps_provider
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.types import Recommendation
from app.services.scheduling_service import SchedulingService

COOLDOWN = timedelta(minutes=45)
OFFER_HORIZON_DAYS = 3


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class ProactivePushService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _in_cooldown(self, last, rec: Recommendation, now: datetime) -> bool:
        if last is None:
            return False
        sent = last.sent_at if last.sent_at.tzinfo else last.sent_at.replace(tzinfo=timezone.utc)
        if now - sent >= COOLDOWN:
            return False
        # Within cooldown. Same type → always suppress. Different type → allow only if urgent.
        if last.action_type == rec.action_type:
            return True
        return rec.urgency != "high"

    async def push_for_user(
        self, user, sender: PushSender, gateway: LLMGateway | None = None,
        now: datetime | None = None,
    ) -> Recommendation | None:
        """Returns the pushed recommendation if a push was sent, else None."""
        now = now or datetime.now(timezone.utc)

        tokens = await DeviceTokenRepository(self.db).list_tokens(user.id)
        if not tokens:
            return None

        candidates, usable, _ = await gather_candidate_tasks(self.db, user, now)
        ctx, _ = await build_user_context(self.db, user, candidates, now, usable)
        maps = MapsSkillService(get_maps_provider())
        summary = await build_feedback_summary(self.db, user.id, now)
        rec = await run_engine(ctx, maps=maps, now=now, feedback=summary, gateway=gateway)

        if rec.domain == "fallback" or not rec.eligible_for_push:
            return None

        push_repo = PushNotificationRepository(self.db)
        last = await push_repo.latest_for_user(user.id)
        if self._in_cooldown(last, rec, now):
            return None

        data = {"type": "recommendation"}
        if rec.related_entity_ids:
            data["task_id"] = rec.related_entity_ids[0]
        delivered = 0
        for token in tokens:
            if await sender.send(token, rec.title, rec.message, collapse_id=rec.action_type, data=data):
                delivered += 1

        await push_repo.record(
            user_id=user.id, action_type=rec.action_type, title=rec.title,
            body=rec.message, sent_at=now, delivered_count=delivered,
        )
        await self.db.commit()
        return rec

    async def offer_time_block_for_user(
        self, user, sender: PushSender, now: datetime | None = None, respect_cooldown: bool = True
    ) -> dict | None:
        """Proactively offer to block a free slot for a high-priority or overdue UNSCHEDULED task.
        Respects the shared cooldown (unless ``respect_cooldown`` is False, for test firing). Returns
        the offer if pushed, else None."""
        now = now or datetime.now(timezone.utc)

        tokens = await DeviceTokenRepository(self.db).list_tokens(user.id)
        if not tokens:
            return None

        if respect_cooldown:
            last = await PushNotificationRepository(self.db).latest_for_user(user.id)
            if last is not None and now - _utc(last.sent_at) < COOLDOWN:
                return None

        pending = await TaskRepository(self.db).list_by_user(user.id, status="pending", limit=200)
        unscheduled = [t for t in pending if t.scheduled_start is None]

        def _overdue(t) -> bool:
            return t.due_at is not None and _utc(t.due_at) < now

        candidates = [t for t in unscheduled if _overdue(t) or t.priority <= 2]
        if not candidates:
            return None
        candidates.sort(key=lambda t: (0 if _overdue(t) else 1, t.priority))
        task = candidates[0]

        tz = user.profile.timezone if user.profile else "UTC"
        ws = user.preferences.work_start_hour if user.preferences else 8
        we = user.preferences.work_end_hour if user.preferences else 21
        duration = task.estimated_minutes or 30

        horizon = now + timedelta(days=OFFER_HORIZON_DAYS)
        events = await SyncedCalendarEventRepository(self.db).list_window(user.id, now, horizon)
        busy = [t for t in pending if t.id != task.id and t.scheduled_start is not None]
        busy += [
            SimpleNamespace(scheduled_start=e.starts_at, scheduled_end=e.ends_at)
            for e in events if not e.all_day
        ]
        slot = SchedulingService(ws, we).find_slot_multiday(
            now, duration, busy, tz, not_before=now, max_days=OFFER_HORIZON_DAYS
        )
        if slot is None:
            return None

        try:
            local = slot.astimezone(ZoneInfo(tz))
        except Exception:
            local = slot
        when = local.strftime("%-I:%M %p")
        if slot.date() == now.date():
            day = "today"
        elif slot.date() == (now + timedelta(days=1)).date():
            day = "tomorrow"
        else:
            day = local.strftime("%A")
        title = f"Block time for “{task.title}”?"
        body = f"You have a free {duration}-min slot {day} at {when}. Want to schedule it?"

        data = {"type": "offer_time_block", "task_id": str(task.id), "task_title": task.title}
        delivered = 0
        for token in tokens:
            if await sender.send(token, title, body, collapse_id="offer_time_block", data=data):
                delivered += 1
        await PushNotificationRepository(self.db).record(
            user_id=user.id, action_type="offer_time_block", title=title, body=body,
            sent_at=now, delivered_count=delivered,
        )
        await self.db.commit()
        return {"task_id": str(task.id), "slot": slot.isoformat(), "delivered": delivered,
                "title": title, "body": body}

    async def send_test(
        self, user, sender: PushSender, gateway: LLMGateway | None = None,
        title: str | None = None, body: str | None = None, now: datetime | None = None,
    ) -> dict:
        """Push to the user's own devices immediately, bypassing eligibility + cooldown — for
        verifying the APNs chain. Uses a {title, body} override if given, else the engine's pick."""
        now = now or datetime.now(timezone.utc)
        tokens = await DeviceTokenRepository(self.db).list_tokens(user.id)
        if not tokens:
            return {"apns_available": sender.available, "delivered": 0, "reason": "no_device"}

        if title and body:
            out_title, out_body, action = title, body, "test"
        else:
            candidates, usable, _ = await gather_candidate_tasks(self.db, user, now)
            ctx, _ = await build_user_context(self.db, user, candidates, now, usable)
            maps = MapsSkillService(get_maps_provider())
            summary = await build_feedback_summary(self.db, user.id, now)
            rec = await run_engine(ctx, maps=maps, now=now, feedback=summary, gateway=gateway)
            out_title, out_body, action = rec.title, rec.message, rec.action_type

        delivered = 0
        for token in tokens:
            if await sender.send(token, out_title, out_body, collapse_id=action):
                delivered += 1
        await PushNotificationRepository(self.db).record(
            user_id=user.id, action_type=action, title=out_title, body=out_body,
            sent_at=now, delivered_count=delivered,
        )
        await self.db.commit()
        return {"apns_available": sender.available, "delivered": delivered,
                "title": out_title, "body": out_body, "action_type": action}
