"""TIME-321: steps — creating them, joining and leaving a group, and the parent finishing by itself."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.core.security import TokenUser
from app.models.task import Task, TaskPrerequisite
from app.repositories.recommendation_swap_repository import RecommendationSwapRepository
from app.repositories.task_prerequisite_repository import TaskPrerequisiteRepository
from app.repositories.task_repository import TaskRepository
from app.services.user_service import UserService

USER = TokenUser(uid="uid-steps-1", email="steps@example.com", role="user", email_verified=True)
HEADERS = {"Authorization": "Bearer test-token"}


def _signed_in(user: TokenUser = USER):
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
    await db_session.refresh(task)
    return task


async def _group(db_session, user, title="Renew passport",
                 steps=("Get photos", "Fill out the form", "Mail it"), sequential=True, **parent_fields):
    parent = await _task(db_session, user, title, steps_sequential=sequential, **parent_fields)
    children = [
        await _task(db_session, user, name, parent_task_id=parent.id, position=i)
        for i, name in enumerate(steps)
    ]
    await TaskPrerequisiteRepository(db_session).rechain_steps(parent)
    return parent, children


async def _fresh(db_session, *tasks):
    for t in tasks:
        await db_session.refresh(t)
    return tasks[0] if len(tasks) == 1 else tasks


async def _edges(db_session):
    rows = await db_session.execute(
        select(TaskPrerequisite.task_id, TaskPrerequisite.prerequisite_task_id, TaskPrerequisite.origin)
    )
    return set(rows.all())


async def _patch(client, task, **body):
    with _signed_in():
        return await client.patch(f"/api/v1/tasks/{task.id}", headers=HEADERS, json=body)


async def _delete(client, task):
    with _signed_in():
        return await client.delete(f"/api/v1/tasks/{task.id}", headers=HEADERS)


# ── The parent finishes by itself, whichever path finished the last step ─────

@pytest.mark.anyio
async def test_finishing_the_last_step_finishes_the_parent(client, db_session):
    user = await _user(db_session)
    parent, (photos, form) = await _group(db_session, user, steps=("Get photos", "Fill out the form"))

    assert (await _patch(client, photos, status="done")).status_code == 200
    assert (await _fresh(db_session, parent)).status == "pending"

    assert (await _patch(client, form, status="done")).status_code == 200
    parent = await _fresh(db_session, parent)
    assert parent.status == "done"
    assert parent.completed_at is not None


@pytest.mark.anyio
async def test_finishing_the_last_step_from_a_recommendation_finishes_the_parent(client, db_session):
    user = await _user(db_session)
    parent, (photos,) = await _group(db_session, user, steps=("Get photos",))

    with _signed_in():
        r = await client.post("/api/v1/recommendations/feedback", headers=HEADERS,
                              json={"task_id": str(photos.id), "signal": "done"})

    assert r.status_code == 201
    assert (await _fresh(db_session, parent)).status == "done"


@pytest.mark.anyio
async def test_marking_the_last_step_done_by_voice_finishes_the_parent(client, db_session):
    user = await _user(db_session)
    # The assistant marks its own best pick done; the step's higher priority makes it the pick.
    parent, (photos,) = await _group(db_session, user, steps=("Get photos",), priority=5)
    photos.priority = 1
    await db_session.flush()

    body = {"responseId": "r", "queryResult": {"queryText": "MarkDone",
                                               "intent": {"displayName": "MarkDone"}, "parameters": {}}}
    with _signed_in():
        r = await client.post("/api/v1/assistant/webhook", headers=HEADERS, json=body)

    assert r.status_code == 200 and "Get photos" in r.json()["fulfillmentText"]
    photos, parent = await _fresh(db_session, photos, parent)
    assert photos.status == "done"
    assert parent.status == "done"


@pytest.mark.anyio
async def test_reopening_a_step_reopens_its_finished_parent(client, db_session):
    user = await _user(db_session)
    parent, (photos,) = await _group(db_session, user, steps=("Get photos",))
    await _patch(client, photos, status="done")
    assert (await _fresh(db_session, parent)).status == "done"

    await _patch(client, photos, status="pending")

    parent = await _fresh(db_session, parent)
    assert parent.status == "pending"
    assert parent.completed_at is None


@pytest.mark.anyio
async def test_a_parent_whose_steps_were_all_deleted_is_a_plain_task_again(client, db_session):
    user = await _user(db_session)
    parent, (photos, form) = await _group(db_session, user, steps=("Get photos", "Fill out the form"))

    await _delete(client, photos)
    await _delete(client, form)

    with _signed_in():
        body = (await client.get(f"/api/v1/tasks/{parent.id}", headers=HEADERS)).json()
    assert body["status"] == "pending"
    assert (body["step_count"], body["open_step_count"]) == (0, 0)


@pytest.mark.anyio
async def test_deleting_a_parent_cancels_its_open_steps_and_keeps_finished_ones(client, db_session):
    user = await _user(db_session)
    parent, (photos, form, mail) = await _group(db_session, user)
    await _patch(client, photos, status="done")

    assert (await _delete(client, parent)).status_code == 204

    photos, form, mail = await _fresh(db_session, photos, form, mail)
    assert (photos.status, form.status, mail.status) == ("done", "cancelled", "cancelled")


@pytest.mark.anyio
async def test_finishing_a_parent_finishes_its_open_steps_and_releases_their_pins(client, db_session):
    user = await _user(db_session)
    parent, (photos, form) = await _group(db_session, user, steps=("Get photos", "Fill out the form"))
    swaps = RecommendationSwapRepository(db_session)
    await swaps.create(user.id, rejected_task_id=photos.id, chosen_task_id=form.id, pin=True)
    assert await swaps.active_pin(user.id) is not None

    await _patch(client, parent, status="done")

    photos, form = await _fresh(db_session, photos, form)
    assert (photos.status, form.status) == ("done", "done")
    assert photos.completed_at is not None and form.completed_at is not None
    assert await swaps.active_pin(user.id) is None


@pytest.mark.anyio
async def test_deleting_a_middle_step_keeps_the_last_one_waiting_on_the_first(client, db_session):
    user = await _user(db_session)
    parent, (photos, form, mail) = await _group(db_session, user)

    await _delete(client, form)

    assert await _edges(db_session) == {(mail.id, photos.id, "sequence")}


@pytest.mark.anyio
async def test_only_the_step_the_user_finished_is_learned_from(client, db_session):
    user = await _user(db_session)
    parent, (photos,) = await _group(db_session, user, steps=("Get photos",))

    with patch("app.services.task_service.TaskCompletionService.record_completion",
               new_callable=AsyncMock) as record:
        await _patch(client, photos, status="done")

    assert (await _fresh(db_session, parent)).status == "done"
    assert record.await_count == 1
    assert record.await_args.args[1].id == photos.id


@pytest.mark.anyio
async def test_no_duration_question_for_a_parent(client, db_session):
    user = await _user(db_session)
    parent, _ = await _group(db_session, user, steps=("Get photos",))

    with _signed_in():
        r = await client.get(f"/api/v1/tasks/{parent.id}/duration-prompt", headers=HEADERS)

    assert r.status_code == 200 and r.json()["ask"] is False


@pytest.mark.anyio
async def test_insights_count_the_steps_not_the_group_or_its_parent(client, db_session):
    user = await _user(db_session)
    parent, (photos, form) = await _group(db_session, user, steps=("Get photos", "Fill out the form"))
    await _patch(client, photos, status="done")
    await _patch(client, form, status="done")
    assert (await _fresh(db_session, parent)).status == "done"

    repo = TaskRepository(db_session)
    now = datetime.now(timezone.utc)
    start, end = now - timedelta(days=1), now + timedelta(days=1)
    assert await repo.count_completed_in_range(user.id, start, end) == 2
    assert await repo.count_created_in_range(user.id, start, end) == 1


# ── Creating steps ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_adding_steps_creates_them_in_order_with_the_parents_priority(client, db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Renew passport", priority=1)

    with _signed_in():
        r = await client.post(f"/api/v1/tasks/{parent.id}/steps", headers=HEADERS, json={
            "steps": [{"title": "Get photos"}, {"title": "Fill out the form", "estimated_minutes": 20}],
            "sequential": True,
        })

    assert r.status_code == 201
    body = r.json()
    assert (body["step_count"], body["open_step_count"]) == (2, 2)
    photos, form = body["steps"]
    assert (photos["title"], photos["position"], photos["priority"]) == ("Get photos", 0, 1)
    assert (form["title"], form["position"], form["estimated_minutes"]) == ("Fill out the form", 1, 20)
    assert photos["estimated_minutes"] is not None
    assert form["parent_title"] == "Renew passport"
    assert form["blocked_by"] == [{"id": photos["id"], "title": "Get photos"}]


@pytest.mark.anyio
async def test_steps_cannot_have_steps(client, db_session):
    user = await _user(db_session)
    _, (photos, *_rest) = await _group(db_session, user)

    with _signed_in():
        r = await client.post(f"/api/v1/tasks/{photos.id}/steps", headers=HEADERS,
                              json={"steps": [{"title": "Find a photo booth"}]})

    assert r.status_code == 422


@pytest.mark.anyio
async def test_a_calendar_event_cannot_have_steps(client, db_session):
    user = await _user(db_session)
    meeting = await _task(db_session, user, "Team sync", source="calendar")

    with _signed_in():
        r = await client.post(f"/api/v1/tasks/{meeting.id}/steps", headers=HEADERS,
                              json={"steps": [{"title": "Prepare notes"}]})

    assert r.status_code == 422


@pytest.mark.anyio
async def test_a_task_can_have_at_most_twelve_steps(client, db_session):
    user = await _user(db_session)
    parent = await _task(db_session, user, "Move house")

    with _signed_in():
        full = await client.post(f"/api/v1/tasks/{parent.id}/steps", headers=HEADERS,
                                 json={"steps": [{"title": f"Box {i}", "estimated_minutes": 5} for i in range(12)]})
        over = await client.post(f"/api/v1/tasks/{parent.id}/steps", headers=HEADERS,
                                 json={"steps": [{"title": "One more box", "estimated_minutes": 5}]})

    assert full.status_code == 201
    assert over.status_code == 422


@pytest.mark.anyio
async def test_adding_steps_hands_an_auto_placed_slot_to_the_steps(client, db_session):
    user = await _user(db_session)
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    parent = await _task(db_session, user, "Renew passport", scheduled_start=start,
                         scheduled_end=start + timedelta(minutes=60), auto_scheduled=True)

    with _signed_in():
        r = await client.post(f"/api/v1/tasks/{parent.id}/steps", headers=HEADERS,
                              json={"steps": [{"title": "Get photos", "estimated_minutes": 15}]})

    assert r.status_code == 201
    parent = await _fresh(db_session, parent)
    assert parent.scheduled_start is None and parent.auto_scheduled is False


@pytest.mark.anyio
async def test_a_task_the_user_timed_keeps_its_time_when_steps_are_added(client, db_session):
    user = await _user(db_session)
    start = datetime.now(timezone.utc) + timedelta(hours=1)
    parent = await _task(db_session, user, "Renew passport", scheduled_start=start,
                         scheduled_end=start + timedelta(minutes=60), auto_scheduled=False)

    with _signed_in():
        await client.post(f"/api/v1/tasks/{parent.id}/steps", headers=HEADERS,
                          json={"steps": [{"title": "Get photos", "estimated_minutes": 15}]})

    assert (await _fresh(db_session, parent)).scheduled_start is not None


# ── Joining, moving and leaving a group ───────────────────────────────────────

@pytest.mark.anyio
async def test_an_existing_task_can_join_move_between_and_leave_groups(client, db_session):
    user = await _user(db_session)
    passport, (photos, form) = await _group(db_session, user, steps=("Get photos", "Fill out the form"))
    party, (venue,) = await _group(db_session, user, title="Plan party", steps=("Book venue",))
    booth = await _task(db_session, user, "Book photo booth")

    r = await _patch(client, booth, parent_task_id=str(passport.id))
    assert r.status_code == 200
    assert (r.json()["parent_title"], r.json()["position"]) == ("Renew passport", 2)
    assert await _edges(db_session) == {
        (form.id, photos.id, "sequence"), (booth.id, form.id, "sequence"),
    }

    r = await _patch(client, booth, parent_task_id=str(party.id))
    assert r.status_code == 200 and r.json()["parent_title"] == "Plan party"
    assert await _edges(db_session) == {
        (form.id, photos.id, "sequence"), (booth.id, venue.id, "sequence"),
    }

    r = await _patch(client, booth, parent_task_id=None)
    assert r.status_code == 200
    assert (r.json()["parent_task_id"], r.json()["position"]) == (None, None)
    assert await _edges(db_session) == {(form.id, photos.id, "sequence")}


@pytest.mark.anyio
async def test_joining_at_a_position_reorders_the_group(client, db_session):
    user = await _user(db_session)
    passport, (form, mail) = await _group(db_session, user, steps=("Fill out the form", "Mail it"))
    photos = await _task(db_session, user, "Get photos")

    r = await _patch(client, photos, parent_task_id=str(passport.id), position=0)

    assert r.status_code == 200
    photos, form, mail = await _fresh(db_session, photos, form, mail)
    assert (photos.position, form.position, mail.position) == (0, 1, 2)
    assert await _edges(db_session) == {
        (form.id, photos.id, "sequence"), (mail.id, form.id, "sequence"),
    }


@pytest.mark.anyio
async def test_a_task_with_steps_cannot_become_a_step(client, db_session):
    user = await _user(db_session)
    passport, _ = await _group(db_session, user)
    party, _ = await _group(db_session, user, title="Plan party", steps=("Book venue",))

    r = await _patch(client, party, parent_task_id=str(passport.id))

    assert r.status_code == 422
    assert (await _fresh(db_session, party)).parent_task_id is None


@pytest.mark.anyio
async def test_a_new_task_can_join_a_group_or_bring_steps_but_not_both(client, db_session):
    user = await _user(db_session)
    passport, _ = await _group(db_session, user, steps=("Fill out the form",))

    with _signed_in():
        joined = await client.post("/api/v1/tasks", headers=HEADERS,
                                   json={"title": "Get photos", "parent_task_id": str(passport.id)})
        with_steps = await client.post("/api/v1/tasks", headers=HEADERS, json={
            "title": "Plan party", "steps": [{"title": "Book venue"}, {"title": "Order cake"}],
        })
        both = await client.post("/api/v1/tasks", headers=HEADERS, json={
            "title": "Nope", "parent_task_id": str(passport.id), "steps": [{"title": "x"}],
        })

    assert joined.status_code == 201 and joined.json()["parent_title"] == "Renew passport"
    assert with_steps.status_code == 201 and with_steps.json()["step_count"] == 2
    assert both.status_code == 422
