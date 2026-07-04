import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.referral import ReferralCodeOut, ReferralValidateIn, ReferralValidateOut
from app.services.referral_service import ReferralService
from app.services.user_service import UserService

router = APIRouter(prefix="/referrals", tags=["referrals"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.get("/my-code", response_model=ReferralCodeOut)
async def get_my_code(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get or create the authenticated user's referral code."""
    user_id = await _get_user_id(current_user, db)
    svc = ReferralService(db)
    code = await svc.get_or_create_code(user_id)
    await db.commit()
    return ReferralCodeOut.model_validate(code)


@router.post("/validate", response_model=ReferralValidateOut)
async def validate_code(
    body: ReferralValidateIn,
    db: AsyncSession = Depends(get_db),
):
    """Validate a referral code at signup (no auth required)."""
    svc = ReferralService(db)
    ref = await svc.validate_code(body.code.upper())
    if ref is None:
        return ReferralValidateOut(valid=False)
    return ReferralValidateOut(valid=True, code=ref.code)


@router.post("/convert", response_model=ReferralValidateOut)
async def record_conversion(
    body: ReferralValidateIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Record that the authenticated user converted via a referral code.
    Called by the Stripe/IAP webhook handler after successful payment.
    """
    user_id = await _get_user_id(current_user, db)
    svc = ReferralService(db)
    conv = await svc.on_conversion(
        referred_user_id=user_id,
        referral_code=body.code.upper(),
    )
    await db.commit()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code or already converted.",
        )
    return ReferralValidateOut(valid=True, code=body.code.upper())
