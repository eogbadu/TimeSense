"""Deterministic recommendation text — used whenever the LLM is unavailable or fails. Built purely
from the already-selected recommendation, so it's instant and never wrong."""

from __future__ import annotations

from app.services.recommendation.types import LLMRecommendationText, Recommendation


def fallback_text(rec: Recommendation) -> LLMRecommendationText:
    body = rec.message or "A good use of this moment."
    # Enrich the body with a known travel time when we actually have one (never invented).
    if rec.travel_estimate is not None and rec.destination_place is not None:
        mins = int(round(rec.travel_estimate.duration_minutes))
        body = f"{rec.destination_place.name} is about {mins} min away. {body}"
    return LLMRecommendationText(
        notification_title=rec.title,
        notification_body=body,
        explanation=rec.explanation or body,
    )
