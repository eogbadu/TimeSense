"""TIME-320: storage for steps and prerequisites, and the graph read layer every task response uses."""
from unittest.mock import patch

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.core.security import TokenUser
from app.models.task import Task, TaskPrerequisite
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.services.task_graph import TaskGraphService
from app.services.user_service import UserService

USER = TokenUser(uid="uid-graph-1", email="g1@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role, "email_verified": user.email_verified},
    )


async def _user(db_session):
    row, _ = await UserService(db_session).get_or_create_user(USER.uid, USER.email)
    return row


async def _task(db_session, user, title, **fields):
    task = Task(user_id=user.id, title=title, **fields)
    db_session.add(task)
    await db_session.flush()
    return task


async def _waits(db_session, user, task, prerequisite, origin="manual"):
    await TaskPrerequisiteRepository(db_session).add(user.id, task.id, prerequisite.id, origin=origin)


async def _edges(db_session):
    rows = await db_session.execute(
        select(TaskPrerequisite.task_id, TaskPrerequisite.prerequisite_task_id, TaskPrerequisite.origin)
    )
    return set(rows.all())


# ── Constraints ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_a_task_cannot_be_its_own_parent(db_session):
    user = await _user(db_session)
    task = await _task(db_session, user, "Renew passport")
    task.parent_task_id = task.id
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.anyio
async def test_a_task_cannot_wait_for_itself(db_session):
    user = await _user(db_session)
    task = await _task(db_session, user, "Renew passport")
    db_session.add(TaskPrerequisite(task_id=task.id, prerequisite_task_id=task.id, user_id=user.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.anyio
async def test_adding_the_same_wait_twice_keeps_one_edge(db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor")
    repo = TaskPrerequisiteRepository(db_session)
    assert await repo.add(user.id, pay.id, invoice.id) is True
    assert await repo.add(user.id, pay.id, invoice.id) is False
    assert len(await _edges(db_session)) == 1


# ── Annotation ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_blocked_by_lists_only_prerequisites_that_are_not_done_or_cancelled(db_session):
    user = await _user(db_session)
    pending = await _task(db_session, user, "Pending", status="pending")
    done = await _task(db_session, user, "Done", status="done")
    cancelled = await _task(db_session, user, "Cancelled", status="cancelled")
    started = await _task(db_session, user, "Started", status="in_progress")
    waiting = await _task(db_session, user, "Waiting")
    for prereq in (pending, done, cancelled, started):
        await _waits(db_session, user, waiting, prereq)

    info = await TaskGraphService(db_session).annotate([waiting])

    assert {ref.title for ref in info.blocked_by[waiting.id]} == {"Pending", "Started"}


@pytest.mark.anyio
async def test_a_step_waits_for_whatever_its_parent_waits_for(db_session):
    user = await _user(db_session)
    appointment = await _task(db_session, user, "Book passport appointment")
    parent = await _task(db_session, user, "Renew passport")
    await _waits(db_session, user, parent, appointment)
    step = await _task(db_session, user, "Get photos", parent_task_id=parent.id, position=0)

    # The parent is not in the list, so annotate has to fetch it.
    [response] = await TaskGraphService(db_session).responses([step])

    assert [ref.title for ref in response.blocked_by] == ["Book passport appointment"]
    assert response.parent_task_id == parent.id
    assert response.parent_title == "Renew passport"
    assert response.position == 0


@pytest.mark.anyio
async def test_step_counts_ignore_cancelled_steps(db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Renew passport")
    await _task(db_session, user, "Get photos", parent_task_id=parent.id, status="done")
    await _task(db_session, user, "Fill out the form", parent_task_id=parent.id, status="pending")
    await _task(db_session, user, "Old idea", parent_task_id=parent.id, status="cancelled")

    [response] = await TaskGraphService(db_session).responses([parent])

    assert (response.step_count, response.open_step_count) == (2, 1)


@pytest.mark.anyio
async def test_recommendable_skips_waiting_tasks_parents_with_open_steps_and_orphaned_steps(db_session):
    user = await _user(db_session)
    free = await _task(db_session, user, "Get invoice")
    waiting = await _task(db_session, user, "Pay contractor")
    await _waits(db_session, user, waiting, free)
    parent = await _task(db_session, user, "Renew passport")
    step = await _task(db_session, user, "Get photos", parent_task_id=parent.id)
    finished_parent = await _task(db_session, user, "Plan party", status="done")
    orphan = await _task(db_session, user, "Order cake", parent_task_id=finished_parent.id)

    svc = TaskGraphService(db_session)
    candidates = [free, waiting, parent, step, orphan]
    picked = svc.recommendable(candidates, await svc.annotate(candidates))

    assert [t.title for t in picked] == ["Get invoice", "Get photos"]


@pytest.mark.anyio
async def test_annotate_uses_the_same_number_of_queries_for_two_tasks_or_twelve(db_session):
    user = await _user(db_session)
    few = [await _task(db_session, user, f"Few {i}") for i in range(2)]
    many = [await _task(db_session, user, f"Many {i}") for i in range(12)]
    await _waits(db_session, user, many[1], many[0])
    await db_session.flush()

    statements: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = db_session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", _record)
    try:
        svc = TaskGraphService(db_session)
        await svc.annotate(few)
        for_few = len(statements)
        statements.clear()
        await svc.annotate(many)
        for_many = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", _record)

    assert for_few == for_many <= 3


# ── Re-chaining ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_rechain_orders_steps_and_never_touches_manual_waits(db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Renew passport", steps_sequential=True)
    photos = await _task(db_session, user, "Get photos", parent_task_id=parent.id, position=0)
    form = await _task(db_session, user, "Fill out the form", parent_task_id=parent.id, position=1)
    mail = await _task(db_session, user, "Mail it", parent_task_id=parent.id, position=2)
    stamps = await _task(db_session, user, "Buy stamps")
    await _waits(db_session, user, mail, stamps)
    repo = TaskPrerequisiteRepository(db_session)

    await repo.rechain_steps(parent)
    assert await _edges(db_session) == {
        (form.id, photos.id, "sequence"),
        (mail.id, form.id, "sequence"),
        (mail.id, stamps.id, "manual"),
    }

    # Cancelling the middle step must not unblock the last one while the first is still open.
    form.status = "cancelled"
    await repo.rechain_steps(parent)
    assert await _edges(db_session) == {
        (mail.id, photos.id, "sequence"),
        (mail.id, stamps.id, "manual"),
    }

    parent.steps_sequential = False
    await repo.rechain_steps(parent)
    assert await _edges(db_session) == {(mail.id, stamps.id, "manual")}


# ── API responses ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_task_responses_carry_the_graph_fields(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor")
    await _waits(db_session, user, pay, invoice)
    parent = await _task(db_session, user, "Renew passport")
    await _task(db_session, user, "Get photos", parent_task_id=parent.id, status="done")
    await _task(db_session, user, "Mail it", parent_task_id=parent.id)

    with _mock_verify(USER):
        single = await client.get(f"/api/v1/tasks/{pay.id}", headers=_auth_headers())
        listed = await client.get("/api/v1/tasks", headers=_auth_headers())

    assert single.status_code == 200
    body = single.json()
    assert body["blocked_by"] == [{"id": str(invoice.id), "title": "Get invoice"}]
    assert body["parent_task_id"] is None and body["parent_title"] is None
    assert body["steps"] == [] and body["suggested_parent"] is None

    by_title = {t["title"]: t for t in listed.json()}
    assert (by_title["Renew passport"]["step_count"], by_title["Renew passport"]["open_step_count"]) == (2, 1)
    assert by_title["Mail it"]["parent_title"] == "Renew passport"
    assert by_title["Get invoice"]["blocked_by"] == []


@pytest.mark.anyio
async def test_today_plan_task_payload_shows_what_it_waits_for(client, db_session):
    user = await _user(db_session)
    invoice = await _task(db_session, user, "Get invoice")
    pay = await _task(db_session, user, "Pay contractor")
    await _waits(db_session, user, pay, invoice)

    with _mock_verify(USER):
        r = await client.get("/api/v1/timeline/today/plan", headers=_auth_headers())

    assert r.status_code == 200
    tasks = {e["title"]: e["task"] for e in r.json() if e["kind"] == "task"}
    assert tasks["Pay contractor"]["blocked_by"] == [{"id": str(invoice.id), "title": "Get invoice"}]
    assert tasks["Get invoice"]["blocked_by"] == []
