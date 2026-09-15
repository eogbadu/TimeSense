"""TIME-322: "Do this after…" — one task waiting for another, and never a loop."""
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.security import TokenUser
from app.models.task import Task, TaskPrerequisite
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.services.user_service import UserService

USER = TokenUser(uid="uid-prereq-1", email="prereq@example.com", role="user", email_verified=True)
OTHER = TokenUser(uid="uid-prereq-2", email="prereq-other@example.com", role="user", email_verified=True)
HEADERS = {"Authorization": "Bearer test-token"}


def _signed_in(user: TokenUser = USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


async def _user(db_session, token: TokenUser = USER):
    row, _ = await UserService(db_session).get_or_create_user(token.uid, token.email)
    return row


async def _task(db_session, user, title, **fields):
    task = Task(user_id=user.id, title=title, **fields)
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


async def _wait(client, task, prerequisite):
    with _signed_in():
        return await client.post(f"/api/v1/tasks/{task.id}/prerequisites", headers=HEADERS,
                                 json={"prerequisite_task_id": str(prerequisite.id)})


async def _stop_waiting(client, task, prerequisite):
    with _signed_in():
        return await client.delete(f"/api/v1/tasks/{task.id}/prerequisites/{prerequisite.id}",
                                   headers=HEADERS)


async def _get(client, task):
    with _signed_in():
        return (await client.get(f"/api/v1/tasks/{task.id}", headers=HEADERS)).json()


async def _edges(db_session):
    rows = await db_session.execute(
        select(TaskPrerequisite.task_id, TaskPrerequisite.prerequisite_task_id, TaskPrerequisite.origin)
    )
    return set(rows.all())


# ── Adding a wait ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_a_task_can_wait_for_another(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor")

    r = await _wait(client, pay, invoice)

    assert r.status_code == 201
    assert r.json()["blocked_by"] == [{"id": str(invoice.id), "title": "Get invoice"}]
    assert await _edges(db_session) == {(pay.id, invoice.id, "manual")}


@pytest.mark.anyio
async def test_adding_the_same_wait_twice_changes_nothing(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor")

    assert (await _wait(client, pay, invoice)).status_code == 201
    assert (await _wait(client, pay, invoice)).status_code == 201
    assert len(await _edges(db_session)) == 1


@pytest.mark.anyio
async def test_a_task_cannot_wait_for_itself(client, db_session):
    user = await _user(db_session)
    pay = await _task(db_session, user, "Pay contractor")

    assert (await _wait(client, pay, pay)).status_code == 400


@pytest.mark.anyio
async def test_another_users_task_is_not_found(client, db_session):
    user = await _user(db_session)
    other = await _user(db_session, OTHER)
    pay = await _task(db_session, user, "Pay contractor")
    theirs = await _task(db_session, other, "Their invoice")

    assert (await _wait(client, pay, theirs)).status_code == 404
    assert await _edges(db_session) == set()


@pytest.mark.anyio
async def test_calendar_events_cannot_wait_or_be_waited_on(client, db_session):
    user = await _user(db_session)
    meeting = await _task(db_session, user, "Team sync", source="calendar")
    notes = await _task(db_session, user, "Prepare notes")

    assert (await _wait(client, notes, meeting)).status_code == 422
    assert (await _wait(client, meeting, notes)).status_code == 422


@pytest.mark.anyio
async def test_a_task_can_wait_for_at_most_ten_others(client, db_session):
    user = await _user(db_session)
    launch = await _task(db_session, user, "Launch")
    for i in range(10):
        assert (await _wait(client, launch, await _task(db_session, user, f"Check {i}"))).status_code == 201

    assert (await _wait(client, launch, await _task(db_session, user, "One more"))).status_code == 422


# ── Never a loop ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_two_tasks_cannot_wait_for_each_other(client, db_session):
    user = await _user(db_session)
    a = await _task(db_session, user, "A")
    b = await _task(db_session, user, "B")
    await _wait(client, a, b)

    r = await _wait(client, b, a)

    assert r.status_code == 409
    assert await _edges(db_session) == {(a.id, b.id, "manual")}


@pytest.mark.anyio
async def test_a_longer_loop_is_refused_too(client, db_session):
    user = await _user(db_session)
    a, b, c = [await _task(db_session, user, name) for name in ("A", "B", "C")]
    await _wait(client, a, b)
    await _wait(client, b, c)

    assert (await _wait(client, c, a)).status_code == 409


@pytest.mark.anyio
async def test_a_parent_cannot_wait_for_its_own_step(client, db_session):
    # The step inherits the parent's waits, so this would make the step wait for itself.
    user = await _user(db_session)
    passport = await _task(db_session, user, "Renew passport")
    photos = await _task(db_session, user, "Get photos", parent_task_id=passport.id, position=0)

    assert (await _wait(client, passport, photos)).status_code == 409


@pytest.mark.anyio
async def test_a_loop_through_a_group_is_refused(client, db_session):
    user = await _user(db_session)
    appointment = await _task(db_session, user, "Book appointment")
    passport = await _task(db_session, user, "Renew passport")
    photos = await _task(db_session, user, "Get photos", parent_task_id=passport.id, position=0)
    await _wait(client, passport, appointment)

    # Get photos already waits for the appointment through its parent.
    assert (await _wait(client, appointment, photos)).status_code == 409


@pytest.mark.anyio
async def test_a_step_cannot_wait_for_the_task_it_belongs_to(client, db_session):
    user = await _user(db_session)
    passport = await _task(db_session, user, "Renew passport")
    photos = await _task(db_session, user, "Get photos", parent_task_id=passport.id, position=0)

    assert (await _wait(client, photos, passport)).status_code == 422


@pytest.mark.anyio
async def test_a_step_can_wait_for_a_task_outside_its_group(client, db_session):
    user = await _user(db_session)
    passport = await _task(db_session, user, "Renew passport")
    mail = await _task(db_session, user, "Mail it", parent_task_id=passport.id, position=0)
    stamps = await _task(db_session, user, "Buy stamps")

    r = await _wait(client, mail, stamps)

    assert r.status_code == 201
    assert r.json()["blocked_by"] == [{"id": str(stamps.id), "title": "Buy stamps"}]


# ── When a wait ends ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_finishing_or_deleting_the_prerequisite_ends_the_wait(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    quote = await _task(db_session, user, "Get quote")
    pay = await _task(db_session, user, "Pay contractor")
    await _wait(client, pay, invoice)
    await _wait(client, pay, quote)

    with _signed_in():
        await client.patch(f"/api/v1/tasks/{invoice.id}", headers=HEADERS, json={"status": "done"})
        await client.delete(f"/api/v1/tasks/{quote.id}", headers=HEADERS)

    assert (await _get(client, pay))["blocked_by"] == []


@pytest.mark.anyio
async def test_starting_the_prerequisite_does_not_end_the_wait(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor")
    await _wait(client, pay, invoice)

    with _signed_in():
        await client.patch(f"/api/v1/tasks/{invoice.id}", headers=HEADERS, json={"status": "in_progress"})

    assert [ref["title"] for ref in (await _get(client, pay))["blocked_by"]] == ["Get invoice"]


@pytest.mark.anyio
async def test_dont_wait_removes_a_wait_the_user_set(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor")
    await _wait(client, pay, invoice)

    r = await _stop_waiting(client, pay, invoice)

    assert r.status_code == 204
    assert await _edges(db_session) == set()
    assert (await _stop_waiting(client, pay, invoice)).status_code == 404


@pytest.mark.anyio
async def test_the_order_of_a_groups_steps_is_not_removed_as_a_wait(client, db_session):
    user = await _user(db_session)
    passport = await _task(db_session, user, "Renew passport", steps_sequential=True)
    photos = await _task(db_session, user, "Get photos", parent_task_id=passport.id, position=0)
    form = await _task(db_session, user, "Fill out the form", parent_task_id=passport.id, position=1)
    await TaskPrerequisiteRepository(db_session).rechain_steps(passport)

    assert (await _stop_waiting(client, form, photos)).status_code == 422
    assert await _edges(db_session) == {(form.id, photos.id, "sequence")}


@pytest.mark.anyio
async def test_a_wait_the_user_set_survives_changes_to_the_group(client, db_session):
    user = await _user(db_session)
    passport = await _task(db_session, user, "Renew passport", steps_sequential=True)
    photos = await _task(db_session, user, "Get photos", parent_task_id=passport.id, position=0)
    form = await _task(db_session, user, "Fill out the form", parent_task_id=passport.id, position=1)
    mail = await _task(db_session, user, "Mail it", parent_task_id=passport.id, position=2)
    await TaskPrerequisiteRepository(db_session).rechain_steps(passport)
    stamps = await _task(db_session, user, "Buy stamps")
    await _wait(client, mail, stamps)

    with _signed_in():
        await client.delete(f"/api/v1/tasks/{form.id}", headers=HEADERS)

    assert await _edges(db_session) == {
        (mail.id, photos.id, "sequence"), (mail.id, stamps.id, "manual"),
    }
