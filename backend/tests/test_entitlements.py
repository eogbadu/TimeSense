"""Tests for Premium gate dependency and feature flag endpoint."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.security import TokenUser

FREE_USER = TokenUser(uid="uid-free-1", email="free@example.com", role="user", email_verified=True)
PREMIUM_USER_TOKEN = TokenUser(uid="uid-premium-1", email="premium@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


def _mock_stripe_customer(customer_id: str = "cus_gate_test"):
    mock = MagicMock()
    mock.id = customer_id
    return patch("stripe.Customer.create", return_value=mock)


@pytest.mark.anyio
async def test_premium_gate_blocks_free_user(client):
    with _mock_verify(FREE_USER):
        r = await client.get("/api/v1/subscriptions/premium-only-example", headers=_auth_headers())
    assert r.status_code == 403
    data = r.json()
    assert data["detail"]["code"] == "SUBSCRIPTION_REQUIRED"


@pytest.mark.anyio
async def test_premium_gate_allows_trialing_user(client):
    with _mock_verify(PREMIUM_USER_TOKEN), _mock_stripe_customer():
        await client.post("/api/v1/subscriptions/trial", headers=_auth_headers(),
                          json={"platform": "stripe"})
        r = await client.get("/api/v1/subscriptions/premium-only-example", headers=_auth_headers())
    assert r.status_code == 200


@pytest.mark.anyio
async def test_feature_flags_free_user(client):
    with _mock_verify(FREE_USER):
        r = await client.get("/api/v1/subscriptions/me/features", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["is_premium"] is False
    assert data["flags"]["capture_basic"] is True
    assert data["flags"]["ai_suggestions"] is False
    assert data["flags"]["calendar_write"] is False


@pytest.mark.anyio
async def test_feature_flags_premium_user(client):
    with _mock_verify(PREMIUM_USER_TOKEN), _mock_stripe_customer():
        await client.post("/api/v1/subscriptions/trial", headers=_auth_headers(),
                          json={"platform": "stripe"})
        r = await client.get("/api/v1/subscriptions/me/features", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["is_premium"] is True
    assert data["flags"]["ai_suggestions"] is True
    assert data["flags"]["calendar_write"] is True
    assert data["flags"]["capture_basic"] is True


@pytest.mark.anyio
async def test_premium_gate_unauthenticated(client):
    r = await client.get("/api/v1/subscriptions/premium-only-example")
    assert r.status_code == 401
