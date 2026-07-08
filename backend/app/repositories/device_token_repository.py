from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_token import DeviceToken


class DeviceTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(self, user_id: uuid.UUID, token: str, platform: str = "ios") -> DeviceToken:
        row = (await self.db.execute(
            select(DeviceToken).where(DeviceToken.token == token)
        )).scalar_one_or_none()
        if row is None:
            row = DeviceToken(user_id=user_id, token=token, platform=platform)
            self.db.add(row)
        else:
            row.user_id = user_id     # token moved to another account → reassign
            row.platform = platform
        await self.db.flush()
        return row

    async def list_tokens(self, user_id: uuid.UUID) -> list[str]:
        rows = await self.db.execute(select(DeviceToken.token).where(DeviceToken.user_id == user_id))
        return [r[0] for r in rows.all()]

    async def delete(self, token: str) -> None:
        await self.db.execute(delete(DeviceToken).where(DeviceToken.token == token))

    async def distinct_user_ids(self) -> list[uuid.UUID]:
        rows = await self.db.execute(select(DeviceToken.user_id).distinct())
        return [r[0] for r in rows.all()]
