"""Past-feedback adjustments. Pure: takes a summary of accept/reject counts per action type (the
integration layer fetches it from the feedback repo) and tags candidates with feedback reason codes
so penalties/boosts apply. Returns candidates with updated reason_codes."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.recommendation.types import ActionType, CandidateAction


@dataclass
class FeedbackSummary:
    rejects: dict[ActionType, int] = field(default_factory=dict)
    accepts: dict[ActionType, int] = field(default_factory=dict)
    recently_dismissed: set = field(default_factory=set)  # action types dismissed within cooldown


def apply_feedback_adjustments(c: CandidateAction, summary: FeedbackSummary) -> CandidateAction:
    codes = list(c.reason_codes)
    if c.type in summary.recently_dismissed:
        codes.append("RECENTLY_DISMISSED_SIMILAR_ACTION")
    rej = summary.rejects.get(c.type, 0)
    acc = summary.accepts.get(c.type, 0)
    if rej >= 3 and rej > acc:
        codes.append("USER_OFTEN_REJECTS_THIS_ACTION")
    elif acc >= 3 and acc > rej:
        codes.append("USER_OFTEN_ACCEPTS_THIS_ACTION")
        c.user_preference_fit = min(1.0, c.user_preference_fit + 0.2)
    c.reason_codes = codes
    return c
