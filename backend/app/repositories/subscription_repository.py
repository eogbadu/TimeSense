import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.subscription import Subscription

TRIAL_DAYS = 14


class SubscriptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_platform_customer_id(self, platform_customer_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.platform_customer_id == platform_customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_platform_subscription_id(self, platform_subscription_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.platform_subscription_id == platform_subscription_id)
        )
        return result.scalar_one_or_none()

    async def start_trial(
        self,
        user_id: uuid.UUID,
        platform: str = "stripe",
        platform_customer_id: str | None = None,
    ) -> Subscription:
        now = datetime.now(UTC)
        trial_end = now + timedelta(days=TRIAL_DAYS)
        sub = Subscription(
            user_id=user_id,
            platform=platform,
            status="trialing",
            platform_customer_id=platform_customer_id,
            trial_start=now.isoformat(),
            trial_end=trial_end.isoformat(),
            current_period_end=trial_end.isoformat(),
        )
        self.db.add(sub)
        await self.db.flush()
        return sub

    async def update(self, user_id: uuid.UUID, **kwargs) -> Subscription | None:
        sub = await self.get_by_user_id(user_id)
        if sub is None:
            return None
        allowed = {
            "status", "platform_customer_id", "platform_subscription_id",
            "plan", "trial_start", "trial_end", "current_period_end", "cancel_at_period_end",
        }
        for key, value in kwargs.items():
            if key in allowed:
                setattr(sub, key, value)
        await self.db.flush()
        return sub

    async def expire_trial(self, user_id: uuid.UUID) -> Subscription | None:
        return await self.update(user_id, status="expired")

    async def list_all(self, offset: int = 0, limit: int = 50) -> list[Subscription]:
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.user))
            .order_by(Subscription.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_status(self, statuses: list[str]) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Subscription).where(Subscription.status.in_(statuses))
        )
        return result.scalar_one()
