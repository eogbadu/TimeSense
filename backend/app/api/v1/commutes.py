from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.commute import CommuteDetectRequest, CommuteEventResponse
from app.services.commute_service import CommuteService, LocationConsentRequired
from app.services.user_service import UserService

router = APIRouter(prefix="/commute", tags=["commute"])


async def _resolve_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.post("/detect", response_model=CommuteEventResponse | None)
async def detect_commute(
    body: CommuteDetectRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CommuteEventResponse | None:
    user_id = await _resolve_user_id(current_user, db)
    svc = CommuteService(db)
    try:
        event = await svc.propose_commute(user_id, body.pings)
    except LocationConsentRequired as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return CommuteEventResponse.model_validate(event) if event else None


@router.get("/pending", response_model=list[CommuteEventResponse])
async def list_pending_commutes(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[CommuteEventResponse]:
    user_id = await _resolve_user_id(current_user, db)
    events = await CommuteService(db).list_pending(user_id)
    return [CommuteEventResponse.model_validate(e) for e in events]


@router.post("/{commute_id}/confirm", status_code=204)
async def confirm_commute(
    commute_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _resolve_user_id(current_user, db)
    confirmed = await CommuteService(db).confirm(user_id, commute_id)
    if not confirmed:
        raise HTTPException(status_code=404, detail="Commute event not found or already handled")


@router.post("/{commute_id}/reject", status_code=204)
async def reject_commute(
    commute_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _resolve_user_id(current_user, db)
    rejected = await CommuteService(db).reject(user_id, commute_id)
    if not rejected:
        raise HTTPException(status_code=404, detail="Commute event not found or already handled")
