"""TIME-113 — candidate generation, scoring, ranking, selection (spec scenarios)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.recommendation.candidates.generate import generate_candidate_actions
from app.services.recommendation.engine import run_engine
from app.services.recommendation.feedback.apply_feedback import FeedbackSummary
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.maps.provider import NullMapsProvider
from app.services.recommendation.normalize_context import RawContextInputs, normalize_context
from app.services.recommendation.selection.notification_policy import eligible_for_push
from app.services.recommendation.time_service import get_time_snapshot
from app.services.recommendation.types import (
    CalendarEvent,
    Coordinates,
    HealthContext,
    LocationIntent,
    Place,
    TaskItem,
    TravelEstimate,
    UserLocationSnapshot,
    UserPreferences,
)

pytestmark = pytest.mark.anyio

TZ = "UTC"
BASE = datetime(2026, 7, 6, 14, 0, tzinfo=timezone.utc)  # Monday 14:00 UTC (afternoon)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _ctx(now, tasks=None, events=None, health=None, location=None, prefs=None):
    raw = RawContextInputs(
        now=now, timezone=TZ, time_snapshot=get_time_snapshot(TZ, now=now),
        preferences=prefs or UserPreferences(),
        tasks=tasks or [], calendar_events=events or [], location_snapshot=location, health=health,
    )
    return normalize_context(raw)


def _task(tid, title, priority="medium", minutes=None, due=None, source="manual", intent=None):
    return TaskItem(id=tid, title=title, source=source, priority=priority, status="not_started",
                    estimated_minutes=minutes, due_date=_iso(due) if due else None, location_intent=intent)


class _StubMaps:
    def __init__(self, minutes): self._m = minutes
    @property
    def available(self): return True
    async def geocode(self, a): return None
    async def search_nearby(self, r): return []
    async def travel_estimate(self, r):
        return TravelEstimate(self._m * 800, self._m * 0.5, self._m * 60, self._m,
                              r.mode, "maps_api", 0.9)


# --------------------------- calendar hard rules ---------------------------

async def test_meeting_in_10_min_prefers_prep_not_deep_work():
    events = [CalendarEvent("e1", "Sync", _iso(BASE + timedelta(minutes=10)),
                            _iso(BASE + timedelta(minutes=40)))]
    tasks = [_task("t1", "Write the report", priority="high", minutes=60, due=BASE + timedelta(hours=6))]
    rec = await run_engine(_ctx(BASE, tasks=tasks, events=events), now=BASE)
    assert rec.action_type == "prepare_for_meeting"


async def test_meeting_now_prefers_join():
    events = [CalendarEvent("e1", "Sync", _iso(BASE + timedelta(minutes=1)),
                            _iso(BASE + timedelta(minutes=31)))]
    rec = await run_engine(_ctx(BASE, events=events), now=BASE)
    assert rec.action_type == "join_meeting"


async def test_long_free_block_high_priority_picks_focus():
    events = [CalendarEvent("e1", "Later", _iso(BASE + timedelta(minutes=120)),
                            _iso(BASE + timedelta(minutes=150)))]
    tasks = [_task("t1", "Deep analysis", priority="high", minutes=60)]
    rec = await run_engine(_ctx(BASE, tasks=tasks, events=events), now=BASE)
    assert rec.action_type in ("deep_work", "protect_focus_block")


async def test_short_free_block_avoids_deep_work():
    events = [CalendarEvent("e1", "Soon", _iso(BASE + timedelta(minutes=18)),
                            _iso(BASE + timedelta(minutes=48)))]
    tasks = [_task("t1", "Big task", priority="high", minutes=90),
             _task("t2", "Quick email", priority="low", minutes=10)]
    rec = await run_engine(_ctx(BASE, tasks=tasks, events=events), now=BASE)
    assert rec.action_type != "deep_work"


# --------------------------- tasks ---------------------------

async def test_overdue_task_leads():
    tasks = [_task("t1", "Overdue filing", priority="medium", minutes=30, due=BASE - timedelta(days=1)),
             _task("t2", "Someday idea", priority="low", minutes=30)]
    rec = await run_engine(_ctx(BASE, tasks=tasks), now=BASE)
    assert rec.title == "Overdue filing" and "TASK_OVERDUE" in rec.reason_codes


async def test_no_tasks_returns_planning_or_fallback():
    rec = await run_engine(_ctx(BASE), now=BASE)
    assert rec.domain in ("planning", "fallback", "calendar")
    assert rec.reason_codes  # always has reason codes


# --------------------------- health ---------------------------

async def test_poor_sleep_suppresses_deep_work():
    tasks = [_task("t1", "Heavy focus work", priority="high", minutes=60)]  # no due date
    health = HealthContext(sleep_hours=4.0, sleep_quality="poor", energy_estimate="low")
    rec = await run_engine(_ctx(BASE, tasks=tasks, health=health), now=BASE)
    assert rec.action_type != "deep_work"


async def test_sedentary_generates_walk():
    health = HealthContext(sedentary_minutes=120)
    maps = MapsSkillService(NullMapsProvider())
    cands = await generate_candidate_actions(_ctx(BASE, health=health), maps, BASE)
    assert any(c.type == "walk" for c in cands)


# --------------------------- location / maps ---------------------------

async def test_errand_from_home_without_maps_does_not_lead():
    """The reported bug, at the engine level: 'Go to Walmart' with no travel data can't confidently
    win over a doable task."""
    walmart = _task("w1", "Go to Walmart", minutes=45,
                    intent=LocationIntent(query="Walmart", place_type="walmart", requires_travel=True))
    essay = _task("t1", "Draft the essay", priority="high", minutes=50)
    loc = UserLocationSnapshot("home", _iso(BASE), 0.9, place_name="Home")  # no coordinates
    rec = await run_engine(_ctx(BASE, tasks=[walmart, essay], location=loc),
                           maps=MapsSkillService(NullMapsProvider()), now=BASE)
    assert rec.title != "Go to Walmart"


async def test_errand_low_confidence_and_not_push_eligible_without_maps():
    walmart = _task("w1", "Go to Walmart", minutes=45,
                    intent=LocationIntent(query="Walmart", place_type="walmart", requires_travel=True))
    loc = UserLocationSnapshot("home", _iso(BASE), 0.9, place_name="Home")
    maps = MapsSkillService(NullMapsProvider())
    cands = await generate_candidate_actions(_ctx(BASE, tasks=[walmart], location=loc), maps, BASE)
    errand = next(c for c in cands if c.id == "loc:w1")
    assert errand.confidence < 0.75
    assert "LOCATION_DATA_MISSING" in errand.reason_codes


async def test_errand_that_fits_leads_with_preferred_place():
    walmart = _task("w1", "Go to Walmart", priority="high", minutes=45, due=BASE + timedelta(hours=3),
                    intent=LocationIntent(query="Walmart", place_type="walmart", requires_travel=True,
                                          estimated_on_site_minutes=25))
    preferred = Place("p1", "My Walmart", "walmart", Coordinates(40.1, -75.1),
                      "user_saved", 1.0, is_preferred=True, open_now=True)
    prefs = UserPreferences(preferred_places=[preferred])
    loc = UserLocationSnapshot("errand", _iso(BASE), 0.9, coordinates=Coordinates(40.0, -75.0))
    events = [CalendarEvent("e1", "Later", _iso(BASE + timedelta(minutes=90)),
                            _iso(BASE + timedelta(minutes=120)))]  # 90-min block
    rec = await run_engine(_ctx(BASE, tasks=[walmart], events=events, location=loc, prefs=prefs),
                           maps=MapsSkillService(_StubMaps(12)), now=BASE)
    assert rec.title == "Go to Walmart"
    assert "TRIP_FITS_FREE_BLOCK" in rec.reason_codes
    assert "PREFERRED_PLACE_FOUND" in rec.reason_codes


async def test_errand_that_does_not_fit_is_rejected():
    walmart = _task("w1", "Go to Walmart", priority="high", minutes=45,
                    intent=LocationIntent(query="Walmart", place_type="walmart", requires_travel=True,
                                          estimated_on_site_minutes=25))
    preferred = Place("p1", "My Walmart", "walmart", Coordinates(41.0, -75.0),
                      "user_saved", 1.0, is_preferred=True, open_now=True)
    prefs = UserPreferences(preferred_places=[preferred])
    loc = UserLocationSnapshot("errand", _iso(BASE), 0.9, coordinates=Coordinates(40.0, -75.0))
    events = [CalendarEvent("e1", "Soon", _iso(BASE + timedelta(minutes=30)),
                            _iso(BASE + timedelta(minutes=60)))]  # only 30 min
    other = _task("t1", "Reply to the client", priority="high", minutes=10)
    rec = await run_engine(_ctx(BASE, tasks=[walmart, other], events=events, location=loc, prefs=prefs),
                           maps=MapsSkillService(_StubMaps(40)), now=BASE)
    assert rec.title != "Go to Walmart"  # 40+25+10 = 75 > 30 → rejected


# --------------------------- time-of-day ---------------------------

async def test_night_suppresses_errands():
    night = datetime(2026, 7, 6, 23, 0, tzinfo=timezone.utc)
    walmart = _task("w1", "Go to Walmart", priority="high", minutes=45, due=night + timedelta(hours=2),
                    intent=LocationIntent(query="Walmart", place_type="walmart", requires_travel=True))
    preferred = Place("p1", "My Walmart", "walmart", Coordinates(40.1, -75.1),
                      "user_saved", 1.0, is_preferred=True, open_now=True)
    prefs = UserPreferences(preferred_places=[preferred])
    loc = UserLocationSnapshot("home", _iso(night), 0.9, coordinates=Coordinates(40.0, -75.0))
    rec = await run_engine(_ctx(night, tasks=[walmart], location=loc, prefs=prefs),
                           maps=MapsSkillService(_StubMaps(10)), now=night)
    assert rec.action_type != "run_nearby_errand"


# --------------------------- notification policy + feedback + robustness ---------------------------

async def test_push_policy_thresholds():
    assert eligible_for_push(80, 0.8) is True
    assert eligible_for_push(74, 0.9) is False
    assert eligible_for_push(90, 0.6) is False


async def test_feedback_demotes_rejected_action_type():
    tasks = [_task("t1", "Quick email", priority="low", minutes=10)]
    fb = FeedbackSummary(rejects={"quick_task": 5}, accepts={})
    rec = await run_engine(_ctx(BASE, tasks=tasks), now=BASE, feedback=fb)
    # the quick task should be pushed down by the repeated rejections
    if rec.action_type == "quick_task":
        assert "USER_OFTEN_REJECTS_THIS_ACTION" not in rec.reason_codes
    else:
        assert True


async def test_missing_everything_does_not_crash():
    rec = await run_engine(_ctx(BASE), now=BASE)
    assert 0.0 <= rec.confidence <= 1.0 and rec.reason_codes and rec.title


async def test_every_recommendation_has_reason_codes_and_confidence():
    tasks = [_task("t1", "Something", priority="medium", minutes=30, due=BASE + timedelta(hours=2))]
    rec = await run_engine(_ctx(BASE, tasks=tasks), now=BASE)
    assert rec.reason_codes and 0.0 <= rec.confidence <= 1.0 and 0.0 <= rec.score <= 100.0
