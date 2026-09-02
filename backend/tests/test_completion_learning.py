"""TIME-316 — what the app learns when you finish something it did not recommend.

The scenario: an opportunity comes up to do a task that wasn't the pick — a better fit for the
user's mood, or they knew something TimeSense didn't. Before this, that was completely invisible.
`recommendation_events` knew what was recommended and when, `tasks` knew a status changed, and
nothing joined them, so the single most informative thing a user does — choosing differently and
being right — taught nothing at all.

It has to stay SILENT (no extra tap, no "why did you do that instead?") and it has to stay MODEST:
a signal inferred from behaviour must never hit as hard as one the user stated outright, because
these signals can only tighten recommendations.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.security import TokenUser
from app.models.recommendation_event import RecommendationEvent
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.recommendation_swap import RecommendationSwap
from app.models.user import User
from app.repositories.recommendation_event_repository import (
    OUTCOME_SUPERSEDED,
    RecommendationEventRepository,
)
from app.repositories.recommendation_swap_repository import RecommendationSwapRepository

USER = TokenUser(uid="uid-cl", email="cl@example.com", role="user", email_verified=True)


def _auth():
    return {"Authorization": "Bearer test-token"}


def _verify(user: TokenUser = USER):
    return patch(
        "app.core.security.firebase_auth.verify_id_token",
        return_value={"uid": user.uid, "email": user.email, "role": user.role,
                      "email_verified": user.email_verified},
    )


async def _task(client, title):
    r = await client.post("/api/v1/tasks", headers=_auth(),
                          json={"title": title, "source": "manual"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


async def _grant_analytics(client):
    r = await client.post("/api/v1/consent/", headers=_auth(),
                          json={"consent_type": "analytics", "granted": True})
    assert r.status_code in (200, 201), r.text


async def _user_row(db_session) -> User:
    return (await db_session.execute(select(User).where(User.firebase_uid == USER.uid))).scalar_one()


async def _show(db_session, user, task_id, *, ago: timedelta = timedelta(minutes=5)):
    """Record that `task_id` was the recommendation on the Now screen `ago` ago."""
    event = await RecommendationEventRepository(db_session).record_impression(
        user_id=user.id, task_id=uuid.UUID(task_id), surface="now", confidence=0.8,
    )
    event.created_at = datetime.now(timezone.utc) - ago
    await db_session.flush()
    return event


async def _complete(client, task_id):
    r = await client.patch(f"/api/v1/tasks/{task_id}", headers=_auth(), json={"status": "done"})
    assert r.status_code == 200, r.text
    return r


async def _swaps(db_session):
    return (await db_session.execute(select(RecommendationSwap))).scalars().all()


# ── Doing what was recommended ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_completing_the_recommended_task_records_done_and_no_swap(client, db_session):
    """`done` has been in POSITIVE_OUTCOMES all along while no client ever sent it — only `agree`
    could ever reach it. Completing IS the strongest form of agreement."""
    with _verify():
        await _grant_analytics(client)
        task_id = await _task(client, "Write the report")
        user = await _user_row(db_session)
        event = await _show(db_session, user, task_id)
        await _complete(client, task_id)

    await db_session.refresh(event)
    assert event.outcome == "done"
    assert await _swaps(db_session) == []


# ── Doing something else ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_completing_a_different_task_records_the_pair(client, db_session):
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended)
        await _complete(client, actually_did)

    rows = await _swaps(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert str(row.rejected_task_id) == recommended
    assert str(row.chosen_task_id) == actually_did
    assert row.context_snapshot["origin"] == "completion"
    assert row.reason is None, "the user never said why; a fabricated reason pollutes _reason_signals"


@pytest.mark.anyio
async def test_the_pair_is_never_pinned(client, db_session):
    """Load-bearing. `active_pin` takes the NEWEST row, so a pinned completion swap would shadow a
    genuine explicit pin for three hours — the user's real "do this instead" silently discarded —
    and would try to recommend a task they have already finished."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended)
        await _complete(client, actually_did)

    rows = await _swaps(db_session)
    assert rows[0].pinned_until is None
    assert await RecommendationSwapRepository(db_session).active_pin(user.id) is None


@pytest.mark.anyio
async def test_the_displaced_recommendation_is_never_marked_rejected(client, db_session):
    """They didn't reject it — they did something else first and may still do it. Inventing a
    `disagree` would suppress a task the user still intends to do."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        event = await _show(db_session, user, recommended)
        await _complete(client, actually_did)

    await db_session.refresh(event)
    assert event.outcome == OUTCOME_SUPERSEDED
    assert event.outcome not in {"disagree", "not_now"}
    feedback = (await db_session.execute(select(RecommendationFeedback))).scalars().all()
    assert feedback == [], "a silent inference must not masquerade as something the user said"


@pytest.mark.anyio
async def test_a_burst_of_completions_cannot_invent_a_preference(client, db_session):
    """Catching up by marking five things done must not pair all five against the same
    recommendation and manufacture a preference out of one bout of housekeeping."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended)
        for i in range(5):
            await _complete(client, await _task(client, f"Chore {i}"))

    assert len(await _swaps(db_session)) == 1, "one recommendation can teach at most once"


# ── Bounds ────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_a_stale_recommendation_teaches_nothing(client, db_session):
    """A 9am pick paired with an afternoon completion reflects nothing the user thought about."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended, ago=timedelta(hours=6))
        await _complete(client, actually_did)

    assert await _swaps(db_session) == []


@pytest.mark.anyio
async def test_nothing_recommended_means_nothing_learned(client, db_session):
    with _verify():
        await _grant_analytics(client)
        actually_did = await _task(client, "Buy groceries")
        await _complete(client, actually_did)

    assert await _swaps(db_session) == []


@pytest.mark.anyio
async def test_without_analytics_consent_nothing_is_recorded(client, db_session):
    """A swap derived from an impression must be gated exactly as the impression was, or the gate
    means nothing."""
    with _verify():
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended)
        await _complete(client, actually_did)

    assert await _swaps(db_session) == []


@pytest.mark.anyio
async def test_the_same_pair_is_not_recorded_twice(client, db_session):
    """The user can say it explicitly AND then complete the task. That is one preference."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        await client.post("/api/v1/recommendations/swap", headers=_auth(),
                          json={"rejected_task_id": recommended, "chosen_task_id": actually_did,
                                "reason": "not_priority"})
        user = await _user_row(db_session)
        await _show(db_session, user, recommended)
        await _complete(client, actually_did)

    assert len(await _swaps(db_session)) == 1


@pytest.mark.anyio
async def test_completing_a_pinned_task_releases_the_pin(client, db_session):
    """A pin means "do this next". Doing it answers the question. Previously only the feedback
    endpoint released it, so completing from Now or Today left it overriding the engine for hours."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        chosen = await _task(client, "Buy groceries")
        await client.post("/api/v1/recommendations/swap", headers=_auth(),
                          json={"rejected_task_id": recommended, "chosen_task_id": chosen,
                                "reason": "wrong_time"})
        user = await _user_row(db_session)
        assert await RecommendationSwapRepository(db_session).active_pin(user.id) is not None
        await _complete(client, chosen)

    assert await RecommendationSwapRepository(db_session).active_pin(user.id) is None


@pytest.mark.anyio
async def test_a_learning_failure_never_costs_the_user_their_completion(client, db_session):
    """The task is done either way. Losing a signal beats losing their work."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended)
        with patch(
            "app.services.task_completion_service.RecommendationSwapRepository.create",
            side_effect=RuntimeError("boom"),
        ):
            r = await _complete(client, actually_did)

    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["completed_at"] is not None


# ── How much a silent signal is allowed to be worth ───────────────────────────
#
# These matter because swap signals can only TIGHTEN recommendations (a -18 bonus for the preferred
# category, a +22 penalty for the one swapped away from). The project rule is that per-user
# adjustments may relax a requirement but never tighten one on thin evidence — and an explicit swap
# took two deliberate multi-tap interactions to reach the threshold, while completions would
# otherwise get there on two Done swipes in one afternoon.

async def _swap_row(db_session, user, *, chosen_category, origin, hour=10):
    from app.models.recommendation_swap import RecommendationSwap

    db_session.add(RecommendationSwap(
        user_id=user.id, rejected_task_id=None, chosen_task_id=None, reason=None,
        pinned_until=None,
        context_snapshot={"local_hour": hour, "chosen_category": chosen_category,
                          "rejected_category": None, "origin": origin},
    ))
    await db_session.flush()


async def _preferred(db_session, user):
    from app.services.recommendation.feedback.build_summary import _swap_signals

    since = datetime.now(timezone.utc) - timedelta(days=30)
    signals = await _swap_signals(db_session, user.id, since, "morning", "UTC")
    return signals["preferred_categories_now"]


@pytest.mark.anyio
async def test_two_silent_completions_alone_do_not_move_scoring(client, db_session):
    with _verify():
        await _task(client, "seed")
        user = await _user_row(db_session)
        for _ in range(2):
            await _swap_row(db_session, user, chosen_category="errand", origin="completion")

    assert "errand" not in await _preferred(db_session, user)


@pytest.mark.anyio
async def test_two_deliberate_swaps_still_move_scoring(client, db_session):
    """The existing behaviour must be untouched — this change may only make the NEW signal weaker."""
    with _verify():
        await _task(client, "seed")
        user = await _user_row(db_session)
        for _ in range(2):
            await _swap_row(db_session, user, chosen_category="errand", origin="explicit")

    assert "errand" in await _preferred(db_session, user)


@pytest.mark.anyio
async def test_enough_silent_completions_eventually_count(client, db_session):
    """Weaker, not ignored. Sustained behaviour is still evidence."""
    with _verify():
        await _task(client, "seed")
        user = await _user_row(db_session)
        for _ in range(4):
            await _swap_row(db_session, user, chosen_category="errand", origin="completion")

    assert "errand" in await _preferred(db_session, user)


@pytest.mark.anyio
async def test_a_completion_corroborates_a_deliberate_swap(client, db_session):
    with _verify():
        await _task(client, "seed")
        user = await _user_row(db_session)
        await _swap_row(db_session, user, chosen_category="errand", origin="explicit")
        await _swap_row(db_session, user, chosen_category="errand", origin="completion")
        await _swap_row(db_session, user, chosen_category="errand", origin="completion")

    assert "errand" in await _preferred(db_session, user)


@pytest.mark.anyio
async def test_rows_predating_origin_are_treated_as_deliberate(client, db_session):
    """Swaps written before TIME-316 have no `origin`; every one of them was explicit by
    definition, so they must not be silently devalued."""
    with _verify():
        await _task(client, "seed")
        user = await _user_row(db_session)
        for _ in range(2):
            await _swap_row(db_session, user, chosen_category="errand", origin=None)

    assert "errand" in await _preferred(db_session, user)
