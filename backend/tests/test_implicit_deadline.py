"""TIME-313 — an implied deadline has an implied TIME, and nothing was supplying it.

The parse prompt told the model to "convert to absolute UTC" but never said what time of day "today"
means, so it returned midnight. A task captured as "due today" was stored with a deadline of 00:00
TODAY: already past the moment it was created, and demoted as stale by the next morning (TIME-309).
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.implicit_deadline import repair_midnight, resolve

NY = "America/New_York"
TOKYO = "Asia/Tokyo"


def _local(dt: datetime, tz: str = NY):
    return dt.astimezone(ZoneInfo(tz))


# 2026-08-30 is a Sunday; 09:00 New York.
NOW = datetime(2026, 8, 30, 9, 0, tzinfo=ZoneInfo(NY)).astimezone(timezone.utc)


def _resolved(text: str, now: datetime = NOW, tz: str = NY):
    r = resolve(text, now, tz)
    assert r is not None, f"no deadline resolved from {text!r}"
    return _local(r.due_at_utc, tz)


# --- the day ends at the end of the day ------------------------------------------------------------

def test_today_means_the_end_of_today_not_midnight():
    """The reported requirement, and the bug: 'today' was becoming 00:00 today."""
    due = _resolved("Finish the report today")
    assert (due.year, due.month, due.day) == (2026, 8, 30)
    assert (due.hour, due.minute) == (23, 59)


def test_a_task_due_today_is_not_born_overdue():
    """The consequence that made this visible. Captured at 9am, due today, must still be ahead."""
    assert resolve("Finish the report today", NOW, NY).due_at_utc > NOW


def test_today_means_the_end_of_the_DAY_not_the_workday():
    """Explicitly not 17:00 or the configured work_end_hour — the day, as the user put it."""
    due = _resolved("email the client by end of day")
    assert due.hour == 23


def test_eod_and_end_of_day_agree_with_today():
    assert _resolved("ship it EOD") == _resolved("ship it today")
    assert _resolved("ship it by end of day") == _resolved("ship it today")


def test_tomorrow_means_the_end_of_tomorrow():
    due = _resolved("send the invoice tomorrow")
    assert (due.month, due.day) == (8, 31)
    assert (due.hour, due.minute) == (23, 59)


# --- parts of a day ---------------------------------------------------------------------------------

def test_this_evening_is_the_same_day_in_the_evening():
    due = _resolved("Call mum this evening")
    assert (due.month, due.day) == (8, 30)
    assert due.hour == 21


def test_tonight_is_the_same_as_this_evening():
    assert _resolved("call mum tonight") == _resolved("call mum this evening")


def test_this_morning_and_this_afternoon():
    assert _resolved("reply to Sam this morning").hour == 11
    assert _resolved("reply to Sam this afternoon").hour == 17


def test_tomorrow_evening_combines_both():
    due = _resolved("dinner prep tomorrow evening")
    assert (due.month, due.day, due.hour) == (8, 31, 21)


def test_this_evening_is_not_swallowed_by_the_bare_today_rule():
    """Ordering matters: a rule list that checked 'today' first would make every part-of-day 23:59."""
    assert _resolved("this evening").hour == 21
    assert _resolved("this afternoon").hour == 17


# --- weeks -------------------------------------------------------------------------------------------

def test_next_week_is_the_end_of_next_week():
    # NOW is Sunday 2026-08-30, which closes the current ISO week; next week ends Sunday 09-06.
    due = _resolved("Submit expenses next week")
    assert (due.month, due.day) == (9, 6)
    assert (due.hour, due.minute) == (23, 59)


def test_this_week_and_next_week_are_a_week_apart():
    this_week = _resolved("wrap this up this week")
    next_week = _resolved("wrap this up next week")
    assert (next_week - this_week).days == 7


def test_next_week_is_not_matched_by_the_this_week_rule():
    assert _resolved("next week") != _resolved("this week")


def test_end_of_next_week_is_the_same_as_next_week():
    assert _resolved("due by end of next week") == _resolved("due next week")


def test_from_midweek_this_week_still_ends_on_sunday():
    wednesday = datetime(2026, 9, 2, 10, 0, tzinfo=ZoneInfo(NY)).astimezone(timezone.utc)
    due = _resolved("finish this week", now=wednesday)
    assert due.weekday() == 6                    # Sunday
    assert (due.month, due.day) == (9, 6)


def test_a_bare_weekday_is_the_end_of_that_day_next_occurrence():
    due = _resolved("file taxes by Friday")
    assert (due.month, due.day) == (9, 4)
    assert (due.hour, due.minute) == (23, 59)


def test_end_of_month():
    due = _resolved("close the books by end of the month")
    assert (due.month, due.day) == (8, 31)


# --- restraint ----------------------------------------------------------------------------------------

def test_no_opinion_when_no_phrase_is_recognised():
    """None means 'keep whatever the model produced' — this must never guess."""
    assert resolve("Solve 10 Leetcode problems", NOW, NY) is None
    assert resolve("", NOW, NY) is None
    assert resolve(None, NOW, NY) is None


def test_the_matched_phrase_is_reported():
    """So an override is traceable to the words that caused it, not an unexplained datetime."""
    assert resolve("Call mum this evening", NOW, NY).phrase == "this evening"


# --- timezone -----------------------------------------------------------------------------------------

def test_resolution_happens_in_the_users_timezone():
    """'today' in Tokyo is a different 24 hours than 'today' in New York — this is the failure the
    user hit travelling to Japan (TIME-283)."""
    ny = _resolved("today", tz=NY)
    tokyo = _resolved("today", tz=TOKYO)
    assert (ny.hour, ny.minute) == (23, 59)
    assert (tokyo.hour, tokyo.minute) == (23, 59)
    assert resolve("today", NOW, NY).due_at_utc != resolve("today", NOW, TOKYO).due_at_utc


def test_an_unknown_timezone_falls_back_rather_than_raising():
    assert resolve("today", NOW, "Not/AZone") is not None


# --- the midnight repair --------------------------------------------------------------------------------

def test_local_midnight_is_pushed_to_the_end_of_that_day():
    """What the iOS picker produced via Calendar.startOfDay, and what the model returns unprompted."""
    midnight = datetime(2026, 8, 30, 0, 0, tzinfo=ZoneInfo(NY)).astimezone(timezone.utc)
    repaired = _local(repair_midnight(midnight, NY))
    assert (repaired.month, repaired.day) == (8, 30)      # same day, not the next
    assert (repaired.hour, repaired.minute) == (23, 59)


def test_a_real_time_is_left_alone():
    real = datetime(2026, 8, 30, 14, 30, tzinfo=ZoneInfo(NY)).astimezone(timezone.utc)
    assert repair_midnight(real, NY) == real


def test_midnight_is_judged_locally_not_in_utc():
    """04:00 UTC is midnight in New York and must be repaired; it is 13:00 in Tokyo and must not."""
    utc_4am = datetime(2026, 8, 30, 4, 0, tzinfo=timezone.utc)
    assert repair_midnight(utc_4am, NY) != utc_4am
    assert repair_midnight(utc_4am, TOKYO) == utc_4am


def test_none_stays_none():
    assert repair_midnight(None, NY) is None


def test_a_naive_datetime_is_treated_as_utc():
    assert repair_midnight(datetime(2026, 8, 30, 4, 0), NY) is not None
