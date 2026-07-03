"""
Notification and Replan Approval Service.

RULE: Replans must never be applied without explicit user approval.
      propose_replan() creates the request; approve_replan() applies it.
"""
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, ReplanRequest
from app.repositories.notification_repository import NotificationRepository, ReplanRepository


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notif_repo = NotificationRepository(db)
        self.replan_repo = ReplanRepository(db)

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
