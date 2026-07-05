from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.services.privacy_service import PrivacyService
from app.services.user_service import UserService

router = APIRouter(prefix="/privacy", tags=["privacy"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.get("/export", summary="Export all of my data (JSON)")
async def export_my_data(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return a portable JSON bundle of everything the authenticated user owns (tokens redacted)."""
    user_id = await _get_user_id(current_user, db)
    return await PrivacyService(db).export_data(user_id)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT, summary="Delete my account and all data")
async def delete_my_account(
    current_user: CurrentUser,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Permanently erase the authenticated user's account and all associated data.

    Irreversible — requires ?confirm=true so a stray call can't wipe data.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion must be confirmed with ?confirm=true.",
        )
    user_id = await _get_user_id(current_user, db)
    await PrivacyService(db).delete_account(user_id)
    await db.commit()
