"""TIME-277: pull OAuth-connected calendars into SyncedCalendarEvent so they flow into the plan.

The provider (and token refresh) are stubbed — this exercises the sync logic, not real HTTP/OAuth."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.integrations.calendar_base import CalendarEvent
from app.models.calendar import CalendarIntegration
from app.repositories.calendar_repository import CalendarIntegrationRepository
from app.repositories.synced_calendar_event_repository import SyncedCalendarEventRepository
from app.services.calendar_event_sync_service import CalendarEventSyncService
from app.services.user_service import UserService

NOW = datetime.now(timezone.utc)


class _StubProvider:
    def __init__(self, events, fail_first_401=False):
        self._events = events
        self._fail = fail_first_401
        self.calls = 0

    async def list_events(self, access_token, start, end, calendar_id="primary"):
        self.calls += 1
        if self._fail and self.calls == 1:
            raise HTTPException(status_code=401, detail="expired")
        return self._events


def _event(title, hours_ahead, minutes=30, all_day=False, eid=None):
    start = NOW + timedelta(hours=hours_ahead)
    return CalendarEvent(title=title, start=start, end=start + timedelta(minutes=minutes),
                         event_id=eid or title, provider="google", all_day=all_day)


async def _connect(db_session, provider="google", refresh="rt"):
    user, _ = await UserService(db_session).get_or_create_user("uid-oauth-cal", "oc@example.com")
    db_session.add(CalendarIntegration(
        user_id=user.id, provider=provider, access_token="at",
        refresh_token=refresh, calendar_id="primary", is_active=True))
    await db_session.flush()
    return user


async def _synced(db_session, user_id):
    return await SyncedCalendarEventRepository(db_session).list_window(
        user_id, NOW - timedelta(hours=13), NOW + timedelta(hours=37))


@pytest.mark.anyio
async def test_sync_user_writes_timed_events_and_skips_all_day(db_session, monkeypatch):
    user = await _connect(db_session)
    stub = _StubProvider([_event("Standup", 1), _event("Holiday", 2, all_day=True, eid="h")])
    monkeypatch.setattr("app.services.calendar_event_sync_service.get_provider", lambda name: stub)

    n = await CalendarEventSyncService(db_session).sync_user(user.id)

    assert n == 1  # all-day skipped
    rows = await _synced(db_session, user.id)
    assert len(rows) == 1
    assert rows[0].source == "google"
    assert rows[0].title == "Standup"


@pytest.mark.anyio
async def test_resync_is_idempotent(db_session, monkeypatch):
    user = await _connect(db_session)
    stub = _StubProvider([_event("Standup", 1)])
    monkeypatch.setattr("app.services.calendar_event_sync_service.get_provider", lambda name: stub)
    svc = CalendarEventSyncService(db_session)

    await svc.sync_user(user.id)
    await svc.sync_user(user.id)

    rows = await _synced(db_session, user.id)
    assert len(rows) == 1  # replace_for_source — no duplicate


@pytest.mark.anyio
async def test_expired_token_is_refreshed_then_synced(db_session, monkeypatch):
    user = await _connect(db_session)
    stub = _StubProvider([_event("Standup", 1)], fail_first_401=True)
    monkeypatch.setattr("app.services.calendar_event_sync_service.get_provider", lambda name: stub)

    from app.integrations.google_oauth import TokenResult

    async def fake_refresh(refresh_token):
        assert refresh_token == "rt"
        return TokenResult(access_token="new-at", refresh_token="rt2", expires_at=None)

    monkeypatch.setattr("app.integrations.google_oauth.refresh_access_token", fake_refresh)

    n = await CalendarEventSyncService(db_session).sync_user(user.id)

    assert n == 1
    assert stub.calls == 2  # 401, then retried after refresh
    integ = await CalendarIntegrationRepository(db_session).get_active(user.id, "google")
    assert integ.access_token == "new-at"


@pytest.mark.anyio
async def test_missing_refresh_token_gives_up_quietly(db_session, monkeypatch):
    user = await _connect(db_session, refresh=None)
    stub = _StubProvider([_event("Standup", 1)], fail_first_401=True)
    monkeypatch.setattr("app.services.calendar_event_sync_service.get_provider", lambda name: stub)

    n = await CalendarEventSyncService(db_session).sync_user(user.id)

    assert n == 0  # 401 with no refresh token → skip this integration, no crash
    assert await _synced(db_session, user.id) == []
