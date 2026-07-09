"""TIME-164 — explicit Capture inputs (time/date/location) override the parse."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from app.core.security import TokenUser

USER = TokenUser(uid="cap-ov", email="capov@example.com", role="user", email_verified=True)
def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user", "email_verified": True})

@pytest.mark.anyio
async def test_explicit_scheduled_at_and_location_override(client, db_session):
    when = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    with _verify():
        r = await client.post("/api/v1/capture", headers={"Authorization": "Bearer t"}, json={
            "raw_input": "pick up groceries",
            "scheduled_at": when.isoformat(),
            "location_name": "Walmart Supercenter", "location_lat": 39.2, "location_lng": -76.8,
        })
    body = r.json()
    assert body["location_name"] == "Walmart Supercenter"
    assert body["scheduled_start"] is not None
    assert body["scheduled_end"] is not None  # end block derived from duration

@pytest.mark.anyio
async def test_places_search_returns_saved(client, db_session):
    with _verify():
        await client.put("/api/v1/places", headers={"Authorization": "Bearer t"}, json={
            "places": [{"name": "Home Gym", "latitude": 39.1, "longitude": -76.7, "is_preferred": True}]})
        r = await client.get("/api/v1/places/search?q=gym", headers={"Authorization": "Bearer t"})
    names = [p["name"] for p in r.json()]
    assert "Home Gym" in names
