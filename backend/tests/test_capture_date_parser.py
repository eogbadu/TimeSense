"""Tests for the rule-based capture date parser (TIME-072)."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.services.capture_date_parser import parse_datetime

TZ = "America/New_York"


def _local_today(tz=TZ):
    return datetime.now(ZoneInfo(tz)).date()


def test_today_gets_a_due_date():
    due, title = parse_datetime("Buy new pants today", TZ)
    assert due is not None
    assert due.astimezone(ZoneInfo(TZ)).date() == _local_today()
    assert title == "Buy new pants"


def test_tomorrow():
    due, _ = parse_datetime("Call the dentist tomorrow", TZ)
    assert due.astimezone(ZoneInfo(TZ)).date() == _local_today() + timedelta(days=1)


def test_today_at_time():
    due, title = parse_datetime("Go to Walmart today at 5pm", TZ)
    local = due.astimezone(ZoneInfo(TZ))
    assert local.date() == _local_today()
    assert local.hour == 17 and local.minute == 0
    assert "Walmart" in title


def test_month_day():
    due, _ = parse_datetime("Go to the mall July 5th", TZ)
    local = due.astimezone(ZoneInfo(TZ))
    assert local.month == 7 and local.day == 5


def test_weekday_next_occurrence():
    due, _ = parse_datetime("Go to chiropractor on Monday", TZ)
    local = due.astimezone(ZoneInfo(TZ))
    assert local.weekday() == 0  # Monday
    assert local.date() > _local_today()  # a future Monday, not today


def test_no_date_returns_none_but_cleans_title():
    due, title = parse_datetime("Buy milk", TZ)
    assert due is None
    assert title == "Buy milk"


def test_am_pm_and_minutes():
    due, _ = parse_datetime("Standup tomorrow at 9:30am", TZ)
    local = due.astimezone(ZoneInfo(TZ))
    assert local.hour == 9 and local.minute == 30


def test_invalid_timezone_defaults_utc():
    due, _ = parse_datetime("ship it today", "Not/AZone")
    assert due is not None  # doesn't crash; uses UTC
