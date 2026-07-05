from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

MOCK_USER = TokenUser(uid="uid-commute-1", email="commute@example.com", role="user", email_verified=True)
OTHER_USER = TokenUser(uid="uid-commute-2", email="commute-other@example.com", role="user", email_verified=True)

# ~5.5km apart — well over the 500m displacement threshold
HOME = (37.7749, -122.4194)
OFFICE = (37.8044, -122.2712)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


async def _grant_location_consent(client, user: TokenUser):
    with _mock_verify(user):
        await client.post(
            "/api/v1/consent/",
            headers=_auth_headers(),
            json={"consent_type": "location_tracking", "granted": True},
        )


def _commuting_pings(start_hour: int = 8):
    start = datetime.now(timezone.utc).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    return [
        {"lat": HOME[0], "lng": HOME[1], "timestamp": start.isoformat()},
        {"lat": OFFICE[0], "lng": OFFICE[1], "timestamp": (start + timedelta(minutes=30)).isoformat()},
    ]


@pytest.mark.anyio
async def test_detect_without_consent_returns_403(client):
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/commute/detect",
            headers=_auth_headers(),
            json={"pings": _commuting_pings()},
        )
    assert r.status_code == 403


@pytest.mark.anyio
async def test_detect_commute_creates_pending_event(client):
    await _grant_location_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/commute/detect",
            headers=_auth_headers(),
            json={"pings": _commuting_pings(start_hour=8)},
        )
    assert r.status_code == 200
    data = r.json()
    assert data is not None
    assert data["status"] == "pending"
    assert data["direction"] == "to_work"
    assert data["estimated_minutes"] == 30


@pytest.mark.anyio
async def test_detect_evening_commute_is_to_home(client):
    await _grant_location_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/commute/detect",
            headers=_auth_headers(),
            json={"pings": _commuting_pings(start_hour=18)},
        )
    assert r.json()["direction"] == "to_home"


@pytest.mark.anyio
async def test_detect_no_movement_returns_none(client):
    await _grant_location_consent(client, MOCK_USER)
    start = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    pings = [
        {"lat": HOME[0], "lng": HOME[1], "timestamp": start.isoformat()},
        {"lat": HOME[0], "lng": HOME[1], "timestamp": (start + timedelta(minutes=30)).isoformat()},
    ]
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/commute/detect", headers=_auth_headers(), json={"pings": pings}
        )
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.anyio
async def test_detect_too_slow_elapsed_time_returns_none(client):
    await _grant_location_consent(client, MOCK_USER)
    start = datetime.now(timezone.utc).replace(hour=8, minute=0, second=0, microsecond=0)
    pings = [
        {"lat": HOME[0], "lng": HOME[1], "timestamp": start.isoformat()},
        {"lat": OFFICE[0], "lng": OFFICE[1], "timestamp": (start + timedelta(hours=5)).isoformat()},
    ]
    with _mock_verify(MOCK_USER):
        r = await client.post(
            "/api/v1/commute/detect", headers=_auth_headers(), json={"pings": pings}
        )
    assert r.json() is None


@pytest.mark.anyio
async def test_confirm_pending_commute(client):
    await _grant_location_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        detect_r = await client.post(
            "/api/v1/commute/detect", headers=_auth_headers(), json={"pings": _commuting_pings()}
        )
        commute_id = detect_r.json()["id"]
        r = await client.post(f"/api/v1/commute/{commute_id}/confirm", headers=_auth_headers())
    assert r.status_code == 204

    with _mock_verify(MOCK_USER):
        pending_r = await client.get("/api/v1/commute/pending", headers=_auth_headers())
    assert pending_r.json() == []


@pytest.mark.anyio
async def test_reject_pending_commute(client):
    await _grant_location_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        detect_r = await client.post(
            "/api/v1/commute/detect", headers=_auth_headers(), json={"pings": _commuting_pings()}
        )
        commute_id = detect_r.json()["id"]
        r = await client.post(f"/api/v1/commute/{commute_id}/reject", headers=_auth_headers())
    assert r.status_code == 204


@pytest.mark.anyio
async def test_confirm_unknown_commute_404(client):
    await _grant_location_consent(client, MOCK_USER)
    import uuid
    with _mock_verify(MOCK_USER):
        r = await client.post(f"/api/v1/commute/{uuid.uuid4()}/confirm", headers=_auth_headers())
    assert r.status_code == 404


@pytest.mark.anyio
async def test_commutes_are_per_user(client):
    await _grant_location_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        detect_r = await client.post(
            "/api/v1/commute/detect", headers=_auth_headers(), json={"pings": _commuting_pings()}
        )
        commute_id = detect_r.json()["id"]

    with _mock_verify(OTHER_USER):
        r = await client.post(f"/api/v1/commute/{commute_id}/confirm", headers=_auth_headers())
    assert r.status_code == 404


@pytest.mark.anyio
async def test_pending_list_only_this_user(client):
    await _grant_location_consent(client, MOCK_USER)
    with _mock_verify(MOCK_USER):
        await client.post(
            "/api/v1/commute/detect", headers=_auth_headers(), json={"pings": _commuting_pings()}
        )

    with _mock_verify(OTHER_USER):
        r = await client.get("/api/v1/commute/pending", headers=_auth_headers())
    assert r.json() == []


@pytest.mark.anyio
async def test_commute_detect_unauthenticated(client):
    r = await client.post("/api/v1/commute/detect", json={"pings": _commuting_pings()})
    assert r.status_code == 401
