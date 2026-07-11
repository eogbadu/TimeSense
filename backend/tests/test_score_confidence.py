"""TIME-213 — confidence is derived from the engine score (single source of truth)."""

from app.services.recommendation.scoring.score import score_to_confidence


def test_score_maps_linearly_to_confidence():
    assert score_to_confidence(82) == 0.82   # strong pick reads high
    assert score_to_confidence(40) == 0.40   # weak "nothing pressing" pick reads low


def test_confidence_is_floored_and_capped():
    assert score_to_confidence(10) == 0.30   # gentle floor — never looks broken
    assert score_to_confidence(0) == 0.30
    assert score_to_confidence(98) == 0.95   # cap — never claim near-certainty
    assert score_to_confidence(100) == 0.95


def test_push_threshold_stays_consistent():
    # score_to_confidence(75) == PUSH_CONFIDENCE_THRESHOLD, so eligible_for_push stays equivalent
    # to score >= 75 (no behaviour change from the switch).
    from app.services.recommendation.selection.notification_policy import (
        PUSH_CONFIDENCE_THRESHOLD,
        eligible_for_push,
    )

    assert score_to_confidence(75) == PUSH_CONFIDENCE_THRESHOLD
    assert eligible_for_push(75.0, score_to_confidence(75.0)) is True
    assert eligible_for_push(74.0, score_to_confidence(74.0)) is False
