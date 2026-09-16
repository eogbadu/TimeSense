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


# The part-of-day boundaries the pairing rule uses (time_service.part_of_day). The test user has no
# timezone, so these are UTC hours.
_PART_BOUNDARIES = (5, 8, 11, 14, 17, 21)


def _part_start(moment: datetime) -> datetime:
    """The start of the part of day `moment` falls in."""
    started = [h for h in _PART_BOUNDARIES if h <= moment.hour]
    if not started:  # before 05:00 — night began at 21:00 yesterday
        return moment.replace(hour=21, minute=0, second=0, microsecond=0) - timedelta(days=1)
    return moment.replace(hour=started[-1], minute=0, second=0, microsecond=0)


def _fixed_now(hour: int, minute: int = 2) -> datetime:
    """Today at `hour:minute` UTC."""
    return datetime.now(timezone.utc).replace(hour=hour, minute=minute, second=0, microsecond=0)


def _clock(fixed: datetime):
    """Pin the clock the completion service reads. It takes no `now` from the route, so this is the
    only way to choose the hour a completion is judged at (TIME-332)."""

    class _Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is not None else fixed.replace(tzinfo=None)

    return patch("app.services.task_completion_service.datetime", _Fixed)


async def _show(db_session, user, task_id, *, ago: timedelta = timedelta(minutes=5),
                now: datetime | None = None, same_part: bool = True):
    """Record that `task_id` was the recommendation on the Now screen `ago` ago.

    The impression is kept inside the CURRENT part of day by default. A pair only teaches when the
    recommendation and the completion share one, so a flat five minutes back landed in the previous
    part whenever the suite ran in the first five minutes after 05:00, 08:00, 11:00, 14:00, 17:00 or
    21:00 — five minutes in every three hours where these tests failed (TIME-332). Pass
    `same_part=False` for a deliberately stale impression.
    """
    now = now or datetime.now(timezone.utc)
    shown_at = now - ago
    if same_part:
        shown_at = max(shown_at, _part_start(now) + timedelta(seconds=1))
    event = await RecommendationEventRepository(db_session).record_impression(
        user_id=user.id, task_id=uuid.UUID(task_id), surface="now", confidence=0.8,
    )
    event.created_at = shown_at
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


@pytest.mark.anyio
@pytest.mark.parametrize("hour", _PART_BOUNDARIES)
async def test_the_pair_is_recorded_just_after_a_part_of_day_boundary(client, db_session, hour):
    """TIME-332: two minutes past a boundary, a recommendation dated five minutes back sat in the
    previous part of day, so nothing was learned and these tests failed."""
    fixed = _fixed_now(hour)
    with _verify(), _clock(fixed):
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended, now=fixed)
        await _complete(client, actually_did)

    rows = await _swaps(db_session)
    assert len(rows) == 1
    assert str(rows[0].rejected_task_id) == recommended
    assert str(rows[0].chosen_task_id) == actually_did


# ── Bounds ────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_a_stale_recommendation_teaches_nothing(client, db_session):
    """A 9am pick paired with an afternoon completion reflects nothing the user thought about."""
    with _verify():
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        await _show(db_session, user, recommended, ago=timedelta(hours=6), same_part=False)
        await _complete(client, actually_did)

    assert await _swaps(db_session) == []


@pytest.mark.anyio
async def test_a_recommendation_from_the_previous_part_of_day_teaches_nothing(client, db_session):
    """`_swap_signals` buckets by part of day, so a pair straddling a boundary would be filed under a
    context that never existed. Ten minutes back is well inside the 90-minute lookback, so this
    isolates the boundary rule — and it is the exact shape that used to break the tests above
    whenever the suite ran just after a boundary (TIME-332)."""
    fixed = _fixed_now(14)  # 14:02 is afternoon; ten minutes earlier is still midday
    with _verify(), _clock(fixed):
        await _grant_analytics(client)
        recommended = await _task(client, "Write the report")
        actually_did = await _task(client, "Buy groceries")
        user = await _user_row(db_session)
        event = await _show(db_session, user, recommended, ago=timedelta(minutes=10),
                            now=fixed, same_part=False)
        await _complete(client, actually_did)

    assert await _swaps(db_session) == []
    await db_session.refresh(event)
    # The impression WAS found and closed; only the pairing stopped, at the part-of-day check.
    assert event.outcome == OUTCOME_SUPERSEDED


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
