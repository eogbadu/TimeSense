from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_place import UserPlace


class UserPlaceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(self, user_id: uuid.UUID) -> list[UserPlace]:
        rows = await self.db.execute(
            select(UserPlace).where(UserPlace.user_id == user_id).order_by(UserPlace.name)
        )
        return list(rows.scalars().all())

    async def replace_all(self, user_id: uuid.UUID, places: list[dict]) -> list[UserPlace]:
        """Replace the user's saved places with the given set (the app owns the source of truth)."""
        await self.db.execute(delete(UserPlace).where(UserPlace.user_id == user_id))
        created: list[UserPlace] = []
        for p in places:
            row = UserPlace(
                user_id=user_id, name=p["name"], place_type=p.get("place_type"),
                latitude=p["latitude"], longitude=p["longitude"],
                is_preferred=p.get("is_preferred", True),
            )
            self.db.add(row)
            created.append(row)
        await self.db.flush()
        return created
