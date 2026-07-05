"""
Lightweight natural-language date/time extraction used as a fallback when the LLM is unavailable
(e.g. OpenAI quota/rate errors). Handles the common phrasings — "today", "tonight", "tomorrow",
weekday names, "Month Dayth", and "at 5pm" / "9:30am" — so captured tasks still get a due date and
can be prioritized, instead of every task tying with no deadline.

Returns (due_at_utc, cleaned_title). due_at is None when no date is found.
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"]
    )
}
_MONTH_ABBR = {m[:3]: n for m, n in _MONTHS.items()}

# Phrases we strip from the title once consumed as scheduling info.
_STRIP_PATTERNS = [
    r"\b(today|tonight|tomorrow)\b",
    r"\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\bat\s+\d{1,2}(:\d{2})?\s*(am|pm)\b",
    r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b",
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(st|nd|rd|th)?(,?\s*\d{4})?\b",
]


def _tz(name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def _extract_time(text: str) -> time | None:
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if not m:
        return None
    hour = int(m.group(1)) % 12
    if m.group(3) == "pm":
        hour += 12
    minute = int(m.group(2)) if m.group(2) else 0
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)


def _extract_date(text: str, now_local: datetime):
    """Return a local date (no time) from the text, or None."""
    if "today" in text or "tonight" in text:
        return now_local.date()
    if "tomorrow" in text:
        return (now_local + timedelta(days=1)).date()

    # "Month Dayth" e.g. "July 5th" / "jul 5" (assume this year, or next year if already past)
    m = re.search(r"\b([a-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?\b", text)
    if m:
        word = m.group(1)
        month = _MONTHS.get(word) or _MONTH_ABBR.get(word[:3])
        if month:
            day = int(m.group(2))
            try:
                candidate = now_local.replace(month=month, day=day).date()
                if candidate < now_local.date():
                    candidate = candidate.replace(year=candidate.year + 1)
                return candidate
            except ValueError:
                pass

    # Weekday name → next occurrence (not today)
    for i, wd in enumerate(_WEEKDAYS):
        if re.search(rf"\b{wd}\b", text):
            days_ahead = (i - now_local.weekday()) % 7 or 7
            return (now_local + timedelta(days=days_ahead)).date()
    return None


def _clean_title(raw: str) -> str:
    title = raw
    for pat in _STRIP_PATTERNS:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" ,.-").strip()
    if not title:
        title = raw.strip()
    return title[:1].upper() + title[1:] if title else raw


def parse_datetime(raw_input: str, user_timezone: str = "UTC") -> tuple[datetime | None, str]:
    tz = _tz(user_timezone)
    now_local = datetime.now(tz)
    text = raw_input.lower()

    due_date = _extract_date(text, now_local)
    if due_date is None:
        return None, _clean_title(raw_input)

    tod = _extract_time(text) or time(17, 0)  # default to 5pm local when only a date is given
    due_local = datetime.combine(due_date, tod).replace(tzinfo=tz)
    return due_local.astimezone(timezone.utc), _clean_title(raw_input)
