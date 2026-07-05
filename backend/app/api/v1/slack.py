from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.schemas.slack import (
    SlackActionItemOut,
    SlackConnectIn,
    SlackIntegrationOut,
    SlackScanIn,
    SlackScanResult,
)
from app.services.slack_service import SlackNotConnected, SlackService
from app.services.user_service import UserService

router = APIRouter(prefix="/slack", tags=["slack"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


# ── Integration management ────────────────────────────────────────────────────

@router.post("/connect", response_model=SlackIntegrationOut, status_code=status.HTTP_201_CREATED)
async def connect_slack(
    body: SlackConnectIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> SlackIntegrationOut:
    """Store a Slack OAuth token (mobile client does OAuth, posts the token here). Premium only."""
    user_id = await _get_user_id(current_user, db)
    integration = await SlackService(db, gateway).connect(user_id, body.access_token, body.team_id)
    await db.commit()
    return SlackIntegrationOut.model_validate(integration)


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_slack(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
):
    user_id = await _get_user_id(current_user, db)
    disconnected = await SlackService(db, gateway).disconnect(user_id)
    await db.commit()
    if not disconnected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slack not connected.")


# ── Scan (detect only) ────────────────────────────────────────────────────────

@router.post("/scan", response_model=SlackScanResult)
async def scan_slack(
    body: SlackScanIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> SlackScanResult:
    """Read recent messages and detect action items. Creates pending suggestions, NOT tasks."""
    user_id = await _get_user_id(current_user, db)
    try:
        scanned, detected = await SlackService(db, gateway).scan_channel(
            user_id, body.channel, body.limit
        )
    except SlackNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return SlackScanResult(
        scanned=scanned,
        detected=[SlackActionItemOut.model_validate(i) for i in detected],
    )


# ── Approval gate ─────────────────────────────────────────────────────────────

@router.get("/pending", response_model=list[SlackActionItemOut])
async def list_pending_slack_items(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> list[SlackActionItemOut]:
    user_id = await _get_user_id(current_user, db)
    items = await SlackService(db, gateway).list_pending(user_id)
    return [SlackActionItemOut.model_validate(i) for i in items]


@router.post("/actions/{item_id}/confirm", response_model=SlackActionItemOut)
async def confirm_slack_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> SlackActionItemOut:
    """User approves a detected action item — the only path that creates a Task from Slack."""
    user_id = await _get_user_id(current_user, db)
    try:
        item = await SlackService(db, gateway).confirm(user_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return SlackActionItemOut.model_validate(item)


@router.post("/actions/{item_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_slack_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
):
    user_id = await _get_user_id(current_user, db)
    rejected = await SlackService(db, gateway).reject(user_id, item_id)
    if rejected:
        await db.commit()
