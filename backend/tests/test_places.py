"""TIME-115 — saved places sync + coordinate plumbing into the engine context."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser

USER = TokenUser(uid="places-1", email="places@example.com", role="user", email_verified=True)


def _verify():
    return patch("app.core.security.firebase_auth.verify_id_token",
                 return_value={"uid": USER.uid, "email": USER.email, "role": "user",
                               "email_verified": True})


@pytest.mark.anyio
async def test_sync_and_list_places(client):
    with _verify():
        put = await client.put("/api/v1/places", headers={"Authorization": "Bearer t"}, json={
            "places": [
                {"name": "Home", "latitude": 40.0, "longitude": -75.0},
                {"name": "My Walmart", "place_type": "walmart", "latitude": 40.1, "longitude": -75.1},
            ]
        })
        assert put.status_code == 200 and len(put.json()) == 2
        got = await client.get("/api/v1/places", headers={"Authorization": "Bearer t"})
    names = {p["name"] for p in got.json()}
    assert names == {"Home", "My Walmart"}


@pytest.mark.anyio
async def test_sync_replaces_previous_places(client):
    with _verify():
        await client.put("/api/v1/places", headers={"Authorization": "Bearer t"},
                         json={"places": [{"name": "Old", "latitude": 1.0, "longitude": 1.0}]})
        await client.put("/api/v1/places", headers={"Authorization": "Bearer t"},
                         json={"places": [{"name": "New", "latitude": 2.0, "longitude": 2.0}]})
        got = await client.get("/api/v1/places", headers={"Authorization": "Bearer t"})
    assert [p["name"] for p in got.json()] == ["New"]


@pytest.mark.anyio
async def test_context_builder_uses_saved_place_as_origin_and_preferred(db_session):
    """When the user is at a saved place, its coords become the travel origin; saved places are
    exposed as preferred destinations."""
    from app.services.user_service import UserService
    from app.models.task import Task
    from app.models.user_place import UserPlace
    from app.models.user_location_state import UserLocationState
    from app.services.recommendation.context_builder import build_user_context

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    db_session.add_all([
        UserPlace(user_id=user.id, name="Home", latitude=40.0, longitude=-75.0),
        UserPlace(user_id=user.id, name="My Walmart", place_type="walmart",
                  latitude=40.1, longitude=-75.1),
        UserLocationState(user_id=user.id, place_name="Home", is_home=True),
    ])
    task = Task(user_id=user.id, title="Buy things", status="pending", priority=3)
    db_session.add(task)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    ctx, _ = await build_user_context(db_session, user, [task], now, usable_minutes=90)
    assert ctx.location_context.coordinates is not None          # origin resolved from saved Home
    assert ctx.location_context.coordinates.latitude == 40.0
    prefs = {p.name for p in ctx.user_preferences.preferred_places}
    assert prefs == {"Home", "My Walmart"}


@pytest.mark.anyio
async def test_engine_recommends_errand_when_maps_confirms_it_fits(db_session):
    """End-to-end with a stub provider: at a saved place with a preferred Walmart and a driveable
    trip that fits the free block, the errand leads."""
    from app.services.user_service import UserService
    from app.models.task import Task
    from app.models.user_place import UserPlace
    from app.models.user_location_state import UserLocationState
    from app.services.recommendation.context_builder import build_user_context
    from app.services.recommendation.engine import run_engine
    from app.services.recommendation.maps.maps_skill_service import MapsSkillService
    from app.services.recommendation.types import TravelEstimate

    class _Stub:
        available = True
        async def geocode(self, a): return None
        async def search_nearby(self, r): return []
        async def travel_estimate(self, r):
            return TravelEstimate(9000, 5.6, 600, 10.0, r.mode, "maps_api", 0.9)

    user, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    db_session.add_all([
        UserPlace(user_id=user.id, name="Errands", place_type="custom", latitude=40.0, longitude=-75.0),
        UserPlace(user_id=user.id, name="My Walmart", place_type="walmart", is_preferred=True,
                  latitude=40.1, longitude=-75.1),
        # currently out at "Errands" (a saved, non-home place → origin available)
        UserLocationState(user_id=user.id, place_name="Errands", is_home=False),
    ])
    walmart = Task(user_id=user.id, title="Go to Walmart", status="pending", priority=2,
                   due_at=datetime.now(timezone.utc) + timedelta(hours=3), estimated_minutes=45)
    db_session.add(walmart)
    await db_session.flush()

    now = datetime(2026, 7, 6, 14, 0, tzinfo=timezone.utc)  # afternoon (not night)
    ctx, _ = await build_user_context(db_session, user, [walmart], now, usable_minutes=90)
    rec = await run_engine(ctx, maps=MapsSkillService(_Stub()), now=now)
    assert rec.title == "Go to Walmart"
    assert "TRIP_FITS_FREE_BLOCK" in rec.reason_codes
    assert rec.travel_estimate is not None and rec.travel_estimate.duration_minutes == 10.0
