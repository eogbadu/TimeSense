from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.user_place_repository import UserPlaceRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/places", tags=["places"])


class PlaceIn(BaseModel):
    name: str = Field(max_length=64)
    place_type: str | None = Field(default=None, max_length=32)
    latitude: float
    longitude: float
    is_preferred: bool = True


class PlaceOut(PlaceIn):
    pass


class PlacesPayload(BaseModel):
    places: list[PlaceIn] = []


@router.get("", response_model=list[PlaceOut])
async def list_places(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> list[PlaceOut]:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    rows = await UserPlaceRepository(db).list_for_user(user.id)
    return [PlaceOut(name=r.name, place_type=r.place_type, latitude=r.latitude,
                     longitude=r.longitude, is_preferred=r.is_preferred) for r in rows]


@router.put("", response_model=list[PlaceOut])
async def sync_places(
    payload: PlacesPayload, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> list[PlaceOut]:
    """The app syncs its saved places (with coordinates) here so the engine can resolve errands and
    compute travel time. These are deliberate, user-named places — not a location trail."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    rows = await UserPlaceRepository(db).replace_all(user.id, [p.model_dump() for p in payload.places])
    await db.commit()
    return [PlaceOut(name=r.name, place_type=r.place_type, latitude=r.latitude,
                     longitude=r.longitude, is_preferred=r.is_preferred) for r in rows]
