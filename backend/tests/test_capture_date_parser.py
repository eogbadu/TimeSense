"""Tests for the rule-based capture date parser (TIME-072, TIME-140).

parse_datetime returns (scheduled_start_utc, due_at_utc, cleaned_title): a specific clock time →
scheduled_start; a date without a time → due_at.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services.capture_date_parser import parse_datetime

TZ = "America/New_York"


def _local_today(tz=TZ):
    return datetime.now(ZoneInfo(tz)).date()


def test_date_only_becomes_due_date():
    start, due, title = parse_datetime("Buy new pants today", TZ)
    assert start is None
    assert due is not None and due.astimezone(ZoneInfo(TZ)).date() == _local_today()
    assert title == "Buy new pants"


def test_tomorrow_date_only():
    start, due, _ = parse_datetime("Call the dentist tomorrow", TZ)
    assert start is None
    assert due.astimezone(ZoneInfo(TZ)).date() == _local_today() + timedelta(days=1)


def test_today_at_time_becomes_scheduled_start():
    start, due, title = parse_datetime("Go to Walmart today at 5pm", TZ)
    assert due is None
    assert start is not None
    local = start.astimezone(ZoneInfo(TZ))
    assert local.date() == _local_today() and local.hour == 17 and local.minute == 0
    assert "Walmart" in title


def test_bare_time_defaults_to_today_scheduled():
    start, due, _ = parse_datetime("Team sync at 3pm", TZ)
    assert due is None and start is not None
    local = start.astimezone(ZoneInfo(TZ))
    assert local.date() == _local_today() and local.hour == 15


def test_month_day_due():
    start, due, _ = parse_datetime("Go to the mall July 5th", TZ)
    assert start is None
    local = due.astimezone(ZoneInfo(TZ))
    assert local.month == 7 and local.day == 5


def test_weekday_next_occurrence_due():
    _, due, _ = parse_datetime("Go to chiropractor on Monday", TZ)
    local = due.astimezone(ZoneInfo(TZ))
    assert local.weekday() == 0 and local.date() > _local_today()


def test_no_date_returns_none_but_cleans_title():
    start, due, title = parse_datetime("Buy milk", TZ)
    assert start is None and due is None
    assert title == "Buy milk"


def test_am_pm_and_minutes_scheduled():
    start, _, _ = parse_datetime("Standup tomorrow at 9:30am", TZ)
    local = start.astimezone(ZoneInfo(TZ))
    assert local.hour == 9 and local.minute == 30
    assert local.date() == _local_today() + timedelta(days=1)


def test_invalid_timezone_defaults_utc():
    _, due, _ = parse_datetime("ship it today", "Not/AZone")
    assert due is not None  # doesn't crash; uses UTC
