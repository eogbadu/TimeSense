from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.repositories.device_token_repository import DeviceTokenRepository
from app.services.push.factory import get_push_sender
from app.services.push.push_service import ProactivePushService
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


class TestPushIn(BaseModel):
    title: str | None = Field(default=None, max_length=128)
    body: str | None = Field(default=None, max_length=256)


class TestPushOut(BaseModel):
    apns_available: bool       # False → APNs isn't configured on the server (nothing delivered)
    delivered: int
    title: str | None = None
    body: str | None = None
    action_type: str | None = None
    reason: str | None = None  # e.g. "no_device"


@router.post("/test-push", response_model=TestPushOut)
async def test_push(
    body: TestPushIn,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> TestPushOut:
    """Send a push to YOUR OWN devices right now, bypassing eligibility + cooldown — for verifying
    the APNs chain. Provide {title, body} to test raw delivery, or omit them to push the engine's
    current recommendation. apns_available=false means the server has no APNs credentials."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    result = await ProactivePushService(db).send_test(
        user, get_push_sender(), gateway=gateway, title=body.title, body=body.body
    )
    return TestPushOut(**result)


class OfferOut(BaseModel):
    offered: bool
    title: str | None = None
    body: str | None = None
    delivered: int = 0


@router.post("/test-offer", response_model=OfferOut)
async def test_offer(
    current_user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> OfferOut:
    """Fire a 'block time for a high-priority task' offer to your own devices now, bypassing the
    cooldown — to verify the proactive offer. Returns offered=false if there's no suitable task/slot."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    result = await ProactivePushService(db).offer_time_block_for_user(
        user, get_push_sender(), respect_cooldown=False
    )
    if result is None:
        return OfferOut(offered=False)
    return OfferOut(offered=True, title=result["title"], body=result["body"],
                    delivered=result["delivered"])
