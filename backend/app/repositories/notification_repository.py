import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, ReplanRequest
from app.models.notification_event import NotificationEvent

REPLAN_TTL_HOURS = 12


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        type: str,
        title: str,
        body: str,
        channel: str = "in_app",
        payload: dict | None = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            type=type,
            channel=channel,
            title=title,
            body=body,
            payload=json.dumps(payload) if payload else None,
        )
        self.db.add(notif)
        await self.db.flush()
        return notif

    async def list_unread(self, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
        result = await self.db.execute(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status.in_(["pending", "sent"]),
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            return False
        notif.status = "read"
        notif.read_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def mark_sent(self, notification_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notif = result.scalar_one_or_none()
        if notif:
            notif.status = "sent"
            notif.sent_at = datetime.now(UTC)
            await self.db.flush()


class ReplanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        reason: str,
        proposed_changes: list[dict],
        notification_id: uuid.UUID | None = None,
    ) -> ReplanRequest:
        request = ReplanRequest(
            user_id=user_id,
            reason=reason,
            proposed_changes=json.dumps(proposed_changes),
            expires_at=datetime.now(UTC) + timedelta(hours=REPLAN_TTL_HOURS),
            notification_id=notification_id,
        )
        self.db.add(request)
        await self.db.flush()
        return request

    async def get(self, request_id: uuid.UUID, user_id: uuid.UUID) -> ReplanRequest | None:
        result = await self.db.execute(
            select(ReplanRequest).where(
                ReplanRequest.id == request_id,
                ReplanRequest.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, user_id: uuid.UUID) -> list[ReplanRequest]:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(ReplanRequest).where(
                ReplanRequest.user_id == user_id,
                ReplanRequest.status == "pending",
                ReplanRequest.expires_at > now,
            ).order_by(ReplanRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def set_status(
        self, request_id: uuid.UUID, status: str, applied_at: datetime | None = None
    ) -> ReplanRequest | None:
        result = await self.db.execute(
            select(ReplanRequest).where(ReplanRequest.id == request_id)
        )
        req = result.scalar_one_or_none()
        if req is None:
            return None
        req.status = status
        if applied_at:
            req.applied_at = applied_at
        await self.db.flush()
        return req


class NotificationEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        user_id: uuid.UUID,
        event_type: str,
        notification_id: uuid.UUID | None = None,
    ) -> NotificationEvent:
        event = NotificationEvent(
            user_id=user_id, event_type=event_type, notification_id=notification_id
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def has_sent_today(self, user_id: uuid.UUID, event_type: str) -> bool:
        today = datetime.now(UTC).date()
        result = await self.db.execute(
            select(NotificationEvent).where(
                NotificationEvent.user_id == user_id,
                NotificationEvent.event_type == event_type,
            )
        )
        events = result.scalars().all()
        return any(_utc(e.created_at).date() == today for e in events)


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
