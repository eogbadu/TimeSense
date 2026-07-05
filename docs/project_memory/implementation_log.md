# Implementation Log

## 2026-07-05 — TIME-040 (Jira TIME-39): Meal Tracking (Lightweight)

### Created
- `backend/app/models/meal.py` — MealEvent model, MEAL_TYPES, MEAL_STATUSES
- `backend/migrations/versions/i9j0k1l2m3n4_add_meal_events.py` — meal_events table
- `backend/app/repositories/meal_repository.py` — log(), get_today_status() (explicit log wins;
  else infers skipped/pending from the matching RoutineAssumption window from TIME-039)
- `backend/app/schemas/meal.py` — MealLogRequest, MealEventResponse, MealTodayResponse
- `backend/app/api/v1/meals.py` — POST /meals, GET /meals/today
- `backend/tests/test_meals.py` — 9 tests (API + direct repository skip/pending inference)

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered meals router/model
- `backend/app/api/v1/recommendations.py` — RecommendationResponse gained `skipped_meals: list[str]`,
  sourced from MealRepository, context only (does not change TaskScorer/ranking)
- `backend/tests/test_recommendations.py` — 3 tests for the new field

### Design notes
- Skip inference reuses the UTC-minute-of-day RoutineAssumption windows directly — same
  UTC-only simplification `UsableTimeService` already relies on, not blocked on the
  timezone-awareness follow-up tracked in known_issues.md.
- Discovered `test_referrals.py` has 2 tests that intermittently fail on real Stripe network
  calls in this sandbox (unrelated to this ticket) — documented in known_issues.md, not fixed here.

### Verification
- `pytest tests/test_meals.py tests/test_recommendations.py -v` — 20 passed
- Full suite: `pytest` — 172 passed (after a rerun past the flaky Stripe network tests above)
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline

## 2026-07-05 — TIME-039 (Jira TIME-38): Routine Assumptions Model

### Created
- `backend/app/models/routine.py` — RoutineAssumption model, ROUTINE_TYPES, DEFAULT_ROUTINES (sleep/breakfast/lunch/dinner/morning_hygiene/evening_hygiene, minutes-since-local-midnight)
- `backend/migrations/versions/h8i9j0k1l2m3_add_routine_assumptions.py` — routine_assumptions table
- `backend/app/repositories/routine_repository.py` — get_or_seed_defaults(), update_one()
- `backend/app/schemas/routine.py` — RoutineAssumptionResponse, RoutineAssumptionUpdate
- `backend/app/api/v1/routines.py` — GET /routines (seeds defaults), PATCH /routines/{routine_type}
- `backend/tests/test_routines.py` — 9 tests

### Modified
- `backend/app/api/v1/__init__.py` — registered routines_router
- `backend/app/models/__init__.py` — registered RoutineAssumption

### Design notes
- Deliberately does NOT wire routine blocks into `UsableTimeService` yet — see known_issues.md
  "RoutineAssumption data (TIME-039) is not yet subtracted from usable time". `UsableTimeService`
  has no timezone awareness today; doing that properly once for routines+meals+commute together
  (after TIME-040–042) avoids three partial integrations.
- `end_minute < start_minute` signals a block that wraps past midnight (sleep 23:00→07:00).
- Editing a routine sets `is_customized=True` so future auto-detection tickets (commute/sleep) know
  not to silently overwrite a user's explicit choice.

### Verification
- `pytest tests/test_routines.py -v` — 9 passed
- Full suite: `pytest` — 161 passed
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline (no live
  Postgres available in this environment)

## 2026-07-04 — TIME-038 (Jira TIME-37): Feedback Collection

### Created
- `backend/app/models/recommendation_feedback.py` — RecommendationFeedback model (user_id, task_id, signal, snooze_until)
- `backend/migrations/versions/g7h8i9j0k1l2_add_recommendation_feedback.py` — recommendation_feedback table
- `backend/app/repositories/recommendation_feedback_repository.py` — RecommendationFeedbackRepository.get_suppressed_task_ids()
- `backend/tests/test_feedback.py` — 7 tests for POST /recommendations/feedback
- `backend/migrations/versions/e55970716568_merge_parallel_migration_heads.py` — merges 4 divergent Alembic heads (pre-existing issue, see Known Issues)

### Modified
- `backend/app/api/v1/recommendations.py` — added `POST /recommendations/feedback` (done/snooze/not_now); `GET /recommendations` now filters out tasks suppressed by active snooze or a recent not_now
- `backend/app/models/__init__.py` — registered RecommendationFeedback so Alembic autogenerate detects it
- `backend/tests/test_recommendations.py` — 3 new tests for suppression behavior (not_now, active snooze, expired snooze)

### Design notes
- `not_now` suppresses a task from recommendations for a 4-hour cooldown (`NOT_NOW_COOLDOWN`), not permanently — avoids "nagging" per the recommendation-engine skill while still letting a still-pending task resurface later.
- `snooze` suppresses until `snooze_until` passes.
- Only the *latest* feedback per task is considered — an expired snooze or superseded not_now does not keep suppressing.
- `signal=done` also flips the task to `status=done` via `TaskRepository.update`.

### Verification
- `pytest tests/test_feedback.py tests/test_recommendations.py -v` — 16 passed
- Full suite: `pytest` — 152 passed
- `alembic upgrade head --sql` (offline mode) — compiles cleanly, single resolved head. No live Postgres available in this environment to run a real `alembic upgrade head`; needs verification against a real DB before deploy.

## 2026-07-03 — TIME-001: Repository Bootstrap

### Created
- `/README.md` — full project overview, stack, setup instructions
- `/AGENTS.md` — agent rules, subagents, skills, code generation constraints
- `/CHANGELOG.md` — initialized
- `/docs/product/product_brief.md` — product vision, rules, non-negotiables
- `/docs/architecture/architecture_overview.md` — system architecture, backend/mobile/web structure, integration patterns, data flow
- `/docs/project_memory/context_summary.md` — current state and next steps
- `/docs/project_memory/phase_status.md` — phase tracking
- `/docs/project_memory/decision_log.md` — all settled product and technical decisions

### In Progress
- Remaining project memory files
- Workflow docs
- Ticket sequence
- Skills
- PR template
- Operational CLAUDE.md
