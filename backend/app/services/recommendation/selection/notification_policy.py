"""Push eligibility: only notify for a strong, confident recommendation (score >= 75 and
confidence >= 0.75). Cooldown/last-sent logic is applied at the integration layer."""

from __future__ import annotations

PUSH_SCORE_THRESHOLD = 75.0
PUSH_CONFIDENCE_THRESHOLD = 0.75


def eligible_for_push(score: float, confidence: float) -> bool:
    return score >= PUSH_SCORE_THRESHOLD and confidence >= PUSH_CONFIDENCE_THRESHOLD
