from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.device_token_repository import DeviceTokenRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceTokenIn(BaseModel):
    token: str = Field(min_length=8, max_length=256)
    platform: str = Field(default="ios", max_length=16)


class DeviceAck(BaseModel):
    ok: bool = True


@router.put("", response_model=DeviceAck)
async def register_device(
    body: DeviceTokenIn, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> DeviceAck:
    """Register this device's push token so TimeSense can send proactive notifications."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    await DeviceTokenRepository(db).upsert(user.id, body.token, body.platform)
    await db.commit()
    return DeviceAck()


@router.delete("/{token}", response_model=DeviceAck)
async def unregister_device(
    token: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> DeviceAck:
    await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    await DeviceTokenRepository(db).delete(token)
    await db.commit()
    return DeviceAck()
