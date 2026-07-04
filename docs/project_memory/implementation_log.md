# Implementation Log

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
