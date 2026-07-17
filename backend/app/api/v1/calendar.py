import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.integrations.calendar_base import CalendarEventCreate
from app.repositories.consent_repository import ConsentRepository
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.schemas.calendar import (
    CalendarConnectIn,
    CalendarEventCreateIn,
    CalendarEventOut,
    CalendarIntegrationOut,
    PendingCalendarActionOut,
)
from app.services.calendar_import_service import CalendarImportService
from app.services.calendar_service import CalendarService
from app.services.user_service import UserService

router = APIRouter(prefix="/calendar", tags=["calendar"])


# ── Synced events (Apple Calendar / EventKit — device-read, no OAuth) ──────────


class SyncedEventIn(BaseModel):
    external_id: str = Field(max_length=256)
    title: str = Field(max_length=256)
    starts_at: datetime
    ends_at: datetime
    location: str | None = Field(default=None, max_length=256)
    all_day: bool = False


class CalendarSyncIn(BaseModel):
    source: str = Field(default="apple", max_length=16)
    events: list[SyncedEventIn] = []


class CalendarSyncOut(BaseModel):
    synced: int


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.put("/synced", response_model=CalendarSyncOut)
async def sync_calendar(
    body: CalendarSyncIn, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> CalendarSyncOut:
    """The app pushes the events it read from the device (EventKit) so the engine can factor the
    user's schedule. Replaces the user's synced events for that source. No OAuth — device permission
    lives on the client."""
    user_id = await _get_user_id(current_user, db)
    n = await SyncedCalendarEventRepository(db).replace_for_source(
        user_id, body.source, [e.model_dump() for e in body.events]
    )
    # Syncing device (EventKit) calendar events is the user granting calendar visibility — record the
    # consent so the Privacy panel reflects it (TIME-256).
    await ConsentRepository(db).ensure_granted(user_id, "calendar_details", source="calendar_sync")
    await db.commit()
    return CalendarSyncOut(synced=n)


class CalendarImportOut(BaseModel):
    imported: int


@router.post("/import", response_model=CalendarImportOut)
async def import_calendar_events(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> CalendarImportOut:
    """Turn the user's synced calendar events into editable tasks in their list. Deduped, so calling
    it repeatedly (e.g. after each sync) never creates duplicates. Imports a wide window covering the
    synced range."""
    user_id = await _get_user_id(current_user, db)
    now = datetime.now(timezone.utc)
    created = await CalendarImportService(db).import_window(
        user_id, now - timedelta(days=1), now + timedelta(days=14)
    )
    await db.commit()
    return CalendarImportOut(imported=len(created))


@router.get("/synced/today", response_model=list[SyncedEventIn])
async def synced_today(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[SyncedEventIn]:
    user_id = await _get_user_id(current_user, db)
    now = datetime.now(timezone.utc)
    rows = await SyncedCalendarEventRepository(db).list_window(
        user_id, now - timedelta(hours=12), now + timedelta(hours=36)
    )
    return [
        SyncedEventIn(external_id=r.external_id, title=r.title, starts_at=r.starts_at,
                      ends_at=r.ends_at, location=r.location, all_day=r.all_day)
        for r in rows
    ]


# ── Integration management ────────────────────────────────────────────────────

@router.post("/connect", response_model=CalendarIntegrationOut, status_code=status.HTTP_201_CREATED)
async def connect_calendar(
    body: CalendarConnectIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Store OAuth tokens for a calendar provider. Premium only."""
    user_id = await _get_user_id(current_user, db)
    svc = CalendarService(db)
    integration = await svc.connect(
        user_id=user_id,
        provider=body.provider,
        access_token=body.access_token,
        refresh_token=body.refresh_token,
        token_expires_at=body.token_expires_at,
        calendar_id=body.calendar_id,
    )
    await db.commit()
    return CalendarIntegrationOut.model_validate(integration)


@router.delete("/disconnect/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_calendar(
    provider: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    svc = CalendarService(db)
    disconnected = await svc.disconnect(user_id, provider)
    await db.commit()
    if not disconnected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")


# ── Read events ───────────────────────────────────────────────────────────────

@router.get("/events", response_model=list[CalendarEventOut])
async def list_events(
    provider: str,
    start: datetime,
    end: datetime,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Read calendar events for a date range. Premium only."""
    user_id = await _get_user_id(current_user, db)
    svc = CalendarService(db)
    events = await svc.list_events(user_id=user_id, provider=provider, start=start, end=end)
    return [
        CalendarEventOut(
            event_id=e.event_id,
            title=e.title,
            start=e.start,
            end=e.end,
            calendar_id=e.calendar_id,
            location=e.location,
            description=e.description,
            provider=e.provider,
        )
        for e in events
    ]


# ── Approval-gated writes ─────────────────────────────────────────────────────

@router.post("/actions/request", response_model=PendingCalendarActionOut, status_code=status.HTTP_201_CREATED)
async def request_event(
    provider: str,
    body: CalendarEventCreateIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Queue a calendar write for user approval. Never writes until approved."""
    user_id = await _get_user_id(current_user, db)
    svc = CalendarService(db)
    event = CalendarEventCreate(
        title=body.title,
        start=body.start,
        end=body.end,
        location=body.location,
        description=body.description,
        calendar_id=body.calendar_id,
    )
    action = await svc.request_event_creation(user_id=user_id, provider=provider, event=event)
    await db.commit()
    return PendingCalendarActionOut.model_validate(action)


@router.get("/actions/pending", response_model=list[PendingCalendarActionOut])
async def list_pending(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    svc = CalendarService(db)
    return [PendingCalendarActionOut.model_validate(a) for a in await svc.list_pending_actions(user_id)]


@router.post("/actions/{action_id}/approve", response_model=CalendarEventOut)
async def approve_event(
    action_id: uuid.UUID,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """User approves a pending calendar write. This is the only path that writes to the calendar."""
    user_id = await _get_user_id(current_user, db)
    svc = CalendarService(db)
    try:
        created = await svc.approve_action(action_id=action_id, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return CalendarEventOut(
        event_id=created.event_id,
        title=created.title,
        start=created.start,
        end=created.end,
        calendar_id=created.calendar_id,
        location=created.location,
        description=created.description,
        provider=created.provider,
    )


@router.post("/actions/{action_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_event(
    action_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    svc = CalendarService(db)
    rejected = await svc.reject_action(action_id=action_id, user_id=user_id)
    if rejected:
        await db.commit()
