from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.schemas.teams import (
    TeamsActionItemOut,
    TeamsConnectIn,
    TeamsIntegrationOut,
    TeamsScanIn,
    TeamsScanResult,
)
from app.services.teams_service import TeamsNotConnected, TeamsService
from app.services.user_service import UserService

router = APIRouter(prefix="/teams", tags=["teams"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


# ── Integration management ────────────────────────────────────────────────────

@router.post("/connect", response_model=TeamsIntegrationOut, status_code=status.HTTP_201_CREATED)
async def connect_teams(
    body: TeamsConnectIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> TeamsIntegrationOut:
    """Store a Microsoft Graph token (mobile client does OAuth, posts the token here). Premium only."""
    user_id = await _get_user_id(current_user, db)
    integration = await TeamsService(db, gateway).connect(user_id, body.access_token, body.tenant_id)
    await db.commit()
    return TeamsIntegrationOut.model_validate(integration)


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_teams(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
):
    user_id = await _get_user_id(current_user, db)
    disconnected = await TeamsService(db, gateway).disconnect(user_id)
    await db.commit()
    if not disconnected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teams not connected.")


# ── Scan (detect only) ────────────────────────────────────────────────────────

@router.post("/scan", response_model=TeamsScanResult)
async def scan_teams(
    body: TeamsScanIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> TeamsScanResult:
    """Read recent messages and detect action items. Creates pending suggestions, NOT tasks."""
    user_id = await _get_user_id(current_user, db)
    try:
        scanned, detected = await TeamsService(db, gateway).scan_conversation(
            user_id, body.conversation_id, body.limit
        )
    except TeamsNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return TeamsScanResult(
        scanned=scanned,
        detected=[TeamsActionItemOut.model_validate(i) for i in detected],
    )


# ── Approval gate ─────────────────────────────────────────────────────────────

@router.get("/pending", response_model=list[TeamsActionItemOut])
async def list_pending_teams_items(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> list[TeamsActionItemOut]:
    user_id = await _get_user_id(current_user, db)
    items = await TeamsService(db, gateway).list_pending(user_id)
    return [TeamsActionItemOut.model_validate(i) for i in items]


@router.post("/actions/{item_id}/confirm", response_model=TeamsActionItemOut)
async def confirm_teams_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> TeamsActionItemOut:
    """User approves a detected action item — the only path that creates a Task from Teams."""
    user_id = await _get_user_id(current_user, db)
    try:
        item = await TeamsService(db, gateway).confirm(user_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return TeamsActionItemOut.model_validate(item)


@router.post("/actions/{item_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_teams_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
):
    user_id = await _get_user_id(current_user, db)
    rejected = await TeamsService(db, gateway).reject(user_id, item_id)
    if rejected:
        await db.commit()
