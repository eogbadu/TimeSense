from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.user_location_repository import UserLocationRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/location", tags=["location"])


class PlaceUpdate(BaseModel):
    place_name: str | None = Field(default=None, max_length=64)  # None = away / out and about
    is_home: bool = False


class PlaceResponse(BaseModel):
    place_name: str | None
    is_home: bool


@router.post("/place", response_model=PlaceResponse)
async def update_place(
    body: PlaceUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PlaceResponse:
    """The app reports the user's current derived place (or None when away) on geofence transitions.
    Only the place name is stored — never raw coordinates. Used to shape recommendations + the
    location signal in 'Why this recommendation?'."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    row = await UserLocationRepository(db).upsert(user.id, body.place_name, body.is_home)
    await db.commit()
    return PlaceResponse(place_name=row.place_name, is_home=row.is_home)
