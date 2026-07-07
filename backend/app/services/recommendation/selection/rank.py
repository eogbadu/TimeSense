"""Rank scored candidates: highest score first, then confidence, then urgency. Deterministic."""

from __future__ import annotations

from app.services.recommendation.scoring.score import score_candidate
from app.services.recommendation.types import CandidateAction, ScoredCandidateAction, UserContext


def rank_candidates(candidates: list[CandidateAction], ctx: UserContext) -> list[ScoredCandidateAction]:
    scored = [score_candidate(c, ctx) for c in candidates]
    scored.sort(key=lambda s: (s.score, s.candidate.confidence, s.candidate.urgency), reverse=True)
    return scored
