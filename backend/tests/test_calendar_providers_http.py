"""TIME-280: verify the OAuth calendar providers against realistic mocked HTTP payloads.

This closes the gap the stubbed-provider tests left: the real JSON->CalendarEvent parsing (timed vs
all-day), request params, error mapping (401/5xx), and the token-refresh request/response shape — the
parts most likely to break in production. No live network: httpx is mocked with MockTransport."""
from datetime import UTC, datetime, timedelta, timezone
from urllib.parse import parse_qsl

import httpx
import pytest
from fastapi import HTTPException

from app.integrations.google_calendar import GoogleCalendarProvider
from app.integrations.microsoft_calendar import MicrosoftCalendarProvider
from app.integrations import google_oauth, microsoft_oauth

START = datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc)
END = START + timedelta(days=1)


def _mock_httpx(monkeypatch, handler):
    """Route every httpx.AsyncClient request through `handler` (a Request->Response callable)."""
    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real(*args, **kwargs)

    monkeypatch.setattr("httpx.AsyncClient", factory)


def _form(request: httpx.Request) -> dict:
    return dict(parse_qsl(request.content.decode()))


# ── Google Calendar list_events ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_google_list_events_parses_timed_and_all_day(monkeypatch):
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"items": [
            {"id": "e1", "summary": "Standup",
             "start": {"dateTime": "2026-08-05T09:00:00+00:00"},
             "end": {"dateTime": "2026-08-05T09:30:00+00:00"},
             "location": "HQ"},
            {"id": "e2", "summary": "Holiday",
             "start": {"date": "2026-08-06"}, "end": {"date": "2026-08-07"}},
        ]})

    _mock_httpx(monkeypatch, handler)
    events = await GoogleCalendarProvider().list_events("AT", START, END)

    assert captured["path"] == "/calendar/v3/calendars/primary/events"
    assert captured["params"]["singleEvents"] == "true"
    assert captured["auth"] == "Bearer AT"
    assert len(events) == 2
    timed, allday = events
    assert timed.title == "Standup" and timed.all_day is False and timed.location == "HQ"
    assert timed.start == datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc)
    assert allday.title == "Holiday" and allday.all_day is True


@pytest.mark.anyio
async def test_google_list_events_401_raises(monkeypatch):
    _mock_httpx(monkeypatch, lambda r: httpx.Response(401, json={"error": "invalid"}))
    with pytest.raises(HTTPException) as exc:
        await GoogleCalendarProvider().list_events("AT", START, END)
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_google_list_events_5xx_maps_to_502(monkeypatch):
    _mock_httpx(monkeypatch, lambda r: httpx.Response(500, text="boom"))
    with pytest.raises(HTTPException) as exc:
        await GoogleCalendarProvider().list_events("AT", START, END)
    assert exc.value.status_code == 502


# ── Microsoft Graph list_events ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_microsoft_list_events_parses_all_day_flag(monkeypatch):
    def handler(request):
        assert request.url.path == "/v1.0/me/calendarView"
        return httpx.Response(200, json={"value": [
            {"id": "m1", "subject": "Sync",
             "start": {"dateTime": "2026-08-05T09:00:00.0000000"},
             "end": {"dateTime": "2026-08-05T09:30:00.0000000"},
             "isAllDay": False, "location": {"displayName": "Room 2"}},
            {"id": "m2", "subject": "Company holiday",
             "start": {"dateTime": "2026-08-06T00:00:00.0000000"},
             "end": {"dateTime": "2026-08-07T00:00:00.0000000"},
             "isAllDay": True},
        ]})

    _mock_httpx(monkeypatch, handler)
    events = await MicrosoftCalendarProvider().list_events("AT", START, END)

    assert len(events) == 2
    assert events[0].title == "Sync" and events[0].all_day is False
    assert events[0].location == "Room 2"
    assert events[0].start == datetime(2026, 8, 5, 9, 0)
    assert events[1].all_day is True


@pytest.mark.anyio
async def test_microsoft_list_events_401_raises(monkeypatch):
    _mock_httpx(monkeypatch, lambda r: httpx.Response(401, json={}))
    with pytest.raises(HTTPException) as exc:
        await MicrosoftCalendarProvider().list_events("AT", START, END)
    assert exc.value.status_code == 401


# ── Token refresh ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_google_refresh_sends_grant_and_keeps_refresh_token(monkeypatch):
    captured = {}

    def handler(request):
        captured["body"] = _form(request)
        # Google usually omits refresh_token on refresh.
        return httpx.Response(200, json={"access_token": "NEW-AT", "expires_in": 3600})

    _mock_httpx(monkeypatch, handler)
    before = datetime.now(UTC)
    result = await google_oauth.refresh_access_token("RT")

    assert captured["body"]["grant_type"] == "refresh_token"
    assert captured["body"]["refresh_token"] == "RT"
    assert result.access_token == "NEW-AT"
    assert result.refresh_token == "RT"  # kept, since the response omitted one
    assert result.expires_at is not None
    assert timedelta(minutes=59) < (result.expires_at - before) < timedelta(minutes=61)


@pytest.mark.anyio
async def test_microsoft_refresh_uses_rotated_token(monkeypatch):
    def handler(request):
        body = _form(request)
        assert body["grant_type"] == "refresh_token"
        assert body["refresh_token"] == "RT"
        assert "scope" in body
        return httpx.Response(200, json={"access_token": "NEW", "refresh_token": "RT2", "expires_in": 3600})

    _mock_httpx(monkeypatch, handler)
    result = await microsoft_oauth.refresh_access_token("RT")

    assert result.access_token == "NEW"
    assert result.refresh_token == "RT2"  # Microsoft rotates the refresh token
