"""Calendar/schedule candidates: prepare/join a meeting, leave for an event with a location, protect
a focus block, and review upcoming day/tomorrow."""

from __future__ import annotations

from datetime import datetime

from app.services.recommendation.types import CandidateAction, UserContext


def generate_calendar_candidates(ctx: UserContext, now: datetime) -> list[CandidateAction]:
    out: list[CandidateAction] = []
    cal = ctx.calendar_context
    nxt = cal.next_event
    mins = cal.minutes_until_next_event

    located = bool(nxt.location) if nxt is not None else False
    if nxt is not None and mins is not None and mins >= 0:
        if mins <= 2:
            out.append(CandidateAction(
                id=f"cal:join:{nxt.id}", type="join_meeting", domain="calendar",
                title=f"Join “{nxt.title}”", description="Your meeting is starting now.",
                estimated_minutes=30, urgency=1.0, importance=0.85, context_fit=0.95,
                time_fit=1.0, energy_fit=0.8, confidence=0.9, interruption_level="high",
                reason_codes=["MEETING_STARTING_NOW"], related_entity_ids=[nxt.id],
            ))
        elif mins <= 20 or (located and mins <= 30):
            # Prep now (or head out for a nearby event).
            leaving = located and mins <= 30
            out.append(CandidateAction(
                id=f"cal:prep:{nxt.id}",
                type="leave_for_event" if leaving else "prepare_for_meeting",
                domain="calendar",
                title=(f"Leave for “{nxt.title}”" if leaving else f"Prep for “{nxt.title}”"),
                description=(f"It's at {nxt.location}." if leaving else f"Starts in {mins} min — get ready."),
                estimated_minutes=min(mins, 20), urgency=0.9, importance=0.85, context_fit=0.9,
                time_fit=1.0, energy_fit=0.8, location_fit=0.7 if leaving else 0.5,
                confidence=0.85, interruption_level="medium", requires_location=leaving,
                reason_codes=(["EVENT_HAS_LOCATION", "TRAVEL_TIME_REQUIRED"] if leaving else ["NEXT_MEETING_SOON"]),
                related_entity_ids=[nxt.id],
            ))
        elif mins <= (60 if located else 75):
            # Coming up within the hour — surface it as the salient next thing so it isn't buried
            # under routine tasks (and located events need lead time to travel).
            out.append(CandidateAction(
                id=f"cal:next:{nxt.id}",
                type="leave_for_event" if located else "prepare_for_meeting",
                domain="calendar",
                title=(f"Head out soon for “{nxt.title}”" if located else f"Coming up: “{nxt.title}”"),
                description=(f"In {mins} min at {nxt.location}." if located else f"In {mins} min."),
                estimated_minutes=min(mins, 30),
                urgency=round(max(0.6, 1.0 - mins / 90.0), 2),
                importance=0.85, context_fit=0.9, time_fit=1.0, energy_fit=0.8,
                location_fit=0.7 if located else 0.5, confidence=0.75, interruption_level="medium",
                requires_location=located,
                reason_codes=(["EVENT_HAS_LOCATION", "TRAVEL_TIME_REQUIRED"] if located else ["NEXT_MEETING_SOON"]),
                related_entity_ids=[nxt.id],
            ))

    # Long free block + high-priority work → protect a focus block.
    free = cal.free_block_minutes or 0
    if free >= 60 and ctx.task_context.high_priority_tasks:
        out.append(CandidateAction(
            id="cal:focus", type="protect_focus_block", domain="calendar",
            title="Protect a focus block", description=f"You have {free} min free — guard it for deep work.",
            estimated_minutes=min(free, 90), urgency=0.5, importance=0.7, context_fit=0.75,
            time_fit=0.9, energy_fit=0.8, confidence=0.7,
            reason_codes=["LONG_FREE_BLOCK", "HIGH_PRIORITY_TASK"],
        ))

    tod = ctx.time_context.part_of_day
    if tod in ("early_morning", "morning") and (nxt is not None or ctx.task_context.due_today_tasks):
        out.append(CandidateAction(
            id="cal:review_day", type="review_upcoming_day", domain="calendar",
            title="Review your day", description="Skim what's ahead before diving in.",
            estimated_minutes=10, urgency=0.4, importance=0.5, context_fit=0.7, time_fit=0.9,
            energy_fit=0.9, routine_fit=0.6, confidence=0.7,
            reason_codes=["MORNING_PLANNING_WINDOW"],
        ))
    return out
