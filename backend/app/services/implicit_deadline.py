"""
What time of day an implied deadline actually means (TIME-313).

People phrase deadlines the way they think about them — "today", "this evening", "next week" — and
every one of those carries an implied time that nothing in the pipeline was supplying. The parse
prompt told the model to "convert to absolute UTC" but never said WHAT TIME "today" is, so it
returned midnight. A task captured as "due today" was stored with a deadline of 00:00 *today*:
already past the moment it was created, immediately overdue, and demoted as stale by the next
morning (TIME-309).

Two rules settle it:

* A deadline that names a DAY means the END of that day. Not the end of the workday — the day. If
  someone says "today" at 9am they have until midnight, not until 5pm.
* A deadline that names a PART of a day means the end of that part.

The arithmetic lives here, deterministically, rather than in the prompt. Counting days is exactly
the kind of thing a language model gets subtly wrong and no one notices, and the phrase set is small
and closed. The model is still asked (it handles phrasings this doesn't), but where a phrase is
recognised here, this answer wins.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# The day ends at 23:59 local. Deliberately not the end of the working day, and deliberately not
# configurable: the day ends when the day ends, and a user who wants an earlier deadline can say so.
END_OF_DAY = time(23, 59)

# Ends of the named parts of a day. "Evening" ends at 21:00 rather than midnight because a task for
# "this evening" that is still open at 11:50pm has plainly been missed, and saying so is more useful
# than technically still counting it.
END_OF_MORNING = time(11, 59)
END_OF_AFTERNOON = time(17, 0)
END_OF_EVENING = time(21, 0)

# Weeks run Monday-Sunday (ISO). "End of next week" is therefore next Sunday night, which is the
# forgiving reading — it hands the user the whole weekend rather than cutting them off on Friday.
_WEEK_ENDS_ON = 6            # Monday=0 ... Sunday=6

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


@dataclass(frozen=True)
class ResolvedDeadline:
    """A deadline the resolver is confident about, and the phrase it came from.

    `phrase` exists so callers can say WHY they overrode the model, and so a mis-resolution is
    traceable to the words that caused it rather than being an unexplained datetime.
    """
    due_at_utc: datetime
    phrase: str


def _zone(tz_name: str | None):
    try:
        return ZoneInfo(tz_name) if tz_name else timezone.utc
    except Exception:
        return timezone.utc


def _at(day: date, when: time, tz) -> datetime:
    return datetime.combine(day, when).replace(tzinfo=tz).astimezone(timezone.utc)


def _end_of_week_containing(day: date) -> date:
    """The Sunday that closes the week `day` falls in."""
    return day + timedelta(days=(_WEEK_ENDS_ON - day.weekday()) % 7)


def _end_of_month(day: date) -> date:
    first_next = day.replace(day=28) + timedelta(days=4)
    return first_next.replace(day=1) - timedelta(days=1)


# Ordered longest/most specific first: "this evening" must not be read as bare "evening"-less
# "today", and "next week" must not be caught by "this week".
_RULES: list[tuple[str, str]] = [
    (r"\bthis\s+evening\b", "evening_today"),
    (r"\btonight\b", "evening_today"),
    (r"\bthis\s+afternoon\b", "afternoon_today"),
    (r"\bthis\s+morning\b", "morning_today"),
    (r"\btomorrow\s+(?:evening|night)\b", "evening_tomorrow"),
    (r"\btomorrow\s+afternoon\b", "afternoon_tomorrow"),
    (r"\btomorrow\s+morning\b", "morning_tomorrow"),
    (r"\bend\s+of\s+(?:the\s+)?month\b", "end_of_month"),
    (r"\bnext\s+month\b", "end_of_next_month"),
    (r"\bend\s+of\s+(?:the\s+)?(?:next|following)\s+week\b", "end_of_next_week"),
    (r"\b(?:by\s+)?(?:the\s+)?(?:next|following)\s+week\b", "end_of_next_week"),
    (r"\bend\s+of\s+(?:the\s+)?week\b", "end_of_this_week"),
    (r"\bthis\s+week\b", "end_of_this_week"),
    (r"\bend\s+of\s+(?:the\s+)?day\b", "end_of_today"),
    (r"\bby\s+end\s+of\s+day\b", "end_of_today"),
    (r"\beod\b", "end_of_today"),
    (r"\btomorrow\b", "end_of_tomorrow"),
    (r"\btoday\b", "end_of_today"),
]


def resolve(text: str, now: datetime, tz_name: str | None = "UTC") -> ResolvedDeadline | None:
    """The deadline a phrase implies, or None when the text contains no phrase we own.

    None means "no opinion" — the caller keeps whatever the model or the fallback parser produced.
    This never guesses; it only answers for phrases whose meaning is not in doubt.
    """
    if not text:
        return None
    tz = _zone(tz_name)
    today = now.astimezone(tz).date()
    lowered = text.lower()

    for pattern, kind in _RULES:
        match = re.search(pattern, lowered)
        if match:
            return ResolvedDeadline(_resolve_kind(kind, today, tz), match.group(0).strip())

    # A bare weekday ("by Friday") is the end of that day, next occurrence.
    for index, name in enumerate(_WEEKDAYS):
        if re.search(rf"\b{name}\b", lowered):
            ahead = (index - today.weekday()) % 7 or 7
            return ResolvedDeadline(_at(today + timedelta(days=ahead), END_OF_DAY, tz), name)

    return None


def _resolve_kind(kind: str, today: date, tz) -> datetime:
    tomorrow = today + timedelta(days=1)
    match kind:
        case "end_of_today":
            return _at(today, END_OF_DAY, tz)
        case "end_of_tomorrow":
            return _at(tomorrow, END_OF_DAY, tz)
        case "morning_today":
            return _at(today, END_OF_MORNING, tz)
        case "afternoon_today":
            return _at(today, END_OF_AFTERNOON, tz)
        case "evening_today":
            return _at(today, END_OF_EVENING, tz)
        case "morning_tomorrow":
            return _at(tomorrow, END_OF_MORNING, tz)
        case "afternoon_tomorrow":
            return _at(tomorrow, END_OF_AFTERNOON, tz)
        case "evening_tomorrow":
            return _at(tomorrow, END_OF_EVENING, tz)
        case "end_of_this_week":
            return _at(_end_of_week_containing(today), END_OF_DAY, tz)
        case "end_of_next_week":
            return _at(_end_of_week_containing(today) + timedelta(days=7), END_OF_DAY, tz)
        case "end_of_month":
            return _at(_end_of_month(today), END_OF_DAY, tz)
        case "end_of_next_month":
            first_next = _end_of_month(today) + timedelta(days=1)
            return _at(_end_of_month(first_next), END_OF_DAY, tz)
    return _at(today, END_OF_DAY, tz)


def repair_midnight(due_at: datetime | None, tz_name: str | None = "UTC") -> datetime | None:
    """Push a deadline sitting exactly on local midnight to the end of that day instead.

    A deadline of 00:00 is almost never what anyone means. It is what you get when a date with no
    time is turned into a datetime — the model does it, and so did the iOS picker, which stored a
    date-only deadline as `Calendar.startOfDay`. Both produce a task that is due at the very moment
    the day BEGINS, so it is overdue for the whole day it was meant to be done in.

    Applied where tasks are written rather than in capture alone, so every client gets it. The cost
    of being wrong is 24 hours of slack on a deadline someone genuinely set to midnight; the cost of
    not doing it is every date-only deadline being born overdue.
    """
    if due_at is None:
        return None
    tz = _zone(tz_name)
    local = (due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)).astimezone(tz)
    if (local.hour, local.minute) != (0, 0):
        return due_at
    return _at(local.date(), END_OF_DAY, tz)
