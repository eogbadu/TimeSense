import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.calendar_base import CalendarEventCreate
from app.models.calendar import CalendarIntegration, PendingCalendarAction

PENDING_ACTION_TTL_HOURS = 24


class CalendarIntegrationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active(self, user_id: uuid.UUID, provider: str) -> CalendarIntegration | None:
        result = await self.db.execute(
            select(CalendarIntegration).where(
                CalendarIntegration.user_id == user_id,
                CalendarIntegration.provider == provider,
                CalendarIntegration.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        provider: str,
        access_token: str,
        refresh_token: str | None = None,
        token_expires_at: datetime | None = None,
        calendar_id: str = "primary",
    ) -> CalendarIntegration:
        existing = await self.get_active(user_id, provider)
        if existing:
            existing.access_token = access_token
            if refresh_token:
                existing.refresh_token = refresh_token
            existing.token_expires_at = token_expires_at
            existing.calendar_id = calendar_id
            await self.db.flush()
            return existing
        integration = CalendarIntegration(
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            calendar_id=calendar_id,
        )
        self.db.add(integration)
        await self.db.flush()
        return integration

    async def deactivate(self, user_id: uuid.UUID, provider: str) -> bool:
        integration = await self.get_active(user_id, provider)
        if integration is None:
            return False
        integration.is_active = False
        await self.db.flush()
        return True


class PendingCalendarActionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        provider: str,
        event: CalendarEventCreate,
    ) -> PendingCalendarAction:
        action = PendingCalendarAction(
            user_id=user_id,
            provider=provider,
            calendar_id=event.calendar_id,
            event_payload=json.dumps({
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "location": event.location,
                "description": event.description,
                "calendar_id": event.calendar_id,
            }),
            expires_at=datetime.now(UTC) + timedelta(hours=PENDING_ACTION_TTL_HOURS),
        )
        self.db.add(action)
        await self.db.flush()
        return action

    async def get(self, action_id: uuid.UUID, user_id: uuid.UUID) -> PendingCalendarAction | None:
        result = await self.db.execute(
            select(PendingCalendarAction).where(
                PendingCalendarAction.id == action_id,
                PendingCalendarAction.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending(self, user_id: uuid.UUID) -> list[PendingCalendarAction]:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(PendingCalendarAction).where(
                PendingCalendarAction.user_id == user_id,
                PendingCalendarAction.status == "pending",
                PendingCalendarAction.expires_at > now,
            ).order_by(PendingCalendarAction.created_at.desc())
        )
        return list(result.scalars().all())

    async def set_status(
        self,
        action_id: uuid.UUID,
        status: str,
        created_event_id: str | None = None,
    ) -> PendingCalendarAction | None:
        result = await self.db.execute(
            select(PendingCalendarAction).where(PendingCalendarAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        if action is None:
            return None
        action.status = status
        if created_event_id:
            action.created_event_id = created_event_id
        await self.db.flush()
        return action
