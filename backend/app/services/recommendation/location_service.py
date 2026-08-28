"""Centralized location service. Reads the user's current derived place (UserLocationState — place
name, is_home, and since TIME-291 the CURRENT coordinates when the user has consented; never a
movement history) and returns a typed snapshot. Never crashes the engine when location is
unavailable; returns an "unknown" snapshot with low confidence instead."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_location_repository import UserLocationRepository
from app.services.recommendation.types import Coordinates, LocationCategory, UserLocationSnapshot


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
        # The current position, when the user has consented to location (TIME-291). Without this an
        # errand could never be travel-checked unless the reported place name happened to match a
        # saved place exactly, so location silently stopped influencing recommendations.
        coordinates=(
            Coordinates(latitude=state.latitude, longitude=state.longitude)
            if state.latitude is not None and state.longitude is not None else None
        ),
    )
