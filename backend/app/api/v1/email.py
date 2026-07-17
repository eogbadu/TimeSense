from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.entitlements import PremiumUser
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.schemas.email import EmailActionItemOut, EmailScanIn, EmailScanResult
from app.services.email_service import EmailConsentRequired, EmailNotConnected, EmailService
from app.services.user_service import UserService

router = APIRouter(prefix="/email", tags=["email"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


# ── Scan (detect only — never creates Tasks) ──────────────────────────────────

@router.post("/scan", response_model=EmailScanResult)
async def scan_email(
    body: EmailScanIn,
    _premium: PremiumUser,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> EmailScanResult:
    """Read recent inbox emails and detect action items. Creates pending suggestions, NOT tasks.
    Requires email_content consent. Premium only."""
    user_id = await _get_user_id(current_user, db)
    try:
        scanned, detected = await EmailService(db, gateway).scan(user_id, body.max_results)
    except EmailConsentRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email access requires consent (email_content).",
        ) from exc
    except EmailNotConnected as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not connected.") from exc
    await db.commit()
    return EmailScanResult(
        scanned=scanned,
        detected=[EmailActionItemOut.model_validate(i) for i in detected],
    )


# ── Approval gate ─────────────────────────────────────────────────────────────

@router.get("/pending", response_model=list[EmailActionItemOut])
async def list_pending_email_items(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[EmailActionItemOut]:
    user_id = await _get_user_id(current_user, db)
    items = await EmailService(db).list_pending(user_id)
    return [EmailActionItemOut.model_validate(i) for i in items]


@router.post("/actions/{item_id}/confirm", response_model=EmailActionItemOut)
async def confirm_email_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EmailActionItemOut:
    """User approves a detected item — the only path that creates a Task from email."""
    user_id = await _get_user_id(current_user, db)
    try:
        item = await EmailService(db).confirm(user_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return EmailActionItemOut.model_validate(item)


@router.post("/actions/{item_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_email_item(
    item_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await _get_user_id(current_user, db)
    rejected = await EmailService(db).reject(user_id, item_id)
    if rejected:
        await db.commit()


# ── Disconnect ────────────────────────────────────────────────────────────────

@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_email(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Deactivate the user's Gmail connection (drops stored tokens). Idempotent."""
    user_id = await _get_user_id(current_user, db)
    disconnected = await EmailService(db).disconnect(user_id)
    if not disconnected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not connected.")
    await db.commit()
