"""TIME-311 — tasks created before classification existed still carry the old estimates.

The user reported "tasks always estimated at 23 mins regardless of task". TIME-286 and TIME-305 fixed
how NEW estimates are derived and never revisited existing rows, so a task captured earlier still
shows 23 minutes on a screen that has otherwise been fixed.
"""
import uuid

import pytest

from app.models.task import Task
from app.services.task_backfill import TaskBackfillService, stated_a_duration
from app.services.task_service import TaskService
from app.services.user_service import UserService


# --- did the user say how long? ---------------------------------------------------------------------
# There is no column recording where an estimate came from, and for rows this old there never was
# one. The capture text is the only evidence, and it is good evidence.

@pytest.mark.parametrize("text", [
    "Call mum for 30 minutes",
    "write the report, 2 hrs",
    "take a half an hour walk",
    "30m standup",
    "block an hour for this",
    "review PR 45 min",
    "a 10-15 minutes task",
])
def test_stated_durations_are_recognised(text):
    assert stated_a_duration(text) is True


@pytest.mark.parametrize("text", [
    "quick call",
    "Solve 10+ Leetcode problems daily for a month",
    "meet Sam at 3pm",
    "Finish the quarterly report",
    "",
    None,
])
def test_unstated_durations_are_not_invented(text):
    assert stated_a_duration(text) is False


# --- the backfill itself ------------------------------------------------------------------------------

async def _user(db, suffix: str):
    user, _ = await UserService(db).get_or_create_user(f"uid-bf-{suffix}", f"bf{suffix}@example.com")
    return user


@pytest.mark.anyio
async def test_a_legacy_task_gains_a_type_and_a_fresh_estimate(db_session):
    user = await _user(db_session, "1")
    task = Task(user_id=user.id, title="Go to the dentist", status="pending", priority=3,
                task_type=None, estimated_minutes=23, raw_input="Go to the dentist")
    db_session.add(task)
    await db_session.flush()

    await TaskBackfillService(db_session).backfill(user.id, [task])

    assert task.task_type is not None
    assert task.task_type != "general", "a classifiable title should not stay in the catch-all"
    assert task.estimated_minutes != 23, "the pre-classification estimate survived"


@pytest.mark.anyio
async def test_a_stated_duration_survives_reestimation(db_session):
    """A duration the user spelled out is an instruction, not a default."""
    user = await _user(db_session, "2")
    task = Task(user_id=user.id, title="Call mum", status="pending", priority=3,
                task_type=None, estimated_minutes=45, raw_input="Call mum for 45 minutes")
    db_session.add(task)
    await db_session.flush()

    await TaskBackfillService(db_session).backfill(user.id, [task])

    assert task.task_type is not None, "it should still be classified"
    assert task.estimated_minutes == 45, "the user's own duration was overwritten"


@pytest.mark.anyio
async def test_a_task_that_already_has_a_type_is_left_alone(db_session):
    """Only pre-classification rows are touched — a hand-set type and its estimate are not revisited."""
    user = await _user(db_session, "3")
    task = Task(user_id=user.id, title="Go to the dentist", status="pending", priority=3,
                task_type="dentist_appointment", estimated_minutes=99, raw_input="dentist")
    db_session.add(task)
    await db_session.flush()

    await TaskBackfillService(db_session).backfill(user.id, [task])

    assert task.task_type == "dentist_appointment"
    assert task.estimated_minutes == 99


@pytest.mark.anyio
async def test_an_unclassifiable_title_still_gets_a_type_rather_than_staying_null(db_session):
    """The catch-all is a real answer — leaving task_type null means re-doing this work every read."""
    user = await _user(db_session, "4")
    task = Task(user_id=user.id, title="Zzzz qqqq", status="pending", priority=3,
                task_type=None, estimated_minutes=23, raw_input="Zzzz qqqq")
    db_session.add(task)
    await db_session.flush()

    await TaskBackfillService(db_session).backfill(user.id, [task])
    assert task.task_type == "general"


@pytest.mark.anyio
async def test_backfill_is_idempotent(db_session):
    user = await _user(db_session, "5")
    task = Task(user_id=user.id, title="Go for a run", status="pending", priority=3,
                task_type=None, estimated_minutes=23, raw_input="Go for a run")
    db_session.add(task)
    await db_session.flush()

    svc = TaskBackfillService(db_session)
    await svc.backfill(user.id, [task])
    first_type, first_minutes = task.task_type, task.estimated_minutes
    await svc.backfill(user.id, [task])

    assert (task.task_type, task.estimated_minutes) == (first_type, first_minutes)


@pytest.mark.anyio
async def test_tasks_sharing_a_type_are_estimated_once(db_session):
    """Cost scales with DISTINCT types, not with the number of tasks — reading a long list must not
    become one query per row."""
    user = await _user(db_session, "6")
    tasks = [
        Task(user_id=user.id, title="Go for a run", status="pending", priority=3,
             task_type=None, estimated_minutes=23, raw_input=f"run {i}")
        for i in range(5)
    ]
    db_session.add_all(tasks)
    await db_session.flush()

    calls = {"n": 0}
    svc = TaskBackfillService(db_session)
    original = svc._estimator.estimate

    async def counting(*args, **kwargs):
        calls["n"] += 1
        return await original(*args, **kwargs)

    svc._estimator.estimate = counting
    await svc.backfill(user.id, tasks)

    assert calls["n"] == 1, f"estimated {calls['n']} times for one type across 5 tasks"
    assert all(t.task_type == tasks[0].task_type for t in tasks)


@pytest.mark.anyio
async def test_reading_a_task_backfills_it(db_session):
    """The 'on read' part of the requirement — no bulk migration, nothing rewritten until looked at."""
    user = await _user(db_session, "7")
    task = Task(user_id=user.id, title="Go to the dentist", status="pending", priority=3,
                task_type=None, estimated_minutes=23, raw_input="Go to the dentist")
    db_session.add(task)
    await db_session.flush()

    fetched = await TaskService(db_session).get_task(task.id, user.id)
    assert fetched.task_type is not None
    assert fetched.estimated_minutes != 23


@pytest.mark.anyio
async def test_listing_tasks_backfills_them(db_session):
    user = await _user(db_session, "8")
    db_session.add(Task(user_id=user.id, title="Go to the dentist", status="pending", priority=3,
                        task_type=None, estimated_minutes=23, raw_input="dentist"))
    await db_session.flush()

    listed = await TaskService(db_session).list_tasks(user.id)
    assert all(t.task_type is not None for t in listed)


@pytest.mark.anyio
async def test_an_empty_batch_does_no_work(db_session):
    assert await TaskBackfillService(db_session).backfill(uuid.uuid4(), []) == []


# --- when NOT to touch the number ---------------------------------------------------------------------
# Classifying a legacy row is pure gain. Overwriting its estimate is not: the whole complaint is that
# the app put wrong durations on tasks, and replacing a duration someone chose is the same failure
# wearing different clothes. The bar is positive evidence the estimate was derived.

@pytest.mark.anyio
async def test_an_estimate_set_through_the_api_is_not_overwritten(db_session):
    """No raw_input means it did not come from capture — most likely the user set it in the app.
    Absence of evidence is not evidence it was derived.

    Caught by test_suggested_slot, which asserted a 60-minute task keeps its 60 minutes."""
    user = await _user(db_session, "9")
    task = Task(user_id=user.id, title="Write proposal", status="pending", priority=2,
                task_type=None, estimated_minutes=60, raw_input=None)
    db_session.add(task)
    await db_session.flush()

    await TaskBackfillService(db_session).backfill(user.id, [task])

    assert task.estimated_minutes == 60, "an API-set estimate was overwritten"
    assert task.task_type is not None, "it should still be classified"


@pytest.mark.anyio
async def test_a_missing_estimate_is_always_filled_in(db_session):
    """Nothing to lose, so no evidence is needed."""
    user = await _user(db_session, "10")
    task = Task(user_id=user.id, title="Go to the dentist", status="pending", priority=3,
                task_type=None, estimated_minutes=None, raw_input=None)
    db_session.add(task)
    await db_session.flush()

    await TaskBackfillService(db_session).backfill(user.id, [task])
    assert task.estimated_minutes is not None


@pytest.mark.anyio
async def test_a_captured_task_with_no_stated_duration_is_reestimated(db_session):
    """Where the "everything takes 23 minutes" rows actually live — capture always records
    raw_input, so these are identifiable."""
    user = await _user(db_session, "11")
    task = Task(user_id=user.id, title="Go to the dentist", status="pending", priority=3,
                task_type=None, estimated_minutes=23,
                raw_input="dentist appointment next week")
    db_session.add(task)
    await db_session.flush()

    await TaskBackfillService(db_session).backfill(user.id, [task])
    assert task.estimated_minutes != 23
