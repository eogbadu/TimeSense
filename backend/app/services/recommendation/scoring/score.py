"""Deterministic scoring — the weighted sum from the spec, minus penalties, clamped to 0..100."""

from __future__ import annotations

from app.services.recommendation.scoring.penalties import compute_penalty
from app.services.recommendation.types import CandidateAction, ScoredCandidateAction, UserContext

WEIGHTS = {
    "urgency": 0.20, "importance": 0.20, "context_fit": 0.15, "time_fit": 0.12,
    "energy_fit": 0.10, "location_fit": 0.10, "routine_fit": 0.08, "user_preference_fit": 0.05,
}


def base_score(c: CandidateAction) -> float:
    return 100.0 * (
        WEIGHTS["urgency"] * c.urgency
        + WEIGHTS["importance"] * c.importance
        + WEIGHTS["context_fit"] * c.context_fit
        + WEIGHTS["time_fit"] * c.time_fit
        + WEIGHTS["energy_fit"] * c.energy_fit
        + WEIGHTS["location_fit"] * c.location_fit
        + WEIGHTS["routine_fit"] * c.routine_fit
        + WEIGHTS["user_preference_fit"] * c.user_preference_fit
    )


def score_candidate(c: CandidateAction, ctx: UserContext) -> ScoredCandidateAction:
    penalty = compute_penalty(c, ctx)
    score = max(0.0, min(100.0, base_score(c) - penalty))
    return ScoredCandidateAction(candidate=c, score=score, penalty_score=penalty)


def score_to_confidence(score: float) -> float:
    """The single source of truth for the confidence shown on a recommendation: it just reflects how
    strong the winning pick's 0–100 score is. Cap at 0.95 (never claim near-certainty); gentle 0.30
    floor so a weak 'nothing pressing' pick doesn't read as broken. Both bounds are tunable.

    Note score_to_confidence(75) == 0.75 == PUSH_CONFIDENCE_THRESHOLD, so eligible_for_push (score>=75
    AND confidence>=0.75) stays equivalent to score>=75 — push behaviour is unchanged, just consistent.
    """
    return round(min(0.95, max(0.30, score / 100.0)), 2)
