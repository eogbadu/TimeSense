from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.consent_repository import ConsentRepository
from app.repositories.user_location_repository import UserLocationRepository
from app.services.user_service import UserService

# The consent category that gates storing a position (already used by commute detection).
LOCATION_CONSENT = "location_tracking"

router = APIRouter(prefix="/location", tags=["location"])


class PlaceUpdate(BaseModel):
    place_name: str | None = Field(default=None, max_length=64)  # None = away / out and about
    is_home: bool = False
    # Current position. Optional — a geofence crossing may have no fresh fix, and a client without
    # location consent simply omits these (TIME-291).
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class PlaceResponse(BaseModel):
    place_name: str | None
    is_home: bool
    has_coordinates: bool = False
    # True when the stored fix is close to going stale, so the client knows to send a fresh one
    # rather than letting the signal silently disappear.
    refresh_soon: bool = False


@router.post("/place", response_model=PlaceResponse)
async def update_place(
    body: PlaceUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PlaceResponse:
    """The app reports the user's current derived place (or None when away).

    Coordinates are stored only with the `location_tracking` consent, and only ever as the CURRENT
    position — this row is overwritten on every update, so no movement history accumulates. Without
    consent the name is stored exactly as before and coordinates are dropped (TIME-291).
    """
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")

    consent = await ConsentRepository(db).get_effective(user.id)
    allowed = bool(consent.get(LOCATION_CONSENT))
    lat = body.latitude if allowed else None
    lng = body.longitude if allowed else None

    repo = UserLocationRepository(db)
    row = await repo.upsert(user.id, body.place_name, body.is_home, latitude=lat, longitude=lng)
    refresh_soon = await repo.is_stale_soon(user.id)
    await db.commit()
    return PlaceResponse(
        place_name=row.place_name,
        is_home=row.is_home,
        has_coordinates=row.latitude is not None and row.longitude is not None,
        refresh_soon=refresh_soon,
    )
