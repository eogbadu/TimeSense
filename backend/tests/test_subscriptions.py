"""
Tests for subscription entitlement endpoints.
Stripe API calls are mocked — no real Stripe keys needed.
Webhook signature verification is mocked to test dispatch logic directly.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-sub-1", email="sub@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser = MOCK_USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


def _mock_stripe_customer(customer_id: str = "cus_test123"):
    mock = MagicMock()
    mock.id = customer_id
    return patch("stripe.Customer.create", return_value=mock)


@pytest.mark.anyio
async def test_get_subscription_none_before_trial(client):
    with _mock_verify():
        r = await client.get("/api/v1/subscriptions/me", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.anyio
async def test_entitlement_false_before_trial(client):
    with _mock_verify():
        r = await client.get("/api/v1/subscriptions/me/entitlement", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["is_premium"] is False
    assert data["status"] is None


@pytest.mark.anyio
async def test_start_trial_creates_subscription(client):
    with _mock_verify(), _mock_stripe_customer():
        r = await client.post("/api/v1/subscriptions/trial", headers=_auth_headers(),
                              json={"platform": "stripe"})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "trialing"
    assert data["is_premium"] is True
    assert data["platform"] == "stripe"
    assert data["trial_end"] is not None


@pytest.mark.anyio
async def test_start_trial_idempotent(client):
    with _mock_verify(), _mock_stripe_customer():
        r1 = await client.post("/api/v1/subscriptions/trial", headers=_auth_headers(),
                               json={"platform": "stripe"})
        r2 = await client.post("/api/v1/subscriptions/trial", headers=_auth_headers(),
                               json={"platform": "stripe"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.anyio
async def test_entitlement_true_during_trial(client):
    with _mock_verify(), _mock_stripe_customer():
        await client.post("/api/v1/subscriptions/trial", headers=_auth_headers(),
                          json={"platform": "stripe"})
        r = await client.get("/api/v1/subscriptions/me/entitlement", headers=_auth_headers())
    assert r.json()["is_premium"] is True


@pytest.mark.anyio
async def test_stripe_webhook_missing_secret_returns_503(client):
    with patch("app.core.config.settings.stripe_webhook_secret", ""):
        r = await client.post(
            "/api/v1/subscriptions/webhooks/stripe",
            content=b'{"type":"test"}',
            headers={"stripe-signature": "t=1,v1=abc"},
        )
    assert r.status_code == 503


@pytest.mark.anyio
async def test_stripe_webhook_bad_signature_returns_400(client):
    with patch("app.core.config.settings.stripe_webhook_secret", "whsec_test"):
        r = await client.post(
            "/api/v1/subscriptions/webhooks/stripe",
            content=b'{"type":"test"}',
            headers={"stripe-signature": "t=1,v1=badsig"},
        )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_subscription_service_invoice_paid_activates(client):
    """Test that invoice.paid event moves subscription from trialing to active."""
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.database import Base
    from app.repositories.subscription_repository import SubscriptionRepository
    from app.services.subscription_service import SubscriptionService
    from tests.conftest import TEST_DATABASE_URL

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        user_id = uuid.uuid4()
        repo = SubscriptionRepository(session)
        sub = await repo.start_trial(user_id=user_id, platform="stripe", platform_customer_id="cus_abc")
        await session.commit()
        assert sub.status == "trialing"

        svc = SubscriptionService(session)
        handled = await svc.handle_stripe_event({
            "type": "invoice.paid",
            "data": {"object": {"customer": "cus_abc", "subscription": "sub_xyz"}},
        })
        await session.commit()
        assert handled is True

        updated = await repo.get_by_user_id(user_id)
        assert updated.status == "active"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
