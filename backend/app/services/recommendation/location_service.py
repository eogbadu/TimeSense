"""Centralized location service. Reads the user's current derived place (UserLocationState — place
name + is_home, never raw coordinates) and returns a typed snapshot. Never crashes the engine when
location is unavailable; returns an "unknown" snapshot with low confidence instead."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_location_repository import UserLocationRepository
from app.services.recommendation.types import LocationCategory, UserLocationSnapshot


def _category(place_name: str | None, is_home: bool) -> LocationCategory:
    if place_name is None:
        return "unknown"
    name = place_name.strip().lower()
    if is_home or name == "home":
        return "home"
    if name in ("work", "office"):
        return "work"
    if name == "gym":
        return "gym"
    if name == "school":
        return "school"
    if name in ("store", "grocery", "walmart", "target", "pharmacy", "errands"):
        return "store"
    return "errand"


async def get_user_location_snapshot(
    db: AsyncSession, user_id: uuid.UUID, now: datetime | None = None
) -> UserLocationSnapshot:
    """Best-effort current-place snapshot. Missing/stale data → an 'unknown', low-confidence
    snapshot (the engine then treats location as absent rather than failing)."""
    now = now or datetime.now(timezone.utc)
    state = await UserLocationRepository(db).get_current(user_id, now)
    if state is None:
        return UserLocationSnapshot(
            location_category="unknown", last_updated_at=now.isoformat(), confidence=0.0
        )
    updated = state.updated_at if state.updated_at.tzinfo else state.updated_at.replace(tzinfo=timezone.utc)
    return UserLocationSnapshot(
        location_category=_category(state.place_name, state.is_home),
        last_updated_at=updated.isoformat(),
        confidence=0.9,
        place_name=state.place_name,
        coordinates=None,   # we never persist raw coordinates
    )
