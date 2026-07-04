"""
Referral Service.

Flow:
  1. User gets their code via get_or_create_code()
  2. New user signs up with code → validate_and_record_signup() attaches the referral
  3. When that user pays → on_conversion() records conversion and extends both subscriptions
"""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import ReferralCode, ReferralConversion
from app.repositories.referral_repository import ReferralRepository
from app.services.subscription_service import SubscriptionService

REWARD_DAYS = 30


class ReferralService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ReferralRepository(db)

    async def get_or_create_code(self, user_id: uuid.UUID) -> ReferralCode:
        return await self.repo.get_or_create_code(user_id)

    async def validate_code(self, code: str) -> ReferralCode | None:
        """Validate a referral code at signup. Returns None if invalid/inactive."""
        return await self.repo.get_by_code(code)

    async def on_conversion(
        self,
        referred_user_id: uuid.UUID,
        referral_code: str,
    ) -> ReferralConversion | None:
        """
        Call when a referred user converts to paid.
        - Records the conversion (idempotent — no double-reward)
        - Extends both subscriptions by REWARD_DAYS
        Returns None if already converted or code is invalid.
        """
        ref = await self.repo.get_by_code(referral_code)
        if ref is None:
            return None

        conv = await self.repo.record_conversion(
            referral_code_id=ref.id,
            referred_user_id=referred_user_id,
        )
        if conv is None:
            return None  # already converted

        # Extend both subscriptions
        sub_svc = SubscriptionService(self.db)
        now = datetime.now(UTC)

        for uid in (ref.owner_id, referred_user_id):
            sub = await sub_svc.get_subscription(uid)
            if sub is not None:
                # Push period_end forward by REWARD_DAYS from current end (or now if expired)
                current_end = (
                    datetime.fromisoformat(sub.current_period_end)
                    if sub.current_period_end
                    else now
                )
                new_end = max(current_end, now) + timedelta(days=REWARD_DAYS)
                sub.current_period_end = new_end.isoformat()
                if sub.status in ("canceled", "expired"):
                    sub.status = "active"

        await self.repo.mark_rewarded(conv.id)
        return conv
