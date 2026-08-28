"""The four scoring factors that used to be constants.

Of the eight weighted factors in the engine, four were hard-coded IDENTICAL for every task
candidate: context_fit 0.6, routine_fit 0.4, user_preference_fit 0.5, and location_fit 0.5. Together
they carry 58% of the scoring weight, so 58% of every task's score was the same number and only
urgency, importance, time_fit and energy_fit could tell two tasks apart.

That is the largest single reason recommendations felt arbitrary, and it capped the benefit of every
other fix in this batch: a perfect duration estimate or energy model still only moved 42% of the
score.

Two rules run through all four:

  * Neutral (0.5) below a sample floor. A new user has no history, and inventing preferences from
    one or two data points is worse than admitting we don't know — the ranking then falls back to
    urgency and importance, which is the old behaviour and a reasonable default.
  * Every rule states a mechanism, not a correlation. "Errands are a poor fit while you're at home"
    is something we can explain to the user; "category 7 scores 0.31" is not.
"""
from __future__ import annotations

from app.services.recommendation.types import CandidateAction, TaskItem, UserContext

NEUTRAL = 0.5

# Categories that need sustained attention — the ones a bad moment genuinely ruins.
_FOCUS_CATEGORIES = frozenset({"writing", "engineering", "reading", "planning", "admin"})
# Categories that involve going somewhere or doing something physical.
_OUT_AND_ABOUT_CATEGORIES = frozenset({"errand", "shopping", "travel"})
# Things most naturally done at home.
_HOME_CATEGORIES = frozenset({"chore", "cooking"})

# A commitment this close means don't start anything substantial.
_IMMINENT_MINUTES = 30

# The adaptation profile keys weekdays by index (Monday = 0); the time snapshot carries a name.
_WEEKDAY_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def context_fit(task: TaskItem, category: str, ctx: UserContext) -> float:
    """Is this a sensible KIND of thing to do, right here, right now?

    Combines part of day, what sort of task it is, where the user is, and whether something is about
    to interrupt them. Was a flat 0.6 for every task.
    """
    part = ctx.time_context.part_of_day
    fit = NEUTRAL

    if category in _FOCUS_CATEGORIES:
        if part == "morning":
            fit += 0.20          # most people's best window for concentration
        elif part == "afternoon":
            fit += 0.05
        elif part == "evening":
            fit -= 0.15
        elif part == "night":
            fit -= 0.30

    if category in _OUT_AND_ABOUT_CATEGORIES and part == "night":
        fit -= 0.25              # don't send someone out late

    location = ctx.location_context
    if location is not None and location.location_category != "unknown":
        at_home = location.location_category == "home"
        if category in _OUT_AND_ABOUT_CATEGORIES:
            # The mechanism: you cannot run an errand from your sofa.
            fit += -0.20 if at_home else 0.20
        elif category in _HOME_CATEGORIES:
            fit += 0.15 if at_home else -0.20
        elif category in _FOCUS_CATEGORIES and location.location_category in ("office", "home"):
            fit += 0.10

    free = ctx.calendar_context.free_block_minutes
    if free is not None and free <= _IMMINENT_MINUTES:
        needed = task.estimated_minutes or 30
        if needed > free:
            fit -= 0.25          # about to be interrupted; don't start this

    return _clamp(fit)


def routine_fit(category: str, ctx: UserContext) -> float:
    """Does this person actually get things done at this hour, on this day?

    Sourced from the TIME-292 adaptation profile, which records completion rate by LOCAL hour and
    weekday. Stays neutral until there is enough evidence. Was a flat 0.4 for every task.
    """
    profile = ctx.adaptation
    if profile is None:
        return NEUTRAL

    signals = []
    by_hour = profile.get("completion_by_hour") or {}
    by_weekday = profile.get("completion_by_weekday") or {}

    hour = str(ctx.time_context.hour)
    if hour in by_hour:
        signals.append(by_hour[hour])

    weekday = _WEEKDAY_INDEX.get((ctx.time_context.day_of_week or "").strip().lower())
    if weekday is not None and str(weekday) in by_weekday:
        signals.append(by_weekday[str(weekday)])

    if not signals:
        return NEUTRAL
    # Pull toward the observed rate rather than adopting it outright: a completion rate is evidence
    # about this hour, not a verdict on this task.
    observed = sum(signals) / len(signals)
    return _clamp(NEUTRAL + (observed - NEUTRAL) * 0.8)


def user_preference_fit(category: str, action_type: str, ctx: UserContext) -> float:
    """How often does this person accept this KIND of suggestion?

    The pre-existing learning was keyed on action_type alone, which is far coarser than what a user
    actually rejects — "not this errand" and "not this deep work" are different statements about the
    same action type. Category is preferred when we have it, with action_type as the fallback.
    Was a flat 0.5 for every task.
    """
    profile = ctx.adaptation
    if profile is None:
        return NEUTRAL

    by_category = profile.get("acceptance_by_category") or {}
    if category in by_category:
        return _clamp(by_category[category])

    by_action = profile.get("acceptance_by_action_type") or {}
    if action_type in by_action:
        return _clamp(by_action[action_type])

    return NEUTRAL


def location_fit_for_task(category: str, ctx: UserContext) -> float:
    """Is where the user is a good place for this?

    Errand candidates get real travel feasibility from the location generator; this is the ordinary-
    task case, which was a flat 0.5 and therefore contributed the same +5 to everything. Neutral
    whenever we have no location signal, which is honest rather than pessimistic.
    """
    location = ctx.location_context
    if location is None or location.location_category == "unknown":
        return NEUTRAL

    category_of_place = location.location_category
    if category in _OUT_AND_ABOUT_CATEGORIES:
        # Already out: an errand is cheap now and expensive later.
        return 0.85 if category_of_place not in ("home",) else 0.25
    if category in _HOME_CATEGORIES:
        return 0.85 if category_of_place == "home" else 0.2
    if category in _FOCUS_CATEGORIES:
        return 0.8 if category_of_place in ("home", "office") else 0.35
    return NEUTRAL


def apply_fits(
    candidate: CandidateAction, task: TaskItem, category: str, ctx: UserContext
) -> CandidateAction:
    """Replace the four constants with real values. Kept in one place so the candidate builder
    doesn't grow four inline calculations."""
    candidate.context_fit = context_fit(task, category, ctx)
    candidate.routine_fit = routine_fit(category, ctx)
    candidate.user_preference_fit = user_preference_fit(category, candidate.type, ctx)
    candidate.location_fit = location_fit_for_task(category, ctx)
    return candidate
