"""Turn an already-selected recommendation into friendly, human text using the LLM.

The LLM is ONLY a writer here — it receives the decision + the exact facts and rewrites them. It
cannot change the action (this function returns text fields only; the caller keeps the recommendation)
and it must not invent distances, travel times, open/closed status, calendar conflicts, or
preferences. Any failure (exception, empty, unparseable) falls back to deterministic text."""

from __future__ import annotations

import json

from app.llm.gateway import LLMGateway
from app.services.recommendation.llm.fallback_recommendation_text import fallback_text
from app.services.recommendation.types import (
    LLMRecommendationText,
    Recommendation,
    UserContext,
)

_SYSTEM = (
    "You are the writing layer of a personal time assistant. A deterministic engine has ALREADY "
    "chosen the single best action for the user. Your ONLY job is to phrase it warmly and clearly. "
    "Hard rules: (1) never suggest a different action; (2) never invent distances, travel times, "
    "open/closed status, calendar conflicts, deadlines, or preferences — use ONLY the facts given; "
    "(3) keep it short. Return STRICT JSON with exactly these keys: "
    '{"notification_title": string (<= 6 words), "notification_body": string (<= 24 words), '
    '"explanation": string (<= 40 words)}. No markdown, no extra keys.'
)


def _context_facts(rec: Recommendation, ctx: UserContext) -> str:
    lines = [
        f"Action (fixed): {rec.action_type}",
        f"Title: {rec.title}",
        f"Reason codes: {', '.join(rec.reason_codes) or 'none'}",
        f"Time of day: {ctx.time_context.part_of_day}",
        f"Tone: {ctx.user_preferences.preferred_tone}",
    ]
    if ctx.calendar_context.free_block_minutes is not None:
        lines.append(f"Free block: {ctx.calendar_context.free_block_minutes} min")
    if ctx.location_context is not None and ctx.location_context.place_name:
        lines.append(f"Current place: {ctx.location_context.place_name}")
    if rec.destination_place is not None:
        lines.append(f"Destination: {rec.destination_place.name}")
    if rec.travel_estimate is not None:
        lines.append(
            f"Travel time (known): {int(round(rec.travel_estimate.duration_minutes))} min "
            f"({rec.travel_estimate.distance_miles} mi)"
        )
    return "\n".join(lines)


def _parse(raw: str) -> LLMRecommendationText | None:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
        title = str(data["notification_title"]).strip()
        body = str(data["notification_body"]).strip()
        explanation = str(data["explanation"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    if not (title and body and explanation):
        return None
    return LLMRecommendationText(
        notification_title=title, notification_body=body, explanation=explanation
    )


async def generate_recommendation_text(
    rec: Recommendation, ctx: UserContext, gateway: LLMGateway
) -> LLMRecommendationText:
    try:
        prompt = (
            "Rewrite this pre-selected recommendation as friendly text.\n\n"
            f"{_context_facts(rec, ctx)}\n\n"
            "Return the JSON described in the system prompt."
        )
        raw = await gateway.complete_simple(prompt, system=_SYSTEM, max_tokens=200)
        parsed = _parse(raw or "")
        return parsed if parsed is not None else fallback_text(rec)
    except Exception:
        return fallback_text(rec)
