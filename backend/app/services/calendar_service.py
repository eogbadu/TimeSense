"""
Calendar service.

RULE: create_event() and delete_event() must never be called without an approval token.
      Callers must call request_event_creation() first, get user approval, then call approve_action().
"""
import json
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.calendar_base import CalendarEvent, CalendarEventCreate, CalendarProvider
from app.integrations.google_calendar import GoogleCalendarProvider
from app.integrations.microsoft_calendar import MicrosoftCalendarProvider
from app.models.calendar import CalendarIntegration, PendingCalendarAction
from app.repositories.calendar_repository import (
    CalendarIntegrationRepository,
    PendingCalendarActionRepository,
)
from app.repositories.consent_repository import ConsentRepository

_PROVIDERS: dict[str, CalendarProvider] = {
    "google": GoogleCalendarProvider(),
    "microsoft": MicrosoftCalendarProvider(),
}


def get_provider(name: str) -> CalendarProvider:
    try:
        return _PROVIDERS[name]
    except KeyError:
        raise ValueError(f"Unknown calendar provider: {name}") from None


class CalendarService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integration_repo = CalendarIntegrationRepository(db)
        self.action_repo = PendingCalendarActionRepository(db)

    # ── Token management ──────────────────────────────────────────────────────

    async def connect(
        self,
        user_id: uuid.UUID,
        provider: str,
        access_token: str,
        refresh_token: str | None = None,
        token_expires_at: datetime | None = None,
        calendar_id: str = "primary",
    ) -> CalendarIntegration:
        integration = await self.integration_repo.upsert(
            user_id=user_id,
            provider=provider,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            calendar_id=calendar_id,
        )
        # Connecting a calendar is the user granting us calendar visibility — record the consent so the
        # Privacy panel and any calendar_details gate reflect it (TIME-256).
        await ConsentRepository(self.db).ensure_granted(user_id, "calendar_details", source="calendar_oauth")
        return integration

    async def disconnect(self, user_id: uuid.UUID, provider: str) -> bool:
        return await self.integration_repo.deactivate(user_id, provider)

    async def get_integration(self, user_id: uuid.UUID, provider: str) -> CalendarIntegration | None:
        return await self.integration_repo.get_active(user_id, provider)

    # ── Read (no approval needed) ─────────────────────────────────────────────

    async def list_events(
        self,
        user_id: uuid.UUID,
        provider: str,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        integration = await self.integration_repo.get_active(user_id, provider)
        if integration is None:
            return []
        cal_provider = get_provider(provider)
        return await cal_provider.list_events(
            access_token=integration.access_token,
            start=start,
            end=end,
            calendar_id=integration.calendar_id,
        )

    # ── Write (approval required) ─────────────────────────────────────────────

    async def request_event_creation(
        self,
        user_id: uuid.UUID,
        provider: str,
        event: CalendarEventCreate,
    ) -> PendingCalendarAction:
        """Queue a calendar write for user approval. Returns the pending action to show in UI."""
        return await self.action_repo.create(user_id=user_id, provider=provider, event=event)

    async def approve_action(self, action_id: uuid.UUID, user_id: uuid.UUID) -> CalendarEvent:
        """
        Execute a previously requested calendar write after user approval.
        Raises ValueError if action is not found, expired, or already handled.
        """
        action = await self.action_repo.get(action_id, user_id)
        if action is None:
            raise ValueError("Action not found.")
        if action.status != "pending":
            raise ValueError(f"Action already {action.status}.")

        integration = await self.integration_repo.get_active(user_id, action.provider)
        if integration is None:
            await self.action_repo.set_status(action_id, "rejected")
            raise ValueError("Calendar integration not connected.")

        payload = json.loads(action.event_payload)
        event = CalendarEventCreate(
            title=payload["title"],
            start=datetime.fromisoformat(payload["start"]),
            end=datetime.fromisoformat(payload["end"]),
            location=payload.get("location"),
            description=payload.get("description"),
            calendar_id=payload.get("calendar_id", "primary"),
        )

        cal_provider = get_provider(action.provider)
        created = await cal_provider.create_event(
            access_token=integration.access_token,
            event=event,
        )

        await self.action_repo.set_status(action_id, "approved", created_event_id=created.event_id)
        return created

    async def reject_action(self, action_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        action = await self.action_repo.get(action_id, user_id)
        if action is None or action.status != "pending":
            return False
        await self.action_repo.set_status(action_id, "rejected")
        return True

    async def list_pending_actions(self, user_id: uuid.UUID) -> list[PendingCalendarAction]:
        return await self.action_repo.list_pending(user_id)
