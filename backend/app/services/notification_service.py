"""
Notification and Replan Approval Service.

RULE: Replans must never be applied without explicit user approval.
      propose_replan() creates the request; approve_replan() applies it.
"""
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, ReplanRequest
from app.repositories.notification_repository import (
    NotificationEventRepository,
    NotificationRepository,
    ReplanRepository,
)
from app.repositories.routine_repository import RoutineAssumptionRepository
from app.repositories.user_repository import UserRepository

# Placeholder Learning Mode window: reuses the existing 14-day trial length rather than
# inventing a new number. Should become data-driven (decision_log.md) in a future ticket.
LEARNING_PERIOD_DAYS = 14

# gentle: lightest touch (evening check-out only). balanced: both daily check-ins, no
# learning prompts. active_coach: both check-ins + learning prompts, matching the product
# brief's "Active Coach / Learning Mode" framing.
_MODES_WITH_MORNING_CHECKIN = {"balanced", "active_coach"}
_MODES_WITH_LEARNING_PROMPTS = {"active_coach"}


def _format_minute(minute: int) -> str:
    hour, mins = divmod(minute % (24 * 60), 60)
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{mins:02d}{period}"


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notif_repo = NotificationRepository(db)
        self.replan_repo = ReplanRepository(db)
        self.event_repo = NotificationEventRepository(db)
        self.user_repo = UserRepository(db)

    # ── Notifications ─────────────────────────────────────────────────────────

    async def send_notification(
        self,
        user_id: uuid.UUID,
        type: str,
        title: str,
        body: str,
        channel: str = "in_app",
        payload: dict | None = None,
    ) -> Notification:
        """Create and queue a notification. Actual push delivery is handled by Celery."""
        return await self.notif_repo.create(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            channel=channel,
            payload=payload,
        )

    async def list_unread(self, user_id: uuid.UUID) -> list[Notification]:
        return await self.notif_repo.list_unread(user_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        return await self.notif_repo.mark_read(notification_id, user_id)

    # ── Replan approval flow ──────────────────────────────────────────────────

    async def propose_replan(
        self,
        user_id: uuid.UUID,
        reason: str,
        proposed_changes: list[dict],
    ) -> ReplanRequest:
        """
        Propose a schedule change for user approval.
        Also creates an in-app notification linking to the replan.
        """
        replan = await self.replan_repo.create(
            user_id=user_id,
            reason=reason,
            proposed_changes=proposed_changes,
        )
        await self.notif_repo.create(
            user_id=user_id,
            type="replan_request",
            title="Schedule suggestion",
            body=reason,
            channel="in_app",
            payload={"replan_id": str(replan.id)},
        )
        return replan

    async def approve_replan(
        self, request_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[dict]:
        """
        User approves a replan. Returns the applied change list.
        In production this would trigger the Celery task to schedule the changes.
        Raises ValueError if the request is not found, expired, or already handled.
        """
        req = await self.replan_repo.get(request_id, user_id)
        if req is None:
            raise ValueError("Replan request not found.")
        if req.status != "pending":
            raise ValueError(f"Replan already {req.status}.")

        changes = json.loads(req.proposed_changes)
        await self.replan_repo.set_status(
            request_id, "approved", applied_at=datetime.now(UTC)
        )
        return changes

    async def reject_replan(self, request_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        req = await self.replan_repo.get(request_id, user_id)
        if req is None or req.status != "pending":
            return False
        await self.replan_repo.set_status(request_id, "rejected")
        return True

    async def list_pending_replans(self, user_id: uuid.UUID) -> list[ReplanRequest]:
        return await self.replan_repo.list_pending(user_id)

    # ── Notification orchestration: check-ins and learning prompts ─────────────

    async def _notification_mode(self, user_id: uuid.UUID) -> str | None:
        user = await self.user_repo.get_by_id(user_id)
        if user is None or user.preferences is None:
            return None
        return user.preferences.notification_mode

    async def maybe_send_morning_checkin(self, user_id: uuid.UUID) -> Notification | None:
        mode = await self._notification_mode(user_id)
        if mode not in _MODES_WITH_MORNING_CHECKIN:
            return None
        if await self.event_repo.has_sent_today(user_id, "morning_checkin"):
            return None

        notif = await self.send_notification(
            user_id=user_id,
            type="suggestion",
            title="Good morning",
            body="Ready to start your day? Check Now for today's plan.",
        )
        await self.event_repo.record(user_id, "morning_checkin", notif.id)
        return notif

    async def maybe_send_evening_checkout(self, user_id: uuid.UUID) -> Notification | None:
        # All modes get an evening check-out — it's the lightest-touch nudge.
        if await self.event_repo.has_sent_today(user_id, "evening_checkout"):
            return None

        notif = await self.send_notification(
            user_id=user_id,
            type="suggestion",
            title="How did today go?",
            body="Take a moment to check off anything you finished.",
        )
        await self.event_repo.record(user_id, "evening_checkout", notif.id)
        return notif

    async def maybe_send_learning_prompt(
        self, user_id: uuid.UUID, prompt_text: str
    ) -> Notification | None:
        mode = await self._notification_mode(user_id)
        if mode not in _MODES_WITH_LEARNING_PROMPTS:
            return None

        user = await self.user_repo.get_by_id(user_id)
        if user is None or not user.onboarding_complete:
            return None
        if datetime.now(UTC) - _utc(user.created_at) > timedelta(days=LEARNING_PERIOD_DAYS):
            return None
        if await self.event_repo.has_sent_today(user_id, "learning_prompt"):
            return None

        notif = await self.send_notification(
            user_id=user_id,
            type="suggestion",
            title="Quick check",
            body=prompt_text,
        )
        await self.event_repo.record(user_id, "learning_prompt", notif.id)
        return notif

    async def maybe_send_routine_learning_prompt(
        self, user_id: uuid.UUID
    ) -> Notification | None:
        """Concrete built-in learning prompt: confirm the sleep routine if it's still default."""
        routine_repo = RoutineAssumptionRepository(self.db)
        sleep_routine = await routine_repo.get_one(user_id, "sleep")
        if sleep_routine is None or sleep_routine.is_customized:
            return None

        prompt_text = (
            f"Still assuming you sleep {_format_minute(sleep_routine.start_minute)}–"
            f"{_format_minute(sleep_routine.end_minute)}. Sound right?"
        )
        return await self.maybe_send_learning_prompt(user_id, prompt_text)


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
