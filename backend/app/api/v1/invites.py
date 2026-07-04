import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AdminUser, CurrentUser
from app.repositories.invite_repository import WaitlistRepository
from app.schemas.invite import (
    InviteCodeCreateIn,
    InviteCodeOut,
    InviteValidateIn,
    InviteValidateOut,
    WaitlistEntryOut,
    WaitlistJoinIn,
    WaitlistPositionOut,
)
from app.services.invite_service import InviteService
from app.services.user_service import UserService

router = APIRouter(prefix="/invites", tags=["invites"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.post("/waitlist", response_model=WaitlistEntryOut, status_code=status.HTTP_201_CREATED)
async def join_waitlist(body: WaitlistJoinIn, db: AsyncSession = Depends(get_db)):
    svc = InviteService(db)
    entry = await svc.join_waitlist(email=body.email, referral_code=body.referral_code)
    await db.commit()
    return WaitlistEntryOut.model_validate(entry)


@router.get("/waitlist/position", response_model=WaitlistPositionOut)
async def waitlist_position(email: str, db: AsyncSession = Depends(get_db)):
    repo = WaitlistRepository(db)
    entry = await repo.get_by_email(email)
    if entry is None:
        return WaitlistPositionOut(email=email, position=None, status=None)
    return WaitlistPositionOut(email=email, position=entry.position, status=entry.status)


@router.post("/validate", response_model=InviteValidateOut)
async def validate_invite_code(body: InviteValidateIn, db: AsyncSession = Depends(get_db)):
    svc = InviteService(db)
    valid = await svc.validate_invite_code(body.code.upper())
    return InviteValidateOut(valid=valid)


@router.get("/codes", response_model=list[InviteCodeOut])
async def list_invite_codes(_admin: AdminUser, db: AsyncSession = Depends(get_db)):  # type: ignore[assignment]
    svc = InviteService(db)
    return [InviteCodeOut.model_validate(c) for c in await svc.list_active_codes()]


@router.post("/codes", response_model=InviteCodeOut, status_code=status.HTTP_201_CREATED)
async def create_invite_code(
    body: InviteCodeCreateIn, _admin: AdminUser, current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):  # type: ignore[assignment]
    user_id = await _get_user_id(current_user, db)
    svc = InviteService(db)
    code = await svc.create_invite_code(created_by_id=user_id, max_uses=body.max_uses,
                                         expires_at=body.expires_at, note=body.note)
    await db.commit()
    return InviteCodeOut.model_validate(code)


@router.delete("/codes/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_invite_code(
    code: str, _admin: AdminUser, db: AsyncSession = Depends(get_db),
):  # type: ignore[assignment]
    svc = InviteService(db)
    disabled = await svc.disable_invite_code(code.upper())
    if disabled:
        await db.commit()


@router.post("/waitlist/{entry_id}/invite", response_model=InviteCodeOut)
async def invite_from_waitlist(
    entry_id: uuid.UUID, _admin: AdminUser, current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):  # type: ignore[assignment]
    user_id = await _get_user_id(current_user, db)
    svc = InviteService(db)
    code = await svc.invite_from_waitlist(entry_id=entry_id, admin_user_id=user_id)
    if code is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found.")
    await db.commit()
    return InviteCodeOut.model_validate(code)
