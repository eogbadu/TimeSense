"""Local-day boundaries for a user's stored timezone.

The server clock is always UTC, but almost every product question — "what's on today", "did they
skip lunch", "is it 8am for them" — is asked in the user's LOCAL day. Before TIME-283 several read
paths answered those questions with UTC day bounds, which is silently correct only for users near
UTC and wrong by up to a full day elsewhere.

These helpers exist so that conversion is written once. They deliberately mirror the idiom already
used correctly in api/v1/now.py and api/v1/activity.py: resolve the zone, fall back to UTC if the
stored identifier is unusable, and never raise on a bad value.

Nothing here is region-specific — any IANA zone works, including half-hour and 45-minute offsets
(Asia/Kolkata, Asia/Kathmandu) and zones on the far side of the date line.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def resolve_zone(user_timezone: str | None) -> ZoneInfo | timezone:
    """The user's zone, or UTC when it's missing/unknown. Never raises."""
    if not user_timezone:
        return timezone.utc
    try:
        return ZoneInfo(user_timezone)
    except Exception:
        return timezone.utc


def local_today(user_timezone: str | None, now: datetime | None = None) -> date:
    """The calendar date it currently is where the user is."""
    moment = now or datetime.now(timezone.utc)
    return moment.astimezone(resolve_zone(user_timezone)).date()


def local_day_bounds(
    for_date: date, user_timezone: str | None
) -> tuple[datetime, datetime]:
    """The UTC instants bracketing `for_date` in the user's zone, as [start, end).

    Returned tz-aware and half-open, so a query can use `>= start` and `< end` without the
    23:59:59 fencepost the old UTC-based code used (which silently dropped anything in the final
    second of the day).
    """
    zone = resolve_zone(user_timezone)
    start = datetime.combine(for_date, datetime.min.time(), tzinfo=zone)
    # Add a day on the calendar, not 24h, so DST transition days stay whole.
    end = datetime.combine(for_date + timedelta(days=1), datetime.min.time(), tzinfo=zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def local_hour(user_timezone: str | None, now: datetime | None = None) -> int:
    """The current hour (0-23) where the user is — for 'is it 8am for them?' scheduling checks."""
    moment = now or datetime.now(timezone.utc)
    return moment.astimezone(resolve_zone(user_timezone)).hour


def user_timezone_of(user) -> str:
    """The stored profile timezone for a User, defaulting to UTC. Mirrors the idiom repeated across
    the API layer (`user.profile.timezone if user.profile else "UTC"`)."""
    profile = getattr(user, "profile", None)
    return (getattr(profile, "timezone", None) or "UTC") if profile is not None else "UTC"
