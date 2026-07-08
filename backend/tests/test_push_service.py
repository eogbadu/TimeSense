"""TIME-121 — proactive push decision logic (eligibility, cooldown, urgency override, gating)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.push.push_service import COOLDOWN, ProactivePushService
from app.services.push.sender import NullPushSender

pytestmark = pytest.mark.anyio

USER_UID = "push-1"


class _StubSender:
    """Records every send; always 'delivers'."""
    def __init__(self): self.sent = []
    @property
    def available(self): return True
    async def send(self, token, title, body, collapse_id=None):
        self.sent.append((token, title, body, collapse_id))
        return True


async def _user(db):
    from app.services.user_service import UserService
    user, _ = await UserService(db).get_or_create_user(USER_UID, "push@example.com")
    return user


async def _register(db, user, token="devtok"):
    from app.repositories.device_token_repository import DeviceTokenRepository
    await DeviceTokenRepository(db).upsert(user.id, token)
    await db.flush()


async def _urgent_task(db, user, title="Overdue filing"):
    from app.models.task import Task
    t = Task(user_id=user.id, title=title, status="pending", priority=1,
             due_at=datetime.now(timezone.utc) - timedelta(days=1), estimated_minutes=20)
    db.add(t)
    await db.flush()
    return t


async def test_no_push_without_device_token(db_session):
    user = await _user(db_session)
    await _urgent_task(db_session, user)
    sender = _StubSender()
    rec = await ProactivePushService(db_session).push_for_user(user, sender)
    assert rec is None and sender.sent == []  # no registered device


async def test_no_push_when_not_eligible(db_session):
    """A low-priority task with no deadline isn't push-eligible (score < 75)."""
    from app.models.task import Task
    user = await _user(db_session)
    await _register(db_session, user)
    db_session.add(Task(user_id=user.id, title="Someday idea", status="pending", priority=4))
    await db_session.flush()
    sender = _StubSender()
    rec = await ProactivePushService(db_session).push_for_user(user, sender)
    assert rec is None and sender.sent == []


async def test_cooldown_suppresses_same_type(db_session):
    from app.repositories.push_notification_repository import PushNotificationRepository
    user = await _user(db_session)
    await _register(db_session, user)
    task = await _urgent_task(db_session, user)
    now = datetime.now(timezone.utc)

    # A recent push of the SAME action type (deadline_task) → suppress.
    await PushNotificationRepository(db_session).record(
        user_id=user.id, action_type="deadline_task", title="x", body="y",
        sent_at=now - timedelta(minutes=10), delivered_count=1)
    await db_session.flush()

    sender = _StubSender()
    rec = await ProactivePushService(db_session).push_for_user(user, sender, now=now)
    assert rec is None and sender.sent == []


async def test_pushes_after_cooldown_elapses(db_session):
    from app.repositories.push_notification_repository import PushNotificationRepository
    user = await _user(db_session)
    await _register(db_session, user)
    await _urgent_task(db_session, user)
    now = datetime.now(timezone.utc)

    await PushNotificationRepository(db_session).record(
        user_id=user.id, action_type="deadline_task", title="x", body="y",
        sent_at=now - COOLDOWN - timedelta(minutes=1), delivered_count=1)
    await db_session.flush()

    sender = _StubSender()
    rec = await ProactivePushService(db_session).push_for_user(user, sender, now=now)
    assert rec is not None and len(sender.sent) == 1
    assert sender.sent[0][3] == rec.action_type  # collapse id = action type


async def test_null_sender_records_nothing_delivered(db_session):
    """With no APNs configured, the decision still runs but nothing is delivered."""
    user = await _user(db_session)
    await _register(db_session, user)
    await _urgent_task(db_session, user)
    rec = await ProactivePushService(db_session).push_for_user(user, NullPushSender())
    # eligible + not in cooldown → a push record is made, but 0 delivered
    assert rec is not None
    from app.repositories.push_notification_repository import PushNotificationRepository
    last = await PushNotificationRepository(db_session).latest_for_user(user.id)
    assert last is not None and last.delivered_count == 0
