"""
Sync OAuth-connected calendars (Google / Outlook) into SyncedCalendarEvent (TIME-277).

Calendars connected in-app via OAuth were previously only fetched live for a display list, so the
Smart Plan, usable-time, capture, and the recommendation engine never saw them — only the device
(EventKit) calendars, which the iOS app pushes to SyncedCalendarEvent directly. This service pulls
each connected OAuth calendar's upcoming events and upserts them into the same SyncedCalendarEvent
store (under a per-provider source), so they flow into everything that already reads it.

Read-only: never writes to the user's calendar. Refreshes an expired access token once before giving
up on an integration. Network- and credential-dependent, so it degrades quietly (a failing provider
just leaves that source's rows untouched).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import google_oauth, microsoft_oauth
from app.models.calendar import CalendarIntegration
from app.repositories.calendar_repository import CalendarIntegrationRepository
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.services.calendar_service import get_provider

logger = logging.getLogger(__name__)

# How far back / ahead to pull — matches the EventKit sync window so all sources look the same.
_WINDOW_BACK = timedelta(hours=12)
_WINDOW_AHEAD = timedelta(hours=36)

_REFRESHERS = {"google": google_oauth, "microsoft": microsoft_oauth}


class CalendarEventSyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.integration_repo = CalendarIntegrationRepository(db)
        self.event_repo = SyncedCalendarEventRepository(db)

    async def sync_all(self, now: datetime | None = None) -> int:
        """Sync every active OAuth integration across all users. Returns total events written."""
        integrations = await self.integration_repo.list_all_active()
        total = 0
        for integration in integrations:
            total += await self._sync_integration(integration, now)
        return total

    async def sync_user(self, user_id: uuid.UUID, now: datetime | None = None) -> int:
        """Sync all of one user's active OAuth integrations (on-demand, e.g. right after connecting)."""
        integrations = await self.integration_repo.list_active_for_user(user_id)
        total = 0
        for integration in integrations:
            total += await self._sync_integration(integration, now)
        return total

    async def _sync_integration(self, integration: CalendarIntegration, now: datetime | None) -> int:
        now = now or datetime.now(timezone.utc)
        provider = integration.provider
        # Apple/device calendars come in via the EventKit path (PUT /calendar/synced); only OAuth
        # providers are pulled here.
        if provider not in _REFRESHERS:
            return 0

        start = now - _WINDOW_BACK
        end = now + _WINDOW_AHEAD
        try:
            events = await self._list_with_refresh(integration, start, end)
        except HTTPException:
            logger.warning("calendar sync: auth failed for %s (user %s)", provider, integration.user_id)
            return 0
        except Exception:  # noqa: BLE001 — a flaky provider shouldn't break the whole run
            logger.exception("calendar sync: fetch failed for %s (user %s)", provider, integration.user_id)
            return 0

        # Skip all-day events (they don't consume a working slot) and normalize to the repo's dict shape.
        rows = [
            {
                "external_id": e.event_id or f"{e.title}:{e.start.isoformat()}",
                "title": e.title,
                "starts_at": _aware(e.start),
                "ends_at": _aware(e.end),
                "location": e.location,
                "all_day": e.all_day,
            }
            for e in events
            if not e.all_day
        ]
        # replace_for_source is idempotent — it clears this source's prior rows first, so a re-sync
        # never duplicates and reflects deletions.
        await self.event_repo.replace_for_source(integration.user_id, provider, rows)
        return len(rows)

    async def _list_with_refresh(self, integration: CalendarIntegration, start, end):
        """List events, refreshing the access token once on a 401 (expired token)."""
        cal_provider = get_provider(integration.provider)
        try:
            return await cal_provider.list_events(
                access_token=integration.access_token, start=start, end=end,
                calendar_id=integration.calendar_id,
            )
        except HTTPException as exc:
            if exc.status_code != 401 or not integration.refresh_token:
                raise
            refresher = _REFRESHERS[integration.provider]
            tokens = await refresher.refresh_access_token(integration.refresh_token)
            await self.integration_repo.upsert(
                user_id=integration.user_id,
                provider=integration.provider,
                access_token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_expires_at=tokens.expires_at,
                calendar_id=integration.calendar_id,
            )
            return await cal_provider.list_events(
                access_token=tokens.access_token, start=start, end=end,
                calendar_id=integration.calendar_id,
            )


def _aware(dt: datetime) -> datetime:
    """Providers may return naive datetimes; store them as UTC-aware."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
