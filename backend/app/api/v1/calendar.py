import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.integrations.calendar_base import CalendarEventCreate
from app.schemas.calendar import (
    CalendarConnectIn,
    CalendarEventCreateIn,
    CalendarEventOut,
    CalendarIntegrationOut,
    PendingCalendarActionOut,
)
from app.services.calendar_service import CalendarService
from app.services.user_service import UserService

router = APIRouter(prefix="/calendar", tags=["calendar"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


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
