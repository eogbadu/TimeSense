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
    async def send(self, token, title, body, collapse_id=None, data=None):
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


async def test_send_test_bypasses_eligibility_and_cooldown(db_session):
    """test-push must deliver even for a non-eligible recommendation and inside cooldown."""
    from app.models.task import Task
    from app.repositories.push_notification_repository import PushNotificationRepository
    user = await _user(db_session)
    await _register(db_session, user)
    # low-priority, no deadline → NOT push-eligible normally
    db_session.add(Task(user_id=user.id, title="Someday idea", status="pending", priority=4))
    now = datetime.now(timezone.utc)
    await PushNotificationRepository(db_session).record(  # a recent push (would trigger cooldown)
        user_id=user.id, action_type="deadline_task", title="x", body="y",
        sent_at=now - timedelta(minutes=5), delivered_count=1)
    await db_session.flush()

    sender = _StubSender()
    result = await ProactivePushService(db_session).send_test(user, sender, now=now)
    assert result["delivered"] == 1 and result["apns_available"] is True
    assert len(sender.sent) == 1


async def test_send_test_honors_title_body_override(db_session):
    user = await _user(db_session)
    await _register(db_session, user)
    sender = _StubSender()
    result = await ProactivePushService(db_session).send_test(
        user, sender, title="Ping", body="It works.")
    assert result["title"] == "Ping" and result["body"] == "It works."
    assert sender.sent[0][1] == "Ping" and sender.sent[0][2] == "It works."


async def test_send_test_no_device(db_session):
    user = await _user(db_session)
    result = await ProactivePushService(db_session).send_test(user, _StubSender(), title="a", body="b")
    assert result["delivered"] == 0 and result["reason"] == "no_device"


async def test_offer_time_block_for_high_priority_unscheduled(db_session):
    """A high-priority unscheduled task with a free slot → a 'block time' offer is pushed."""
    from app.models.task import Task
    user = await _user(db_session)
    await _register(db_session, user)
    db_session.add(Task(user_id=user.id, title="Finish the grant", status="pending", priority=1,
                        estimated_minutes=60))  # unscheduled, high priority
    await db_session.flush()

    sender = _StubSender()
    # 09:00 UTC so there's working-hours room today
    now = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    offer = await ProactivePushService(db_session).offer_time_block_for_user(user, sender, now=now)
    assert offer is not None and offer["delivered"] == 1
    assert "Finish the grant" in offer["title"]
    assert sender.sent and sender.sent[0][3] == "offer_time_block"


async def test_no_offer_when_no_high_priority_unscheduled(db_session):
    from app.models.task import Task
    user = await _user(db_session)
    await _register(db_session, user)
    # low priority, no deadline → not offer-worthy
    db_session.add(Task(user_id=user.id, title="Someday", status="pending", priority=4))
    await db_session.flush()
    offer = await ProactivePushService(db_session).offer_time_block_for_user(user, _StubSender())
    assert offer is None


async def test_offer_respects_cooldown(db_session):
    from app.models.task import Task
    from app.repositories.push_notification_repository import PushNotificationRepository
    user = await _user(db_session)
    await _register(db_session, user)
    db_session.add(Task(user_id=user.id, title="Urgent thing", status="pending", priority=1,
                        estimated_minutes=30))
    now = datetime.now(timezone.utc).replace(hour=9)
    await PushNotificationRepository(db_session).record(
        user_id=user.id, action_type="deadline_task", title="x", body="y",
        sent_at=now - timedelta(minutes=10), delivered_count=1)
    await db_session.flush()
    offer = await ProactivePushService(db_session).offer_time_block_for_user(user, _StubSender(), now=now)
    assert offer is None  # inside the shared cooldown


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
