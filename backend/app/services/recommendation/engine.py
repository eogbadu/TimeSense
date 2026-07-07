"""Deterministic engine orchestrator: normalize context is done by the caller; here we generate →
(feedback-adjust) → score → rank → select. The LLM is never consulted for the decision."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.recommendation.candidates.generate import generate_candidate_actions
from app.services.recommendation.feedback.apply_feedback import (
    FeedbackSummary,
    apply_feedback_adjustments,
)
from app.services.recommendation.maps.maps_skill_service import MapsSkillService
from app.services.recommendation.selection.rank import rank_candidates
from app.services.recommendation.selection.select import select_recommendation
from app.services.recommendation.types import Recommendation, ScoredCandidateAction, UserContext


async def run_engine(
    ctx: UserContext,
    maps: MapsSkillService | None = None,
    now: datetime | None = None,
    feedback: FeedbackSummary | None = None,
) -> Recommendation:
    now = now or datetime.now(timezone.utc)
    maps = maps or MapsSkillService()

    candidates = await generate_candidate_actions(ctx, maps, now)
    if feedback is not None:
        candidates = [apply_feedback_adjustments(c, feedback) for c in candidates]

    ranked: list[ScoredCandidateAction] = rank_candidates(candidates, ctx)
    return select_recommendation(ranked, ctx, now)
