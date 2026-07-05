# Change Summary

## 2026-07-05 — TIME-039 (Jira TIME-38) Routine Assumptions Model

**What changed:**
- `routine_assumptions` table: per-user sleep/breakfast/lunch/dinner/morning_hygiene/evening_hygiene blocks
- `GET /api/v1/routines` — seeds 6 sensible defaults on first call, returns them
- `PATCH /api/v1/routines/{routine_type}` — edit a block's start/end minute, flips is_customized
- Completes the data model piece of Phase 9; meal/commute/sleep tickets (TIME-040–042) build on it

**What did not change:**
- `UsableTimeService` does not yet subtract routine blocks from usable time — deliberately deferred
  (see known_issues.md) until timezone awareness is added once all Phase 9 signals exist
- No mobile UI for editing routines
- No automatic learning/detection of routines from behavior

**Next:**
- TIME-040: Meal Tracking (Lightweight)

## 2026-07-04 — TIME-038 (Jira TIME-37) Feedback Collection

**What changed:**
- `POST /api/v1/recommendations/feedback` — records done/snooze/not_now reaction to a task
- `recommendation_feedback` table + model + repository
- `GET /api/v1/recommendations` now excludes tasks with an active snooze or a recent not_now
- Fixed pre-existing Alembic multi-head split (4 divergent heads from earlier merged PRs) with a merge migration
- Registered `RecommendationFeedback` in `app/models/__init__.py` for autogenerate detection
- Added TIME-038 ticket definition to `scripts/create_jira_tickets.py` and created it in Jira (TIME-37) before this work was committed — it had been missing despite code already existing in the working tree at session start

**What did not change:**
- No mobile UI for feedback buttons (API only, per ticket non-goals)
- No feedback-driven scorer weight learning
- No weekly insight generation from feedback

**Next:**
- TIME-039: Routine Assumptions Model, or TIME-040: Meal Tracking (Lightweight)
- Verify `alembic upgrade head` against a real Postgres before deploy — only offline/`--sql` verification was possible in this session (no Docker/Postgres available)

## 2026-07-03 — TIME-001 Repository Bootstrap

**What changed:**
- Repository created from scratch
- All required documentation directories created
- Core docs written: README, AGENTS, CHANGELOG, product brief, architecture overview
- Project memory files initialized
- Phase 0 (TIME-001) in progress

**What did not change:**
- No product application code was written
- No backend, iOS, Android, or web code exists yet

**Next:**
- Complete remaining TIME-001 files (workflows, tickets, skills, PR template, operational CLAUDE.md)
- Begin TIME-002: Backend Foundation
