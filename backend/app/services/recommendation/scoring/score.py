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
