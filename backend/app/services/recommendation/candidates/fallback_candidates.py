"""Always-present low-scoring fallbacks so selection never returns empty."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.types import CandidateAction, UserContext


def generate_fallback_candidates(ctx: UserContext, now: datetime) -> list[CandidateAction]:
    return [
        CandidateAction(
            id="fallback:continue", type="continue_current_activity", domain="fallback",
            title="Keep going", description="Nothing urgent — carry on with what you're doing.",
            estimated_minutes=15, urgency=0.15, importance=0.2, context_fit=0.4, time_fit=0.6,
            energy_fit=0.6, confidence=0.5, reason_codes=["NO_URGENT_ACTION"],
        ),
        CandidateAction(
            id="fallback:none", type="no_urgent_action", domain="fallback",
            title="Nothing pressing right now", description="You're on top of things.",
            estimated_minutes=0, urgency=0.1, importance=0.15, context_fit=0.4, time_fit=0.6,
            energy_fit=0.6, confidence=0.5, reason_codes=["NO_URGENT_ACTION", "LOW_CONFIDENCE_CONTEXT"],
        ),
    ]
