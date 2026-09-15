"""TIME-324: the Today plan shows a group once, with its steps nested underneath."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.models.task import Task
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.services.user_service import UserService

USER = TokenUser(uid="uid-plan-steps", email="plan-steps@example.com", role="user", email_verified=True)
HEADERS = {"Authorization": "Bearer test-token"}


def _signed_in():
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": USER.uid, "email": USER.email, "role": "user", "email_verified": True},
    )


def _today_at(hour: int) -> datetime:
    return datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0)


async def _user(db_session):
    row, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    return row


async def _task(db_session, user, title, **fields):
    fields.setdefault("status", "pending")
    task = Task(user_id=user.id, title=title, **fields)
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


async def _plan(client):
    today = datetime.now(timezone.utc).date()
    with _signed_in():
        r = await client.get(f"/api/v1/timeline/today/plan?date={today.isoformat()}", headers=HEADERS)
    assert r.status_code == 200
    return [e for e in r.json() if e["kind"] == "task"]


def _at(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_a_group_appears_once_with_its_steps_in_order(client, db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Renew passport", steps_sequential=True)
    photos = await _task(db_session, user, "Get photos", parent_task_id=parent.id, position=0,
                         status="done")
    form = await _task(db_session, user, "Fill out the form", parent_task_id=parent.id, position=1)
    await _task(db_session, user, "Mail it", parent_task_id=parent.id, position=2)
    await TaskPrerequisiteRepository(db_session).rechain_steps(parent)
    await _task(db_session, user, "Call the bank")

    entries = await _plan(client)

    assert sorted(e["title"] for e in entries) == ["Call the bank", "Renew passport"]
    group = next(e for e in entries if e["title"] == "Renew passport")["task"]
    assert [s["title"] for s in group["steps"]] == ["Get photos", "Fill out the form", "Mail it"]
    assert (group["step_count"], group["open_step_count"]) == (3, 2)
    mail = group["steps"][2]
    assert mail["parent_title"] == "Renew passport"
    assert [ref["title"] for ref in mail["blocked_by"]] == ["Fill out the form"]
    assert group["steps"][0]["id"] == str(photos.id) and group["steps"][1]["id"] == str(form.id)


@pytest.mark.anyio
async def test_a_step_timed_today_brings_its_untimed_parent_and_sets_the_groups_time(client, db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Renew passport",
                         due_at=datetime.now(timezone.utc) + timedelta(days=5))
    await _task(db_session, user, "Get photos", parent_task_id=parent.id, position=0,
                scheduled_start=_today_at(15), scheduled_end=_today_at(16))

    entries = await _plan(client)

    assert [e["title"] for e in entries] == ["Renew passport"]
    assert _at(entries[0]["start"]) == _today_at(15)
    assert _at(entries[0]["end"]) == _today_at(16)


@pytest.mark.anyio
async def test_the_group_sits_at_its_next_open_step_not_a_finished_one(client, db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Renew passport")
    await _task(db_session, user, "Get photos", parent_task_id=parent.id, position=0, status="done",
                scheduled_start=_today_at(9), scheduled_end=_today_at(10))
    await _task(db_session, user, "Fill out the form", parent_task_id=parent.id, position=1,
                scheduled_start=_today_at(13), scheduled_end=_today_at(14))

    entries = await _plan(client)

    assert [e["title"] for e in entries] == ["Renew passport"]
    assert _at(entries[0]["start"]) == _today_at(13)


@pytest.mark.anyio
async def test_cancelled_steps_are_not_listed(client, db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Renew passport")
    await _task(db_session, user, "Get photos", parent_task_id=parent.id, position=0)
    await _task(db_session, user, "Old idea", parent_task_id=parent.id, position=1, status="cancelled")

    entries = await _plan(client)

    group = next(e for e in entries if e["title"] == "Renew passport")["task"]
    assert [s["title"] for s in group["steps"]] == ["Get photos"]


@pytest.mark.anyio
async def test_a_task_without_steps_keeps_an_empty_steps_list(client, db_session):
    user = await _user(db_session)
    await _task(db_session, user, "Call the bank", scheduled_start=_today_at(11),
                scheduled_end=_today_at(12))

    entries = await _plan(client)

    assert entries[0]["task"]["steps"] == [] and _at(entries[0]["start"]) == _today_at(11)
