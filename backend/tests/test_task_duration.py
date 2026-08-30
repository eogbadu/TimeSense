"""Tests for the task duration estimator (TIME-082, rebuilt in TIME-286)."""
import pytest

from app.services.task_duration import DEFAULT_DURATIONS, infer_category, seed_duration
from app.services.task_duration_service import TaskDurationEstimator
from app.services.task_library import classify, get_type


def test_infer_category():
    assert infer_category("Call the dentist") == "appointment"   # appointment beats call
    assert infer_category("Call mom") == "call"
    assert infer_category("Go to Home Depot") == "shopping"
    assert infer_category("Reply to Sarah's email") == "email"
    assert infer_category("Clean the garage") == "chore"
    assert infer_category("Morning run") == "exercise"
    assert infer_category("Ponder the universe") == "general"


def test_seed_duration_defaults():
    assert seed_duration("call") == DEFAULT_DURATIONS["call"]
    assert seed_duration("nonsense") == DEFAULT_DURATIONS["general"]


@pytest.mark.anyio
async def test_estimate_uses_seed_then_learned(db_session):
    import uuid
    from app.services.user_service import UserService
    from app.core.security import TokenUser

    tu = TokenUser(uid="dur-1", email="dur@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    # Library baseline first (no learning yet). Keyed on the library TYPE since TIME-286.
    baseline = get_type("shop_groceries").typical_minutes
    minutes, task_type = await est.estimate(user.id, "Buy groceries")
    assert task_type == "shop_groceries"
    assert minutes == baseline

    # Teach it that this user's grocery runs go long; the estimate moves toward that, but is held
    # back by the baseline until there's more evidence.
    await est.record_actual(user.id, "Buy groceries", 90)
    learned, _ = await est.estimate(user.id, "Grocery shopping at Aldi")   # same type
    assert baseline < learned < 90


@pytest.mark.anyio
async def test_capture_fills_estimate_from_lookup(client, db_session):
    """A captured task with no LLM estimate still gets a duration from the lookup table."""
    from unittest.mock import patch

    tu_claims = {"uid": "dur-2", "email": "dur2@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=tu_claims):
        r = await client.post(
            "/api/v1/capture",
            headers={"Authorization": "Bearer t"},
            json={"raw_input": "Call mom"},  # LLM unavailable in tests → fallback path
        )
    assert r.status_code == 201
    assert r.json()["estimated_minutes"] == get_type(classify("Call mom").key).typical_minutes


@pytest.mark.anyio
async def test_duration_prompt_and_feedback_learns(client, db_session):
    """During the learning period /duration-prompt asks; feedback teaches and eventually stops asking."""
    from unittest.mock import patch

    baseline = get_type("shop_groceries").typical_minutes
    claims = {"uid": "dur-3", "email": "dur3@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=claims):
        # capture a task (shopping) → gets seed estimate
        r = await client.post("/api/v1/capture", headers={"Authorization": "Bearer t"},
                              json={"raw_input": "Buy groceries"})
        task_id = r.json()["id"]

        # prompt should ask (nothing learned yet)
        p = await client.get(f"/api/v1/tasks/{task_id}/duration-prompt", headers={"Authorization": "Bearer t"})
        assert p.status_code == 200
        assert p.json()["ask"] is True
        assert p.json()["task_type"] == "shop_groceries"
        assert p.json()["category"] == "shop_groceries"   # legacy field name, same value

        # give feedback: it took 90 min → learned estimate moves up
        f = await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                              headers={"Authorization": "Bearer t"}, json={"actual_minutes": 90})
        assert f.status_code == 200
        assert f.json()["task_type"] == "shop_groceries"
        assert f.json()["estimated_minutes"] > baseline

        # after enough observations, it stops asking
        for _ in range(5):
            await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                              headers={"Authorization": "Bearer t"}, json={"actual_minutes": 90})
        p2 = await client.get(f"/api/v1/tasks/{task_id}/duration-prompt", headers={"Authorization": "Bearer t"})
        assert p2.json()["ask"] is False


@pytest.mark.anyio
async def test_working_hours_preference_roundtrip(client, db_session):
    from unittest.mock import patch
    claims = {"uid": "wh-1", "email": "wh@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=claims):
        # default 8–21
        me = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer t"})
        prefs = me.json()["preferences"]
        assert prefs["work_start_hour"] == 8 and prefs["work_end_hour"] == 21
        # update
        r = await client.patch("/api/v1/users/me/preferences", headers={"Authorization": "Bearer t"},
                               json={"work_start_hour": 9, "work_end_hour": 18})
        assert r.status_code == 200
        assert r.json()["work_start_hour"] == 9 and r.json()["work_end_hour"] == 18
        # invalid: end <= start
        bad = await client.patch("/api/v1/users/me/preferences", headers={"Authorization": "Bearer t"},
                                 json={"work_start_hour": 20, "work_end_hour": 8})
        assert bad.status_code == 422


# ── TIME-286: the "everything takes 23 minutes" regression ───────────────────────────────


@pytest.mark.anyio
async def test_the_23_minute_sequence_no_longer_contaminates_unrelated_tasks(db_session):
    """The exact reported bug, reproduced and then shown fixed.

    How it happened: `infer_category` sent most real titles to the catch-all "general" bucket, the
    learned value was stored per bucket, and the iOS prompt offered only ~15 / ~30 / ~1 hour. Feed
    15, 30, 30 into the old EWMA (alpha 0.3) and you get 15 -> 20 -> 23 exactly. From then on EVERY
    unmatched task read 23 minutes.
    """
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    # 1. The old code path still demonstrates the arithmetic that produced 23.
    old_estimate = 15
    for observation in (30, 30):
        old_estimate = round(old_estimate * 0.7 + observation * 0.3)
    assert old_estimate == 23, "the reported number came from this sequence"

    # ...and the old bucketing is what made it universal.
    assert infer_category("Ponder the universe") == "general"
    assert infer_category("Sort out the thing") == "general"

    # 2. The new path: feed the same answers, then check unrelated tasks are untouched.
    tu = TokenUser(uid="dur-23", email="dur23@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    for answer in (15, 30, 30):
        await est.record_actual(user.id, "Reply to Sarah's email", answer)

    unrelated = [
        "Book dentist appointment", "Go for a run", "Clean the kitchen",
        "Deploy the new release", "Buy groceries", "Call mum",
    ]
    for title in unrelated:
        minutes, task_type = await est.estimate(user.id, title)
        assert minutes == get_type(task_type).typical_minutes, (
            f"{title!r} was contaminated by an unrelated type's learning"
        )
        assert minutes != 23 or get_type(task_type).typical_minutes == 23

    # And the type that WAS taught did move — learning still works, it's just contained.
    email_minutes, email_type = await est.estimate(user.id, "Reply to Sarah's email")
    assert email_type == classify("Reply to Sarah's email").key
    assert email_minutes != get_type(email_type).typical_minutes


@pytest.mark.anyio
async def test_a_single_observation_cannot_own_the_estimate(db_session):
    """The other half of the fix. The old code seeded the estimate to the FIRST observation, so one
    tap on a coarse button became the answer outright. Now it is shrunk toward the baseline."""
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-blend", email="blend@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    baseline = get_type("shop_groceries").typical_minutes
    await est.record_actual(user.id, "Buy groceries", 5)      # an implausible one-off

    after_one, _ = await est.estimate(user.id, "Buy groceries")
    assert after_one < baseline, "the observation should still pull the estimate down"
    assert after_one > 5, "but one observation must not become the estimate outright"

    # Consistent evidence keeps winning ground. Convergence is asymptotic by design (see _blend),
    # so this checks the direction and magnitude of travel, not an exact landing point.
    for _ in range(12):
        await est.record_actual(user.id, "Buy groceries", 5)
    after_many, _ = await est.estimate(user.id, "Buy groceries")
    assert after_many < after_one
    travelled = (baseline - after_many) / (baseline - 5)
    assert travelled > 0.75, f"after 13 observations the estimate had only moved {travelled:.0%}"


@pytest.mark.anyio
async def test_unclassified_tasks_are_never_learned_against(db_session):
    """The structural guard. An unclassified task teaches nothing transferable, and letting the
    catch-all accumulate is precisely how one number came to answer for everything."""
    from app.core.security import TokenUser
    from app.services.task_library import GENERAL_KEY
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-gen", email="gen@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    unclassifiable = "Zorble the frobnicator"
    assert classify(unclassifiable).key == GENERAL_KEY

    for _ in range(10):
        await est.record_actual(user.id, unclassifiable, 5)

    minutes, task_type = await est.estimate(user.id, unclassifiable)
    assert task_type == GENERAL_KEY
    assert minutes == get_type(GENERAL_KEY).typical_minutes, "the catch-all must never learn"

    # And it is never prompted about, since there is nothing useful to learn.
    ask, _ = await est.should_ask(user.id, unclassifiable)
    assert ask is False


@pytest.mark.anyio
async def test_raw_observations_are_persisted_not_just_the_blend(db_session):
    """Previously only the blended number survived, so an estimate could not be audited or
    recomputed when the blending rule changed."""
    from app.core.security import TokenUser
    from app.repositories.task_duration_repository import TaskDurationRepository
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-obs", email="obs@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    for answer in (20, 35, 50):
        await est.record_actual(user.id, "Buy groceries", answer, estimated_minutes=45)

    rows = await TaskDurationRepository(db_session).observations_for_type(user.id, "shop_groceries")
    assert sorted(r.actual_minutes for r in rows) == [20, 35, 50]
    assert all(r.estimated_minutes == 45 for r in rows), "what we predicted at the time is kept too"


@pytest.mark.anyio
async def test_learning_is_isolated_between_types(db_session):
    """Two types the OLD code would have merged into one 'general' bucket must not affect each
    other."""
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-iso", email="iso@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    for _ in range(10):
        await est.record_actual(user.id, "Do the laundry", 120)

    laundry, laundry_type = await est.estimate(user.id, "Do the laundry")
    dishes, dishes_type = await est.estimate(user.id, "Wash the dishes")
    laundry_baseline = get_type(laundry_type).typical_minutes
    # Moved most of the way toward the observed 120 from a much lower baseline.
    assert (laundry - laundry_baseline) / (120 - laundry_baseline) > 0.75
    assert dishes == get_type(dishes_type).typical_minutes
    assert dishes_type != classify("Do the laundry").key


@pytest.mark.anyio
async def test_a_stored_classification_is_preferred_over_re_reading_the_title(db_session):
    """A user's correction (TIME-285/287) must actually steer learning, not be re-guessed away."""
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-corr", email="corr@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    # The title looks like shopping, but the user says it's really a code review.
    for _ in range(8):
        await est.record_actual(user.id, "Buy groceries", 15, task_type="code_review")

    corrected, _ = await est.estimate(user.id, "Buy groceries", task_type="code_review")
    by_title, by_title_type = await est.estimate(user.id, "Buy groceries")
    assert corrected < get_type("code_review").typical_minutes
    assert by_title == get_type(by_title_type).typical_minutes, "shopping should be untouched"


@pytest.mark.anyio
async def test_duration_feedback_accepts_an_arbitrary_minute_value(client):
    """The iOS sheet replaced three fixed buttons (15/30/60) with a real minute entry, so the
    endpoint has to take any plausible value — not just the three it used to receive (TIME-287)."""
    from unittest.mock import patch

    claims = {"uid": "dur-any", "email": "any@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=claims):
        r = await client.post("/api/v1/capture", headers={"Authorization": "Bearer t"},
                              json={"raw_input": "Buy groceries"})
        task_id = r.json()["id"]

        for value in (1, 7, 23, 137, 480):
            f = await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                                  headers={"Authorization": "Bearer t"},
                                  json={"actual_minutes": value})
            assert f.status_code == 200, f.text

        # Out of range is rejected rather than silently clamped — a 20-hour "task" is a stuck timer,
        # and letting it through would poison the learned estimate.
        for bad in (0, -5, 1441):
            f = await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                                  headers={"Authorization": "Bearer t"},
                                  json={"actual_minutes": bad})
            assert f.status_code == 422, f"{bad} should have been rejected"


@pytest.mark.anyio
async def test_duration_feedback_applies_a_type_correction_before_learning(client, db_session):
    """The sheet lets the user say "that wasn't shopping, it was a code review". The correction has
    to be applied BEFORE the observation is recorded, or the wrong bucket learns from it."""
    from unittest.mock import patch

    claims = {"uid": "dur-fix", "email": "fix@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=claims):
        r = await client.post("/api/v1/capture", headers={"Authorization": "Bearer t"},
                              json={"raw_input": "Buy groceries"})
        task_id = r.json()["id"]
        assert r.json()["task_type"] == "shop_groceries"

        f = await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                              headers={"Authorization": "Bearer t"},
                              json={"actual_minutes": 25, "task_type": "code_review"})
        assert f.status_code == 200, f.text
        assert f.json()["task_type"] == "code_review"

        # An invented key must be ignored rather than stored.
        f2 = await client.post(f"/api/v1/tasks/{task_id}/duration-feedback",
                               headers={"Authorization": "Bearer t"},
                               json={"actual_minutes": 25, "task_type": "not_a_real_type"})
        assert f2.status_code == 200
        assert f2.json()["task_type"] == "code_review", "an invalid correction must not take effect"


@pytest.mark.anyio
async def test_duration_prompt_reports_the_task_type_for_the_correction_ui(client):
    """The sheet shows "counted as <type>" so a wrong guess can be corrected; the prompt endpoint
    has to supply it."""
    from unittest.mock import patch

    claims = {"uid": "dur-ui", "email": "ui@example.com", "role": "user", "email_verified": True}
    with patch("app.core.security.firebase_auth.verify_id_token", return_value=claims):
        r = await client.post("/api/v1/capture", headers={"Authorization": "Bearer t"},
                              json={"raw_input": "Go for a run"})
        task_id = r.json()["id"]
        p = await client.get(f"/api/v1/tasks/{task_id}/duration-prompt",
                             headers={"Authorization": "Bearer t"})
    assert p.status_code == 200
    assert p.json()["task_type"] == "exercise_run"
    assert p.json()["category"] == p.json()["task_type"]   # legacy alias


# ── TIME-305: the LLM predicts a duration, as the PRIOR in the blend ─────────────────────


def test_a_prediction_is_bounded_against_the_library_baseline():
    """A model will confidently say "5 minutes" for a dissertation. The library is generic but never
    absurd, so it makes a good sanity rail."""
    bound = TaskDurationEstimator.bound_prediction
    baseline = 90

    assert bound(120, baseline) == 120, "a plausible prediction passes through untouched"
    assert bound(5, baseline) == 22, "absurdly short is pulled up to 25% of baseline"
    assert bound(6000, baseline) == 360, "absurdly long is pulled down to 4x baseline"
    assert bound(None, baseline) is None
    assert bound(0, baseline) is None


@pytest.mark.anyio
async def test_two_tasks_of_the_same_type_can_now_get_different_estimates(db_session):
    """The whole point. "Complete dissertation abstract" and "Write the weekly status report" both
    classify as writing and both got the library's 90 minutes, because a keyword-to-type-to-fixed-
    number pipeline cannot read the specifics. With a prediction they diverge."""
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-llm", email="llm@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    big, _ = await est.estimate(user.id, "Complete dissertation abstract", predicted_minutes=240)
    small, _ = await est.estimate(user.id, "Write the weekly status report", predicted_minutes=25)

    assert big > small, "the specifics should separate them"
    assert big != small


@pytest.mark.anyio
async def test_without_a_prediction_behaviour_is_exactly_as_before(db_session):
    """Classification and estimation must never depend on the model being reachable."""
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-nollm", email="nollm@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)

    minutes, task_type = await TaskDurationEstimator(db_session).estimate(user.id, "Buy groceries")
    assert minutes == get_type(task_type).typical_minutes


@pytest.mark.anyio
async def test_the_users_own_history_still_wins_over_a_prediction(db_session):
    """The prediction is a PRIOR, not an override. Real observations must take over as they
    accumulate, so a bad prediction self-corrects instead of persisting."""
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-hist", email="hist@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)
    est = TaskDurationEstimator(db_session)

    # This user's grocery runs really do take ~15 minutes.
    for _ in range(15):
        await est.record_actual(user.id, "Buy groceries", 15)

    # An over-long prediction should barely move the answer now.
    with_prediction, _ = await est.estimate(user.id, "Buy groceries", predicted_minutes=120)
    without, _ = await est.estimate(user.id, "Buy groceries")

    # The prior keeps k/(n+k) of the weight by design (TIME-286) — the same as the library
    # baseline does — so it never vanishes entirely. What matters is that the OBSERVED value
    # dominates: the answer must sit far nearer what actually happened than what was predicted.
    assert abs(with_prediction - 15) < abs(with_prediction - 120), (
        f"history should dominate; got {with_prediction} between observed=15 and predicted=120"
    )
    assert with_prediction < 40, "15 real observations of 15 min should still hold sway"

    # And the prediction's influence must SHRINK as evidence accumulates.
    for _ in range(30):
        await est.record_actual(user.id, "Buy groceries", 15)
    with_more_history, _ = await est.estimate(user.id, "Buy groceries", predicted_minutes=120)
    assert with_more_history < with_prediction, (
        "more observations should pull the estimate further from the prediction"
    )


@pytest.mark.anyio
async def test_a_prediction_seeds_the_estimate_before_any_history_exists(db_session):
    """With no observations the prediction IS the best answer available — better than the library's
    generic number for the type."""
    from app.core.security import TokenUser
    from app.services.user_service import UserService

    tu = TokenUser(uid="dur-seed", email="seed@example.com", role="user", email_verified=True)
    user, _ = await UserService(db_session).get_or_create_user(tu.uid, tu.email)

    minutes, task_type = await TaskDurationEstimator(db_session).estimate(
        user.id, "Buy groceries", predicted_minutes=20
    )
    assert minutes == 20
    assert minutes != get_type(task_type).typical_minutes


# ── TIME-303: cross-user calibration REPORT (reporting, never learning) ───────────────────


async def _consenting_user(db, uid: str, granted: bool = True):
    from app.models.consent import ConsentRecord
    from app.services.user_service import UserService

    user, _ = await UserService(db).get_or_create_user(uid, f"{uid}@example.com")
    db.add(ConsentRecord(user_id=user.id, consent_type="analytics", granted=granted))
    await db.flush()
    return user


@pytest.mark.anyio
async def test_calibration_reports_where_the_baseline_is_wrong(db_session):
    """The point of the report: surface hand-written numbers that reality disagrees with, so a
    human can correct them deliberately."""
    from app.repositories.task_duration_repository import DurationCalibrationRepository

    user = await _consenting_user(db_session, "cal-1")
    est = TaskDurationEstimator(db_session)
    baseline = get_type("shop_groceries").typical_minutes
    for _ in range(6):
        await est.record_actual(user.id, "Buy groceries", baseline * 2, estimated_minutes=baseline)
    await db_session.flush()

    rows = await DurationCalibrationRepository(db_session).calibration_by_type()
    row = next(r for r in rows if r["task_type"] == "shop_groceries")
    assert row["samples"] == 6
    assert row["ratio_vs_baseline"] == 2.0, "reality took twice as long as the library says"
    assert row["suggested_baseline"] == baseline * 2


@pytest.mark.anyio
async def test_a_user_who_did_not_consent_is_excluded(db_session):
    """Every other cross-user aggregate here reads analytics-consent-gated sources.
    task_duration_observations is written unconditionally, so this filter is explicit rather than
    inherited — without it the report would aggregate data collected without the consent that
    covers aggregation."""
    from app.repositories.task_duration_repository import DurationCalibrationRepository

    user = await _consenting_user(db_session, "cal-no", granted=False)
    est = TaskDurationEstimator(db_session)
    for _ in range(8):
        await est.record_actual(user.id, "Buy groceries", 90, estimated_minutes=45)
    await db_session.flush()

    assert await DurationCalibrationRepository(db_session).calibration_by_type() == []


@pytest.mark.anyio
async def test_withdrawn_consent_is_respected_not_just_the_first_grant(db_session):
    """Consent is append-only and latest-wins. A user who granted and later withdrew must be
    excluded — reading only the first record would silently keep using their data."""
    from app.models.consent import ConsentRecord
    from app.repositories.task_duration_repository import DurationCalibrationRepository

    user = await _consenting_user(db_session, "cal-withdrawn", granted=True)
    est = TaskDurationEstimator(db_session)
    for _ in range(8):
        await est.record_actual(user.id, "Buy groceries", 90, estimated_minutes=45)
    await db_session.flush()
    assert await DurationCalibrationRepository(db_session).calibration_by_type() != []

    db_session.add(ConsentRecord(user_id=user.id, consent_type="analytics", granted=False))
    await db_session.flush()
    assert await DurationCalibrationRepository(db_session).calibration_by_type() == [], (
        "withdrawn consent must exclude the user"
    )


@pytest.mark.anyio
async def test_a_thin_bucket_is_suppressed_as_a_k_anonymity_floor(db_session):
    """A bucket built from one or two people's data should not be reportable, and a couple of
    observations is not evidence about a baseline either."""
    from app.repositories.task_duration_repository import (
        CALIBRATION_MIN_SAMPLES,
        DurationCalibrationRepository,
    )

    user = await _consenting_user(db_session, "cal-thin")
    est = TaskDurationEstimator(db_session)
    for _ in range(CALIBRATION_MIN_SAMPLES - 1):
        await est.record_actual(user.id, "Buy groceries", 90, estimated_minutes=45)
    await db_session.flush()

    assert await DurationCalibrationRepository(db_session).calibration_by_type() == []


@pytest.mark.anyio
async def test_the_report_never_mutates_the_library(db_session):
    """The invariant this ticket is built around: reporting, not learning. Nothing one user does
    may change the shared prior."""
    from app.repositories.task_duration_repository import DurationCalibrationRepository
    from app.services.task_library import get_type as _get_type

    before = _get_type("shop_groceries").typical_minutes
    user = await _consenting_user(db_session, "cal-immutable")
    est = TaskDurationEstimator(db_session)
    for _ in range(10):
        await est.record_actual(user.id, "Buy groceries", 300, estimated_minutes=45)
    await db_session.flush()

    rows = await DurationCalibrationRepository(db_session).calibration_by_type()
    assert rows, "the report should have something to say"
    assert _get_type("shop_groceries").typical_minutes == before, (
        "the library must be unchanged — correcting it is a deliberate human edit"
    )


@pytest.mark.anyio
async def test_the_catch_all_never_appears_in_the_report(db_session):
    """record_actual refuses to write an observation for an unclassified task, so the catch-all is
    structurally absent rather than merely filtered."""
    from app.repositories.task_duration_repository import DurationCalibrationRepository
    from app.services.task_library import GENERAL_KEY

    user = await _consenting_user(db_session, "cal-general")
    est = TaskDurationEstimator(db_session)
    for _ in range(10):
        await est.record_actual(user.id, "Zorble the frobnicator", 60, estimated_minutes=30)
    await db_session.flush()

    rows = await DurationCalibrationRepository(db_session).calibration_by_type()
    assert all(r["task_type"] != GENERAL_KEY for r in rows)
