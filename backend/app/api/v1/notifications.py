import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.notification import (
    NotificationOut,
    NotificationSendIn,
    ReplanApproveOut,
    ReplanProposeIn,
    ReplanRequestOut,
)
from app.services.notification_service import NotificationService
from app.services.user_service import UserService

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[NotificationOut])
async def list_unread(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    svc = NotificationService(db)
    return [NotificationOut.model_validate(n) for n in await svc.list_unread(user_id)]


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    svc = NotificationService(db)
    marked = await svc.mark_read(notification_id, user_id)
    if marked:
        await db.commit()


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
async def send_notification(
    body: NotificationSendIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Internal / AI use: queue a notification for the authenticated user."""
    user_id = await _get_user_id(current_user, db)
    svc = NotificationService(db)
    notif = await svc.send_notification(
        user_id=user_id,
        type=body.type,
        title=body.title,
        body=body.body,
        channel=body.channel,
        payload=body.payload,
    )
    await db.commit()
    return NotificationOut.model_validate(notif)


# ── Replan approval flow ──────────────────────────────────────────────────────

@router.get("/replans/pending", response_model=list[ReplanRequestOut])
async def list_pending_replans(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    svc = NotificationService(db)
    return [ReplanRequestOut.model_validate(r) for r in await svc.list_pending_replans(user_id)]


@router.post("/replans", response_model=ReplanRequestOut, status_code=status.HTTP_201_CREATED)
async def propose_replan(
    body: ReplanProposeIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """AI proposes a replan. User must approve before it is applied."""
    user_id = await _get_user_id(current_user, db)
    svc = NotificationService(db)
    req = await svc.propose_replan(
        user_id=user_id,
        reason=body.reason,
        proposed_changes=body.proposed_changes,
    )
    await db.commit()
    return ReplanRequestOut.model_validate(req)


@router.post("/replans/{request_id}/approve", response_model=ReplanApproveOut)
async def approve_replan(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """User approves a pending replan. This is the only path that applies schedule changes."""
    user_id = await _get_user_id(current_user, db)
    svc = NotificationService(db)
    try:
        changes = await svc.approve_replan(request_id=request_id, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return ReplanApproveOut(applied_changes=changes)


@router.post("/replans/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_replan(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    svc = NotificationService(db)
    rejected = await svc.reject_replan(request_id=request_id, user_id=user_id)
    if rejected:
        await db.commit()
