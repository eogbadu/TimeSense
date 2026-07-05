from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.schemas.notion import (
    NotionConnectIn,
    NotionImportItemOut,
    NotionIntegrationOut,
    NotionScanIn,
    NotionScanResult,
)
from app.services.notion_service import NotionNotConnected, NotionService
from app.services.user_service import UserService

router = APIRouter(prefix="/notion", tags=["notion"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


# ── Integration management ────────────────────────────────────────────────────

@router.post("/connect", response_model=NotionIntegrationOut, status_code=status.HTTP_201_CREATED)
async def connect_notion(
    body: NotionConnectIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NotionIntegrationOut:
    """Store a Notion OAuth token (mobile client does OAuth, posts the token here). Premium only."""
    user_id = await _get_user_id(current_user, db)
    integration = await NotionService(db).connect(user_id, body.access_token, body.workspace_id)
    await db.commit()
    return NotionIntegrationOut.model_validate(integration)


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_notion(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    disconnected = await NotionService(db).disconnect(user_id)
    await db.commit()
    if not disconnected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notion not connected.")


# ── Scan (read candidate tasks only) ──────────────────────────────────────────

@router.post("/scan", response_model=NotionScanResult)
async def scan_notion(
    body: NotionScanIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NotionScanResult:
    """Read a Notion database's pages as candidate tasks. Creates pending import items, NOT tasks."""
    user_id = await _get_user_id(current_user, db)
    try:
        scanned, items = await NotionService(db).scan_database(
            user_id, body.database_id, body.limit
        )
    except NotionNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return NotionScanResult(
        scanned=scanned,
        items=[NotionImportItemOut.model_validate(i) for i in items],
    )


# ── Approval gate (import / dismiss) ──────────────────────────────────────────

@router.get("/pending", response_model=list[NotionImportItemOut])
async def list_pending_notion_items(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[NotionImportItemOut]:
    user_id = await _get_user_id(current_user, db)
    items = await NotionService(db).list_pending(user_id)
    return [NotionImportItemOut.model_validate(i) for i in items]


@router.post("/items/{item_id}/import", response_model=NotionImportItemOut)
async def import_notion_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NotionImportItemOut:
    """User imports a candidate task — the only path that creates a Task from Notion."""
    user_id = await _get_user_id(current_user, db)
    try:
        item = await NotionService(db).import_item(user_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return NotionImportItemOut.model_validate(item)


@router.post("/items/{item_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_notion_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    dismissed = await NotionService(db).dismiss(user_id, item_id)
    if dismissed:
        await db.commit()
