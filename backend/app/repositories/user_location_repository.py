from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_location_state import UserLocationState

# Ignore a place fix older than this — the user has probably moved since.
STALE_AFTER = timedelta(hours=6)
# How far ahead of the cutoff a client should refresh, so the signal is renewed rather than lost.
REFRESH_BEFORE = timedelta(hours=1)


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

    async def upsert(
        self,
        user_id: uuid.UUID,
        place_name: str | None,
        is_home: bool,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> UserLocationState:
        """Overwrite the user's current place. Coordinates are the CURRENT position only — this row
        is replaced on every update, so no movement history accumulates (TIME-291)."""
        row = (await self.db.execute(
            select(UserLocationState).where(UserLocationState.user_id == user_id)
        )).scalar_one_or_none()
        if row is None:
            row = UserLocationState(
                user_id=user_id, place_name=place_name, is_home=is_home,
                latitude=latitude, longitude=longitude,
            )
            self.db.add(row)
        else:
            row.place_name = place_name
            row.is_home = is_home
            # Only overwrite coordinates when we were given some. A name-only report (e.g. a
            # geofence crossing without a fresh fix) shouldn't erase a position we already have.
            if latitude is not None and longitude is not None:
                row.latitude = latitude
                row.longitude = longitude
            row.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return row

    async def is_stale_soon(
        self, user_id: uuid.UUID, now: datetime | None = None,
        within: timedelta = REFRESH_BEFORE,
    ) -> bool:
        """True when the stored fix is close enough to the staleness cutoff that the client should
        refresh it. Without this the signal simply vanished after 6 hours with nothing to bring it
        back (TIME-291)."""
        now = now or datetime.now(timezone.utc)
        row = (await self.db.execute(
            select(UserLocationState).where(UserLocationState.user_id == user_id)
        )).scalar_one_or_none()
        if row is None:
            return True
        updated = row.updated_at if row.updated_at.tzinfo else row.updated_at.replace(tzinfo=timezone.utc)
        return (now - updated) > (STALE_AFTER - within)
