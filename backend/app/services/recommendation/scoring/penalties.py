"""Hard-rule penalties (0..100) subtracted from a candidate's base score. This is where the spec's
"do not recommend X in situation Y" rules live, so scoring stays a simple weighted sum."""

from __future__ import annotations

from app.services.recommendation.types import CandidateAction, UserContext

_DEEP = {"deep_work", "protect_focus_block"}
_WORKISH = {"deep_work", "admin_task", "notion_task", "quick_task", "batch_small_tasks",
            "follow_up_task", "deadline_task"}


def compute_penalty(c: CandidateAction, ctx: UserContext) -> float:
    penalty = 0.0
    codes = set(c.reason_codes)
    cal = ctx.calendar_context
    tod = ctx.time_context.part_of_day
    overdue = "TASK_OVERDUE" in codes

    # Meeting imminent → suppress deep work and errands (only prep/join/leave should win).
    mins = cal.minutes_until_next_event
    if mins is not None and mins <= 15:
        if c.type in _DEEP:
            penalty += 60
        if c.domain == "location":
            penalty += 55
        if c.domain == "task" and c.estimated_minutes > mins:
            penalty += 40

    # Short free block → no deep work.
    free = cal.free_block_minutes
    if free is not None and free < 25 and c.type in _DEEP:
        penalty += 45

    # Poor sleep / low energy → reduce demanding work unless there's a hard deadline today.
    h = ctx.health_context
    if h is not None and not cal.has_hard_deadline_today:
        poor = h.sleep_quality == "poor" or (h.sleep_hours is not None and h.sleep_hours < 6)
        low = h.energy_estimate == "low"
        if (poor or low) and (c.type in _DEEP or c.required_energy == "high"):
            penalty += 30

    # Night → suppress errands and normal work unless it's urgent (overdue, or due very soon so
    # urgency is high). We still don't send the user out on an errand at night unless it's overdue.
    if tod == "night":
        urgent = overdue or c.urgency >= 0.8
        if c.domain == "location" and not overdue:
            penalty += 55
        if c.type in _WORKISH and not urgent:
            penalty += 40

    # Don't start an errand/trip right before a calendar commitment — you'd be cutting it close or
    # arrive late, and prepping/heading to the commitment matters more than the errand.
    if (c.domain == "location" and cal.next_event is not None
            and cal.minutes_until_next_event is not None and cal.minutes_until_next_event <= 60):
        penalty += 40

    # A generic context-switch nudge (into work / home / sleep) must not override an imminent
    # calendar commitment — the appointment is the salient next thing, not "move toward sleep".
    if (c.domain == "context_switch" and cal.next_event is not None
            and cal.minutes_until_next_event is not None and 0 <= cal.minutes_until_next_event <= 60):
        penalty += 40

    # At home, an errand is only doable if we've confirmed a feasible trip — otherwise it must not
    # lead (you'd have to leave, and we can't verify it fits). Restores the TIME-110 guarantee.
    loc = ctx.location_context
    if (c.domain == "location" and loc is not None and loc.location_category == "home"
            and "TRIP_FITS_FREE_BLOCK" not in codes):
        penalty += 60

    # Location feasibility / availability.
    if "TRIP_DOES_NOT_FIT_FREE_BLOCK" in codes:
        penalty += 70
    if "PLACE_CLOSED_NOW" in codes:
        penalty += 40
    if "LOCATION_DATA_MISSING" in codes or "MAPS_API_UNAVAILABLE" in codes:
        penalty += 20  # can't confirm a real trip → don't let it win confidently

    # Recently 'disagreed' with this exact task → demote it (don't hide): enough to drop below
    # other candidates so a different recommendation surfaces, but it stays rankable and reappears.
    if "RECENTLY_DISAGREED" in codes:
        penalty += 30

    # Feedback: user often rejects this action type.
    if "USER_OFTEN_REJECTS_THIS_ACTION" in codes:
        penalty += 25
    # Feedback: user often accepts this action type → a bounded boost (negative penalty) so it edges
    # ahead of comparable candidates. Bounded (base is 0..100) so hard safety rules still dominate.
    if "USER_OFTEN_ACCEPTS_THIS_ACTION" in codes:
        penalty -= 15
    if "RECENTLY_DISMISSED_SIMILAR_ACTION" in codes:
        penalty += 35

    return penalty
