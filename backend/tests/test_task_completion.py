"""TIME-316 — `tasks.completed_at`.

Until now the only record of when a task was finished was `updated_at`, which any later edit moves;
`count_completed_in_range` apologised for that in its own docstring. Knowing what was recommended
when a task was actually completed needs an instant that doesn't drift, so these tests pin the one
property that matters: the timestamp is stamped on the pending→done EDGE and never moves again.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.security import TokenUser
from app.models.task import Task

USER = TokenUser(uid="uid-completion", email="completion@example.com", role="user",
                 email_verified=True)


def _auth():
    return {"Authorization": "Bearer test-token"}


def _verify(user: TokenUser = USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


async def _task(client, title="Write the report"):
    r = await client.post("/api/v1/tasks", headers=_auth(),
                          json={"title": title, "source": "manual"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def _completed_at(db_session, task_id) -> datetime | None:
    row = (await db_session.execute(select(Task).where(Task.id == uuid.UUID(task_id)))).scalar_one()
    await db_session.refresh(row)
    return row.completed_at


@pytest.mark.anyio
async def test_completing_a_task_stamps_the_instant(client, db_session):
    with _verify():
        task_id = await _task(client)
        r = await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(),
                               json={"status": "done"})
    assert r.status_code == 200, r.text
    assert r.json()["completed_at"] is not None
    assert await _completed_at(db_session, task_id) is not None


@pytest.mark.anyio
async def test_a_pending_task_has_no_completion_instant(client, db_session):
    with _verify():
        task_id = await _task(client)
        r = await client.get(f"/api/v1/tasks/{task_id}", headers=_auth())
    assert r.status_code == 200
    assert r.json()["completed_at"] is None


@pytest.mark.anyio
async def test_marking_done_twice_does_not_move_the_instant(client, db_session):
    """Today's row circle re-sends `done` on an already-done task, so this is a real path, not a
    hypothetical one."""
    with _verify():
        task_id = await _task(client)
        first = (await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(),
                                    json={"status": "done"})).json()["completed_at"]
        second = (await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(),
                                     json={"status": "done"})).json()["completed_at"]
    assert first is not None
    assert first == second


@pytest.mark.anyio
async def test_editing_a_done_task_does_not_move_the_instant(client):
    """The exact lossiness that made `updated_at` unusable: renaming a task a week later must not
    make it look like it was finished a week later."""
    with _verify():
        task_id = await _task(client)
        done = (await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(),
                                   json={"status": "done"})).json()["completed_at"]
        edited = (await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(),
                                     json={"title": "Write the report (final)"})).json()
    assert edited["completed_at"] == done
    assert edited["title"] == "Write the report (final)"


@pytest.mark.anyio
async def test_completed_at_is_not_client_settable(client):
    """It is derived. A client claiming its own completion instant would defeat the point."""
    forged = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    with _verify():
        task_id = await _task(client)
        r = await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(),
                               json={"status": "done", "completed_at": forged})
    assert r.status_code == 200
    stamped = datetime.fromisoformat(r.json()["completed_at"])
    # SQLite returns this naive where Postgres returns it aware; the assertion is about the VALUE,
    # not the representation (see known_issues.md on the two backends' schemas).
    if stamped.tzinfo is None:
        stamped = stamped.replace(tzinfo=timezone.utc)
    assert (datetime.now(timezone.utc) - stamped) < timedelta(minutes=5)


@pytest.mark.anyio
async def test_legacy_rows_still_count_as_completed(client, db_session):
    """Rows finished before the column existed keep their NULL and fall back to `updated_at`, so
    historic counts don't silently drop to zero on deploy."""
    from app.repositories.task_repository import TaskRepository

    with _verify():
        task_id = await _task(client)
        await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(), json={"status": "done"})

    row = (await db_session.execute(select(Task).where(Task.id == uuid.UUID(task_id)))).scalar_one()
    row.completed_at = None            # simulate a pre-migration row
    await db_session.flush()

    now = datetime.now(timezone.utc)
    count = await TaskRepository(db_session).count_completed_in_range(
        row.user_id, now - timedelta(days=1), now + timedelta(days=1)
    )
    assert count == 1
