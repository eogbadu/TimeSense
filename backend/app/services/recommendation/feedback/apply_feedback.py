"""Past-feedback adjustments. Pure: takes a summary of accept/reject counts per action type (the
integration layer fetches it from the feedback repo) and tags candidates with feedback reason codes
so penalties/boosts apply. Returns candidates with updated reason_codes."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.recommendation.types import ActionType, CandidateAction

# Reactions needed before we scale user_preference_fit by the observed acceptance rate
# (mirrors the task-duration learning target so a couple of taps don't swing the signal).
PREFERENCE_MIN_SAMPLES = 5


# Swaps needed before a pairing counts as a preference rather than a one-off.
SWAP_MIN_SAMPLES = 2
# Reason-tagged disagreements needed before that reason shapes scoring.
REASON_MIN_SAMPLES = 2


@dataclass
class FeedbackSummary:
    rejects: dict[ActionType, int] = field(default_factory=dict)
    accepts: dict[ActionType, int] = field(default_factory=dict)
    recently_dismissed: set = field(default_factory=set)  # action types dismissed within cooldown
    avoided_now: set = field(default_factory=set)          # action types the user rejects at THIS time of day

    # --- swap-derived signals (TIME-296) -----------------------------------------------------
    # A swap is a PAIRED preference: not just "no" but "this instead", at a known time of day.
    # Task-library categories the user has repeatedly chosen at this part of day...
    preferred_categories_now: set = field(default_factory=set)
    # ...and ones they have repeatedly swapped AWAY from at this part of day.
    swapped_away_categories_now: set = field(default_factory=set)

    # --- reason-derived signals (TIME-296) ---------------------------------------------------
    # Until now the disagree reason was read in exactly ONE place — to choose between a 3-hour and a
    # 24-hour demote window. These give each reason a distinct, testable effect.
    wrong_time_categories_now: set = field(default_factory=set)   # "wrong time", at this time of day
    too_big_categories: set = field(default_factory=set)          # "too big" — applies when depleted
    not_priority_categories: set = field(default_factory=set)     # "not a priority"


def apply_feedback_adjustments(c: CandidateAction, summary: FeedbackSummary) -> CandidateAction:
    codes = list(c.reason_codes)
    if c.type in summary.recently_dismissed:
        codes.append("RECENTLY_DISMISSED_SIMILAR_ACTION")
    rej = summary.rejects.get(c.type, 0)
    acc = summary.accepts.get(c.type, 0)
    total = acc + rej
    # Continuous learned preference from action-type history. This used to REPLACE
    # user_preference_fit outright, which since TIME-293 would discard the finer per-category value
    # the candidate already carries. Averaging keeps both signals: the category fit says what kind of
    # work the user accepts, this says how they react to this shape of suggestion.
    if total >= PREFERENCE_MIN_SAMPLES:
        observed = max(0.0, min(1.0, acc / total))
        c.user_preference_fit = (c.user_preference_fit + observed) / 2
    if rej >= 3 and rej > acc:
        codes.append("USER_OFTEN_REJECTS_THIS_ACTION")
    elif acc >= 3 and acc > rej:
        codes.append("USER_OFTEN_ACCEPTS_THIS_ACTION")
    if c.type in summary.avoided_now:
        codes.append("AVOIDED_AT_THIS_TIME")

    # --- swap + reason signals (TIME-296) ----------------------------------------------------
    category = c.task_category
    if category:
        if category in summary.preferred_categories_now:
            codes.append("USER_PREFERS_THIS_TYPE_NOW")
        if category in summary.swapped_away_categories_now:
            codes.append("USER_SWAPS_AWAY_FROM_THIS_NOW")
        if category in summary.wrong_time_categories_now:
            codes.append("WRONG_TIME_FOR_THIS_CATEGORY")
        if category in summary.too_big_categories:
            codes.append("TOO_BIG_WHEN_DEPLETED")
        if category in summary.not_priority_categories:
            codes.append("USER_SAYS_NOT_A_PRIORITY")

    c.reason_codes = codes
    return c
