"""TIME-112 — recommendation engine foundation (phases 1-6): time/location/maps/travel/normalize."""

from datetime import datetime, timezone

import pytest

from app.services.recommendation.maps.maps_skill_service import MapsSkillService, haversine_meters
from app.services.recommendation.maps.provider import NullMapsProvider
from app.services.recommendation.normalize_context import RawContextInputs, normalize_context
from app.services.recommendation.time_service import get_time_snapshot, part_of_day
from app.services.recommendation.travel_feasibility_service import (
    TravelFeasibilityRequest,
    calculate_travel_feasibility,
)
from app.services.recommendation.types import (
    CalendarEvent,
    Coordinates,
    LocationIntent,
    Place,
    PlaceLookupRequest,
    TaskItem,
    TravelEstimate,
    TravelEstimateRequest,
    UserLocationSnapshot,
    UserPreferences,
)

pytestmark = pytest.mark.anyio


# ----------------------------- time service -----------------------------

async def test_time_snapshot_is_timezone_aware_and_deterministic():
    # 2026-07-06 is a Monday; 14:30 UTC == 10:30 America/New_York (EDT)
    now = datetime(2026, 7, 6, 14, 30, tzinfo=timezone.utc)
    snap = get_time_snapshot("America/New_York", now=now)
    assert snap.timezone == "America/New_York"
    assert snap.hour == 10 and snap.part_of_day == "morning"
    assert snap.day_of_week == "Monday" and snap.is_weekend is False
    assert snap.is_work_hours is True


async def test_part_of_day_boundaries():
    assert part_of_day(6) == "early_morning"
    assert part_of_day(9) == "morning"
    assert part_of_day(12) == "midday"
    assert part_of_day(15) == "afternoon"
    assert part_of_day(19) == "evening"
    assert part_of_day(23) == "night" and part_of_day(3) == "night"


async def test_weekend_is_not_work_hours():
    sat = datetime(2026, 7, 11, 15, 0, tzinfo=timezone.utc)  # Saturday
    snap = get_time_snapshot("UTC", now=sat)
    assert snap.is_weekend is True and snap.is_work_hours is False


async def test_bad_timezone_falls_back_to_utc():
    now = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)
    snap = get_time_snapshot("Not/AZone", now=now)
    assert snap.hour == 12  # UTC


# ----------------------------- maps skill (null provider) -----------------------------

async def test_null_maps_provider_returns_nothing():
    maps = MapsSkillService(NullMapsProvider())
    assert maps.available is False
    assert await maps.geocode_address("1600 Amphitheatre") is None
    assert await maps.search_nearby_places(PlaceLookupRequest(query="Walmart")) == []
    est = await maps.get_travel_estimate(
        TravelEstimateRequest(Coordinates(0, 0), Coordinates(1, 1), "driving")
    )
    assert est is None


async def test_resolve_prefers_saved_place_without_provider():
    home_walmart = Place(id="w1", name="Walmart Supercenter", type="walmart",
                         coordinates=Coordinates(40.0, -75.0), source="user_saved",
                         confidence=1.0, is_preferred=True)
    maps = MapsSkillService(NullMapsProvider())
    resolved = await maps.resolve_relevant_place(
        PlaceLookupRequest(query="Walmart", place_type="walmart",
                           user_location=Coordinates(40.0, -75.01),
                           preferred_places=[home_walmart])
    )
    assert resolved is not None and resolved.id == "w1"


async def test_resolve_returns_none_when_no_preferred_and_no_provider():
    maps = MapsSkillService(NullMapsProvider())
    resolved = await maps.resolve_relevant_place(PlaceLookupRequest(query="Walmart", place_type="walmart"))
    assert resolved is None  # can't search without a provider → never invents a place


async def test_haversine_orders_by_distance():
    origin = Coordinates(40.0, -75.0)
    near = Coordinates(40.01, -75.0)
    far = Coordinates(41.0, -75.0)
    assert haversine_meters(origin, near) < haversine_meters(origin, far)


# ----------------------------- travel feasibility -----------------------------

class _StubProvider:
    """Deterministic provider: 12-minute drive, used to exercise feasibility math."""

    def __init__(self, minutes: float = 12.0) -> None:
        self._minutes = minutes

    @property
    def available(self) -> bool:
        return True

    async def geocode(self, address):  # pragma: no cover - unused here
        return None

    async def search_nearby(self, request):  # pragma: no cover - unused here
        return []

    async def travel_estimate(self, request):
        return TravelEstimate(
            distance_meters=self._minutes * 800, distance_miles=self._minutes * 0.5,
            duration_seconds=self._minutes * 60, duration_minutes=self._minutes,
            mode=request.mode, source="maps_api", confidence=0.9,
        )


def _place() -> Place:
    return Place(id="w1", name="Walmart", type="walmart", coordinates=Coordinates(40.1, -75.1),
                 source="user_saved", confidence=1.0)


async def test_feasibility_fits_free_block():
    maps = MapsSkillService(_StubProvider(minutes=12))
    req = TravelFeasibilityRequest(origin=Coordinates(40, -75), destination_place=_place(),
                                   estimated_on_site_minutes=25, mode="driving",
                                   departure_time="2026-07-06T17:00:00+00:00", free_block_minutes=90)
    feas = await calculate_travel_feasibility(req, maps)
    assert feas is not None
    # 12 + 25 + 0 + 10 = 47 <= 90
    assert feas.total_required_minutes == 47 and feas.fits_in_current_free_block is True


async def test_feasibility_rejects_when_over_block():
    maps = MapsSkillService(_StubProvider(minutes=30))
    req = TravelFeasibilityRequest(origin=Coordinates(40, -75), destination_place=_place(),
                                   estimated_on_site_minutes=25, mode="driving",
                                   departure_time="2026-07-06T17:00:00+00:00", free_block_minutes=45)
    feas = await calculate_travel_feasibility(req, maps)
    assert feas is not None
    # 30 + 25 + 10 = 65 > 45
    assert feas.fits_in_current_free_block is False


async def test_feasibility_none_without_maps():
    maps = MapsSkillService(NullMapsProvider())
    req = TravelFeasibilityRequest(origin=Coordinates(40, -75), destination_place=_place(),
                                   estimated_on_site_minutes=25, mode="driving",
                                   departure_time="2026-07-06T17:00:00+00:00", free_block_minutes=90)
    assert await calculate_travel_feasibility(req, maps) is None  # never guesses


# ----------------------------- normalize context -----------------------------

def _raw(now: datetime, tasks=None, events=None, location=None) -> RawContextInputs:
    return RawContextInputs(
        now=now, timezone="UTC",
        time_snapshot=get_time_snapshot("UTC", now=now),
        preferences=UserPreferences(),
        tasks=tasks or [], calendar_events=events or [], location_snapshot=location,
    )


async def test_normalize_buckets_tasks_and_derives_free_block():
    now = datetime(2026, 7, 6, 15, 0, tzinfo=timezone.utc)
    tasks = [
        TaskItem(id="t1", title="Overdue report", source="manual", priority="high",
                 status="not_started", due_date="2026-07-05T00:00:00+00:00", estimated_minutes=60),
        TaskItem(id="t2", title="Reply email", source="manual", priority="low",
                 status="not_started", estimated_minutes=10),
        TaskItem(id="t3", title="Go to Walmart", source="manual", priority="medium",
                 status="not_started", estimated_minutes=45,
                 location_intent=LocationIntent(query="Walmart", place_type="walmart", requires_travel=True)),
    ]
    events = [CalendarEvent(id="e1", title="Standup", start_time="2026-07-06T16:00:00+00:00",
                            end_time="2026-07-06T16:30:00+00:00")]
    ctx = normalize_context(_raw(now, tasks=tasks, events=events))

    assert [t.id for t in ctx.task_context.overdue_tasks] == ["t1"]
    assert [t.id for t in ctx.task_context.quick_tasks] == ["t2"]
    assert [t.id for t in ctx.task_context.deep_work_tasks] == ["t1", "t3"]
    assert [t.id for t in ctx.task_context.location_linked_tasks] == ["t3"]
    assert ctx.task_context.high_priority_tasks[0].id == "t1"
    # next event 60 min out → free block 60
    assert ctx.calendar_context.minutes_until_next_event == 60
    assert ctx.calendar_context.free_block_minutes == 60
    assert ctx.calendar_context.has_hard_deadline_today is True
    assert ctx.calendar_context.next_event is not None


async def test_normalize_open_free_block_without_events():
    now = datetime(2026, 7, 6, 15, 0, tzinfo=timezone.utc)
    ctx = normalize_context(_raw(now))
    assert ctx.calendar_context.next_event is None
    assert ctx.calendar_context.free_block_minutes == 180  # OPEN_FREE_BLOCK_MINUTES
    assert ctx.calendar_context.has_hard_deadline_today is False


async def test_normalize_current_event_detected():
    now = datetime(2026, 7, 6, 16, 15, tzinfo=timezone.utc)
    events = [CalendarEvent(id="e1", title="Standup", start_time="2026-07-06T16:00:00+00:00",
                            end_time="2026-07-06T16:30:00+00:00")]
    ctx = normalize_context(_raw(now, events=events))
    assert ctx.calendar_context.current_event is not None
    assert ctx.calendar_context.current_event.id == "e1"


async def test_normalize_passes_location_snapshot_through():
    now = datetime(2026, 7, 6, 15, 0, tzinfo=timezone.utc)
    loc = UserLocationSnapshot(location_category="home", last_updated_at=now.isoformat(),
                               confidence=0.9, place_name="Home")
    ctx = normalize_context(_raw(now, location=loc))
    assert ctx.location_context is not None and ctx.location_context.location_category == "home"
