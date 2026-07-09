"""Health/recovery candidates: recover after poor sleep, break, walk, hydrate, eat, wind down, sleep."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.types import CandidateAction, UserContext


def generate_health_candidates(ctx: UserContext, now: datetime) -> list[CandidateAction]:
    out: list[CandidateAction] = []
    h = ctx.health_context
    tod = ctx.time_context.part_of_day

    if h is not None:
        poor_sleep = h.sleep_quality == "poor" or (h.sleep_hours is not None and h.sleep_hours < 6)
        if poor_sleep:
            out.append(CandidateAction(
                id="health:recover", type="recover_after_poor_sleep", domain="health",
                title="Take it easy — you slept poorly",
                description="Start with something light and restorative.",
                estimated_minutes=20, urgency=0.55, importance=0.6, context_fit=0.8, time_fit=0.9,
                energy_fit=1.0, confidence=0.75, required_energy="low",
                reason_codes=["POOR_SLEEP", "RECOVERY_NEEDED"],
            ))
        if h.energy_estimate == "low":
            out.append(CandidateAction(
                id="health:break", type="take_break", domain="health",
                title="Take a short break", description="Your energy is low — reset for a few minutes.",
                estimated_minutes=10, urgency=0.4, importance=0.45, context_fit=0.7, time_fit=0.95,
                energy_fit=1.0, confidence=0.7, required_energy="low",
                reason_codes=["LOW_ENERGY"],
            ))
        sedentary = h.sedentary_minutes is not None and h.sedentary_minutes >= 90
        low_steps = (h.steps_today is not None and h.step_goal is not None
                     and h.steps_today < 0.4 * h.step_goal)
        if sedentary or low_steps:
            if sedentary:
                desc = f"You've been sitting for {h.sedentary_minutes} min — a short walk will reset your focus."
            else:
                desc = "You're well under your step goal — get moving."
            # Sitting longer → nudge a little harder.
            urgency = 0.45 + min(0.25, (h.sedentary_minutes - 90) / 400) if sedentary else 0.4
            out.append(CandidateAction(
                id="health:walk", type="walk", domain="health",
                title="Go for a short walk", description=desc,
                estimated_minutes=15, urgency=round(urgency, 2), importance=0.5, context_fit=0.78,
                time_fit=0.9, energy_fit=0.85, confidence=0.72, required_energy="low",
                reason_codes=["SEDENTARY_TOO_LONG"] if sedentary else ["LOW_STEP_COUNT"],
            ))

    if tod == "night":
        out.append(CandidateAction(
            id="health:winddown", type="wind_down", domain="health",
            title="Start winding down", description="It's late — ease toward rest.",
            estimated_minutes=20, urgency=0.5, importance=0.55, context_fit=0.85, time_fit=0.9,
            energy_fit=1.0, routine_fit=0.7, confidence=0.75, required_energy="low",
            reason_codes=["EVENING_ROUTINE_WINDOW"],
        ))
    return out
