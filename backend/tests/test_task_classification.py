"""TIME-285 — every task gets a library type and a difficulty, on every creation path.

The property under test is coverage, not accuracy: tasks are created from capture, manual entry and
the Notion / email / Slack / Teams / calendar imports, and any path that forgot to classify would
quietly produce rows that fall back to the catch-all forever — reintroducing exactly the bug
TIME-284 set out to remove.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.security import TokenUser
from app.services.task_library import (
    GENERAL_KEY,
    VALID_DIFFICULTIES,
    classify,
    get_type,
    resolve_classification,
)

MOCK_USER = TokenUser(uid="uid-cls-1", email="cls@example.com", role="user", email_verified=True)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _mock_verify(user: TokenUser = MOCK_USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


# ── resolve_classification: what the LLM is and isn't allowed to influence ────────────────


def test_llm_type_is_used_when_it_names_a_real_library_type():
    task_type, difficulty = resolve_classification("Sort out the thing", "code_review", None)
    assert task_type == "code_review"
    # The chosen type's own difficulty is adopted, not the keyword match's.
    assert difficulty == get_type("code_review").difficulty


def test_an_invented_llm_type_is_discarded_in_favour_of_the_matcher():
    """An invented key must never reach the DB: TIME-286 keys learned durations on this value, so a
    hallucinated type would become a private learning bucket that answers for nothing real."""
    task_type, difficulty = resolve_classification("Buy groceries", "shopping_supreme", None)
    assert task_type == classify("Buy groceries").key
    assert task_type != "shopping_supreme"
    assert difficulty in VALID_DIFFICULTIES


def test_an_unrecognised_difficulty_falls_back_to_the_librarys_own():
    task_type, difficulty = resolve_classification("Review Tom's PR", None, "extremely hard")
    assert difficulty == get_type(task_type).difficulty
    assert difficulty in VALID_DIFFICULTIES


def test_a_valid_llm_difficulty_overrides_the_library_default():
    """The library value is a baseline; the model can see that *this* instance is harder."""
    default = classify("Reply to Sarah's email").difficulty
    _, difficulty = resolve_classification("Reply to Sarah's email", None, "deep")
    assert difficulty == "deep"
    assert default != "deep"        # otherwise the test proves nothing


def test_classification_never_returns_empty_values():
    for title in ["", "   ", "asdkjhasd", "🙂", "a" * 500]:
        task_type, difficulty = resolve_classification(title, None, None)
        assert task_type
        assert difficulty in VALID_DIFFICULTIES


# ── the creation paths ───────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_manually_created_task_is_classified(client):
    with _mock_verify():
        r = await client.post(
            "/api/v1/tasks", headers=_auth_headers(),
            json={"title": "Book dentist appointment", "source": "manual"},
        )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["task_type"] == "appt_dentist"
    assert body["difficulty"] in VALID_DIFFICULTIES


@pytest.mark.anyio
async def test_an_explicit_classification_from_the_client_is_respected(client):
    """A user correcting a wrong guess must stick — it's a learning signal, not a display tweak."""
    with _mock_verify():
        r = await client.post(
            "/api/v1/tasks", headers=_auth_headers(),
            json={"title": "Buy groceries", "source": "manual",
                  "task_type": "code_review", "difficulty": "deep"},
        )
    assert r.status_code in (200, 201), r.text
    assert r.json()["task_type"] == "code_review"
    assert r.json()["difficulty"] == "deep"


@pytest.mark.anyio
async def test_repository_classifies_imports_that_never_pass_a_type(db_session):
    """Notion / email / Slack / Teams / calendar imports call the repository directly, without any
    classification of their own. They must still come out classified."""
    from app.repositories.task_repository import TaskRepository
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    repo = TaskRepository(db_session)

    for title, source in [
        ("Review the Q3 pull request", "notion"),
        ("Reply to the vendor email", "email"),
        ("Fix the login bug", "slack"),
        ("Client meeting with Acme", "teams"),
    ]:
        task = await repo.create(user_id=user.id, title=title, source=source)
        assert task.task_type, f"{source} import produced an unclassified task"
        assert task.difficulty in VALID_DIFFICULTIES
        assert task.task_type != GENERAL_KEY, f"{title!r} should not fall to the catch-all"


@pytest.mark.anyio
async def test_partial_classification_is_completed_not_overwritten(db_session):
    """A caller supplying only one of the two fields keeps it, and the other gets filled in."""
    from app.repositories.task_repository import TaskRepository
    from app.services.user_service import UserService

    user, _ = await UserService(db_session).get_or_create_user(MOCK_USER.uid, MOCK_USER.email)
    repo = TaskRepository(db_session)

    only_type = await repo.create(user_id=user.id, title="Buy groceries", task_type="code_review")
    assert only_type.task_type == "code_review"
    assert only_type.difficulty in VALID_DIFFICULTIES

    only_difficulty = await repo.create(user_id=user.id, title="Buy groceries", difficulty="deep")
    assert only_difficulty.difficulty == "deep"
    assert only_difficulty.task_type == classify("Buy groceries").key


@pytest.mark.anyio
async def test_capture_classifies_without_a_working_llm(client):
    """Capture must classify from the deterministic matcher alone — the LLM is best-effort and the
    parse path already falls back when it fails."""
    with _mock_verify():
        r = await client.post(
            "/api/v1/capture", headers=_auth_headers(),
            json={"raw_input": "Go for a run tomorrow morning", "user_timezone": "UTC"},
        )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["task_type"], "capture produced an unclassified task"
    assert body["difficulty"] in VALID_DIFFICULTIES
