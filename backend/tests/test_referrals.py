"""Tests for referral code generation, validation, and conversion reward."""
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.core.security import TokenUser, get_current_user
from app.main import app
from app.models import (  # noqa: F401
    AssistantPersonality,
    CalendarIntegration,
    ConsentRecord,
    Notification,
    OnboardingState,
    PendingCalendarAction,
    ReferralCode,
    ReferralConversion,
    ReplanRequest,
    Subscription,
    User,
    UserPreferences,
    UserProfile,
)
from app.models.base import Base
from app.services.referral_service import ReferralService
from app.services.subscription_service import SubscriptionService

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def referrer(db_session):
    user = User(firebase_uid="uid-referrer", email="referrer@example.com")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def referred(db_session):
    user = User(firebase_uid="uid-referred", email="referred@example.com")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def client(db_session):
    fake_user = TokenUser(uid="uid-referrer", email="referrer@example.com", role="user")

    async def _override_auth():
        return fake_user

    def _override_db():
        return db_session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ── Service-level tests ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_or_create_code_idempotent(db_session, referrer):
    svc = ReferralService(db_session)
    code1 = await svc.get_or_create_code(referrer.id)
    await db_session.commit()
    code2 = await svc.get_or_create_code(referrer.id)
    assert code1.id == code2.id
    assert len(code1.code) <= 10


@pytest.mark.anyio
async def test_validate_code(db_session, referrer):
    svc = ReferralService(db_session)
    code = await svc.get_or_create_code(referrer.id)
    await db_session.commit()

    result = await svc.validate_code(code.code)
    assert result is not None
    assert result.code == code.code

    invalid = await svc.validate_code("INVALID000")
    assert invalid is None


@pytest.mark.anyio
async def test_conversion_extends_subscriptions(db_session, referrer, referred):
    sub_svc = SubscriptionService(db_session)
    await sub_svc.start_trial(referrer.id, email=referrer.email, platform="stripe")
    await sub_svc.start_trial(referred.id, email=referred.email, platform="stripe")
    await db_session.commit()

    svc = ReferralService(db_session)
    code = await svc.get_or_create_code(referrer.id)
    await db_session.commit()

    conv = await svc.on_conversion(referred_user_id=referred.id, referral_code=code.code)
    await db_session.commit()

    assert conv is not None
    assert conv.status == "rewarded"

    referrer_sub = await sub_svc.get_subscription(referrer.id)
    referred_sub = await sub_svc.get_subscription(referred.id)
    assert referrer_sub.current_period_end is not None
    assert referred_sub.current_period_end is not None


@pytest.mark.anyio
async def test_no_double_conversion(db_session, referrer, referred):
    sub_svc = SubscriptionService(db_session)
    await sub_svc.start_trial(referrer.id, email=referrer.email, platform="stripe")
    await sub_svc.start_trial(referred.id, email=referred.email, platform="stripe")
    await db_session.commit()

    svc = ReferralService(db_session)
    code = await svc.get_or_create_code(referrer.id)
    await db_session.commit()

    first = await svc.on_conversion(referred_user_id=referred.id, referral_code=code.code)
    await db_session.commit()
    assert first is not None

    second = await svc.on_conversion(referred_user_id=referred.id, referral_code=code.code)
    assert second is None  # double-reward blocked


@pytest.mark.anyio
async def test_invalid_code_conversion_returns_none(db_session, referred):
    svc = ReferralService(db_session)
    result = await svc.on_conversion(referred_user_id=referred.id, referral_code="NOTACODE0")
    assert result is None


# ── API-level tests ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_api_get_my_code(client, referrer):
    resp = await client.get("/api/v1/referrals/my-code")
    assert resp.status_code == 200
    data = resp.json()
    assert "code" in data
    assert data["uses"] == 0


@pytest.mark.anyio
async def test_api_validate_code(client, db_session, referrer):
    svc = ReferralService(db_session)
    code = await svc.get_or_create_code(referrer.id)
    await db_session.commit()

    resp = await client.post("/api/v1/referrals/validate", json={"code": code.code})
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

    bad = await client.post("/api/v1/referrals/validate", json={"code": "BADCODE000"})
    assert bad.json()["valid"] is False
