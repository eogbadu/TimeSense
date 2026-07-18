"""Celery task: pull OAuth-connected calendars (Google/Outlook) into SyncedCalendarEvent (TIME-277).

Runs periodically so connected calendars stay fresh in the Smart Plan / usable-time / engine. All
logic lives in CalendarEventSyncService; read-only and credential-dependent, so it no-ops quietly when
providers aren't configured (not exercised by tests here — no Redis/Docker/live OAuth)."""

import asyncio

from app.core.database import AsyncSessionLocal
from app.services.calendar_event_sync_service import CalendarEventSyncService
from app.workers.celery_app import celery_app


async def _run() -> int:
    async with AsyncSessionLocal() as db:
        total = await CalendarEventSyncService(db).sync_all()
        await db.commit()
        return total


@celery_app.task(name="timesense.sync_oauth_calendars")
def sync_oauth_calendars() -> int:
    return asyncio.run(_run())
