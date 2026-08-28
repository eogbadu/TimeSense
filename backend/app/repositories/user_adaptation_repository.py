from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_adaptation_profile import UserAdaptationProfile


class UserAdaptationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: uuid.UUID) -> UserAdaptationProfile | None:
        """One indexed row. This is deliberately the cheapest possible read: the engine calls it on
        every recommendation, which is the whole reason the rollup exists (TIME-292)."""
        result = await self.db.execute(
            select(UserAdaptationProfile).where(UserAdaptationProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: uuid.UUID, **fields) -> UserAdaptationProfile:
        """Idempotent — the nightly job can be re-run for a day without creating duplicates."""
        row = await self.get(user_id)
        if row is None:
            row = UserAdaptationProfile(user_id=user_id, **fields)
            self.db.add(row)
        else:
            for key, value in fields.items():
                setattr(row, key, value)
        await self.db.flush()
        await self.db.refresh(row)
        return row
