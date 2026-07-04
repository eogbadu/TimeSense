import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.referral import ReferralCode, ReferralConversion


def _new_code() -> str:
    return secrets.token_urlsafe(8).upper()[:10]


class ReferralRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_code(self, user_id: uuid.UUID) -> ReferralCode:
        result = await self.db.execute(
            select(ReferralCode).where(
                ReferralCode.owner_id == user_id,
                ReferralCode.is_active.is_(True),
            ).options(selectinload(ReferralCode.conversions))
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Ensure uniqueness — retry up to 3 times on collision
        for _ in range(3):
            code = _new_code()
            collision = await self.db.execute(
                select(ReferralCode).where(ReferralCode.code == code)
            )
            if collision.scalar_one_or_none() is None:
                break

        ref = ReferralCode(owner_id=user_id, code=code)
        self.db.add(ref)
        await self.db.flush()
        return ref

    async def get_by_code(self, code: str) -> ReferralCode | None:
        result = await self.db.execute(
            select(ReferralCode).where(
                ReferralCode.code == code,
                ReferralCode.is_active.is_(True),
            ).options(selectinload(ReferralCode.conversions))
        )
        return result.scalar_one_or_none()

    async def record_conversion(
        self,
        referral_code_id: uuid.UUID,
        referred_user_id: uuid.UUID,
    ) -> ReferralConversion | None:
        """Returns None if already converted (prevents double-reward)."""
        existing = await self.db.execute(
            select(ReferralConversion).where(
                ReferralConversion.referred_user_id == referred_user_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None

        conv = ReferralConversion(
            referral_code_id=referral_code_id,
            referred_user_id=referred_user_id,
        )
        self.db.add(conv)

        # Increment use counter on the code
        code_result = await self.db.execute(
            select(ReferralCode).where(ReferralCode.id == referral_code_id)
        )
        ref_code = code_result.scalar_one_or_none()
        if ref_code:
            ref_code.uses += 1

        await self.db.flush()
        return conv

    async def mark_rewarded(self, conversion_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(ReferralConversion).where(ReferralConversion.id == conversion_id)
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            return False
        conv.status = "rewarded"
        conv.rewarded_at = datetime.now(UTC)
        await self.db.flush()
        return True
