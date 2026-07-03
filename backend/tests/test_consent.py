from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-consent-1", email="consent@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


@pytest.mark.anyio
async def test_get_consent_empty(client):
    with _mock_verify(MOCK_USER):
        r = await client.get("/api/v1/consent/", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["consents"] == {}


@pytest.mark.anyio
async def test_record_consent_granted(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/consent/",
            headers=_auth_headers(),
            json={"consent_type": "audio_storage", "granted": True, "source": "onboarding"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["consent_type"] == "audio_storage"
    assert data["granted"] is True
    assert data["source"] == "onboarding"


@pytest.mark.anyio
async def test_effective_consent_reflects_latest(client):
    with _mock_verify(MOCK_USER):
        # Grant then revoke
        await client.post("/api/v1/consent/", headers=_auth_headers(),
                          json={"consent_type": "location_tracking", "granted": True})
        await client.post("/api/v1/consent/", headers=_auth_headers(),
                          json={"consent_type": "location_tracking", "granted": False})
        r = await client.get("/api/v1/consent/", headers=_auth_headers())
    assert r.status_code == 200
    assert r.json()["consents"]["location_tracking"] is False


@pytest.mark.anyio
async def test_invalid_consent_type_rejected(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/consent/",
            headers=_auth_headers(),
            json={"consent_type": "sell_data_to_advertisers", "granted": True},
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_revoke_audio_consent(client):
    with _mock_verify(MOCK_USER):
        # First grant both
        await client.post("/api/v1/consent/", headers=_auth_headers(),
                          json={"consent_type": "audio_storage", "granted": True})
        await client.post("/api/v1/consent/", headers=_auth_headers(),
                          json={"consent_type": "audio_training", "granted": True})
        # Now revoke
        r = await client.delete("/api/v1/consent/audio", headers=_auth_headers())
        assert r.status_code == 204
        # Verify effective state
        r2 = await client.get("/api/v1/consent/", headers=_auth_headers())
    consents = r2.json()["consents"]
    assert consents["audio_storage"] is False
    assert consents["audio_training"] is False


@pytest.mark.anyio
async def test_unauthenticated_consent_rejected(client):
    r = await client.get("/api/v1/consent/")
    assert r.status_code == 401
