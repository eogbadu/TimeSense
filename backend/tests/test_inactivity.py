"""TIME-160 — sedentary/inactivity drives a 'take a walk' recommendation."""

from datetime import datetime
from types import SimpleNamespace

from app.services.recommendation.candidates.health_candidates import generate_health_candidates
from app.services.recommendation.types import HealthContext


def _ctx(sedentary):
    # generate_health_candidates only reads health_context + time_context.part_of_day.
    return SimpleNamespace(
        time_context=SimpleNamespace(part_of_day="afternoon"),
        health_context=HealthContext(
            sleep_hours=7.5, sleep_quality="good", energy_estimate="high",
            steps_today=3000, step_goal=10000, sedentary_minutes=sedentary,
        ),
    )


def test_prolonged_sitting_generates_walk():
    cands = generate_health_candidates(_ctx(120), datetime.now())
    walk = [c for c in cands if c.type == "walk"]
    assert walk, "expected a walk candidate when sedentary >= 90"
    assert "120 min" in walk[0].description
    assert "SEDENTARY_TOO_LONG" in walk[0].reason_codes


def test_not_sitting_long_uses_step_wording():
    cands = generate_health_candidates(_ctx(20), datetime.now())
    walk = [c for c in cands if c.type == "walk"]  # steps 3000 < 4000 goal → low-step walk
    if walk:
        assert "sitting" not in walk[0].description.lower()
