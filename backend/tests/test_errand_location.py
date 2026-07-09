"""TIME-167 — the engine uses a task's stored errand location directly (not the title)."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.recommendation.candidates.location_candidates import _one
from app.services.recommendation.context_builder import _location_intent
from app.services.recommendation.maps.factory import get_maps_provider
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.types import Coordinates, LocationIntent, TaskItem


def test_location_intent_prefers_stored_coordinates():
    task = SimpleNamespace(title="Pick up stuff", location_name="Walmart Supercenter",
                           location_lat=39.2, location_lng=-76.8)
    intent = _location_intent(task)
    assert intent is not None and intent.coordinates is not None
    assert intent.query == "Walmart Supercenter"


@pytest.mark.anyio
async def test_explicit_location_used_directly_without_maps():
    task = TaskItem(id="1", title="Pick up groceries", source="manual", priority="medium",
                    status="not_started",
                    location_intent=LocationIntent(query="Walmart", requires_travel=True,
                                                   coordinates=Coordinates(latitude=39.2, longitude=-76.8)))
    ctx = SimpleNamespace(
        location_context=SimpleNamespace(coordinates=Coordinates(latitude=39.15, longitude=-76.75),
                                         location_category="away"),
        calendar_context=SimpleNamespace(free_block_minutes=180),
        user_preferences=SimpleNamespace(preferred_places=[], default_travel_mode="driving"),
        timestamp=datetime.now(),
    )
    maps = MapsSkillService(get_maps_provider())  # NullProvider in tests -> unavailable
    cand = await _one(task, ctx, maps, datetime.now())
    assert cand.destination_place is not None
    assert cand.destination_place.coordinates.latitude == 39.2   # the exact stored place
    assert "PREFERRED_PLACE_FOUND" in cand.reason_codes
    assert "DRIVING_TIME_CALCULATED" in cand.reason_codes        # estimated from straight line
