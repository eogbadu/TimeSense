from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_location_state import UserLocationState

# Ignore a place fix older than this — the user has probably moved since.
STALE_AFTER = timedelta(hours=6)


class UserLocationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_current(self, user_id: uuid.UUID, now: datetime | None = None) -> UserLocationState | None:
        now = now or datetime.now(timezone.utc)
        row = (await self.db.execute(
            select(UserLocationState).where(UserLocationState.user_id == user_id)
        )).scalar_one_or_none()
        if row is None:
            return None
        updated = row.updated_at if row.updated_at.tzinfo else row.updated_at.replace(tzinfo=timezone.utc)
        return None if now - updated > STALE_AFTER else row

    async def upsert(self, user_id: uuid.UUID, place_name: str | None, is_home: bool) -> UserLocationState:
        row = (await self.db.execute(
            select(UserLocationState).where(UserLocationState.user_id == user_id)
        )).scalar_one_or_none()
        if row is None:
            row = UserLocationState(user_id=user_id, place_name=place_name, is_home=is_home)
            self.db.add(row)
        else:
            row.place_name = place_name
            row.is_home = is_home
            row.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return row
