"""Past-feedback adjustments. Pure: takes a summary of accept/reject counts per action type (the
integration layer fetches it from the feedback repo) and tags candidates with feedback reason codes
so penalties/boosts apply. Returns candidates with updated reason_codes."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.recommendation.types import ActionType, CandidateAction

# Reactions needed before we scale user_preference_fit by the observed acceptance rate
# (mirrors the task-duration learning target so a couple of taps don't swing the signal).
PREFERENCE_MIN_SAMPLES = 5


@dataclass
class FeedbackSummary:
    rejects: dict[ActionType, int] = field(default_factory=dict)
    accepts: dict[ActionType, int] = field(default_factory=dict)
    recently_dismissed: set = field(default_factory=set)  # action types dismissed within cooldown
    avoided_now: set = field(default_factory=set)          # action types the user rejects at THIS time of day


def apply_feedback_adjustments(c: CandidateAction, summary: FeedbackSummary) -> CandidateAction:
    codes = list(c.reason_codes)
    if c.type in summary.recently_dismissed:
        codes.append("RECENTLY_DISMISSED_SIMILAR_ACTION")
    rej = summary.rejects.get(c.type, 0)
    acc = summary.accepts.get(c.type, 0)
    total = acc + rej
    # Continuous learned preference: once we've seen enough reactions, set user_preference_fit to the
    # observed acceptance rate (below the sample floor it stays at whatever the candidate set — 0.5
    # neutral). This is a smooth signal; the reject/accept reason codes below add the sharper nudges.
    if total >= PREFERENCE_MIN_SAMPLES:
        c.user_preference_fit = max(0.0, min(1.0, acc / total))
    if rej >= 3 and rej > acc:
        codes.append("USER_OFTEN_REJECTS_THIS_ACTION")
    elif acc >= 3 and acc > rej:
        codes.append("USER_OFTEN_ACCEPTS_THIS_ACTION")
    if c.type in summary.avoided_now:
        codes.append("AVOIDED_AT_THIS_TIME")
    c.reason_codes = codes
    return c
