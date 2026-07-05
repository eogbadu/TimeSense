# Context Summary

**Last updated:** 2026-07-05

## Current Build State

Phases 0–2 merged to main. Phases 3 (subscriptions), 4 (mobile shells), early Phase 5 tasks,
and Phase 8 (Recommendation Engine V1) complete. Phase 9 in progress (TIME-039 done).

Backend API endpoints implemented:
- `GET /api/v1/health`, `GET /api/v1/auth/me`
- `GET/PATCH /api/v1/users/me`, profiles, preferences
- Onboarding state machine, personality, consent records
- Admin routes
- `POST/GET/PATCH/DELETE /api/v1/tasks` (soft-delete)
- `POST /api/v1/capture` (LLM parse → Task)
- Notifications, replan requests
- `GET /api/v1/now`, `GET /api/v1/today`
- `GET /api/v1/recommendations` (best + up to 2 alternatives + LLM "why" + usable_minutes)
- `POST /api/v1/recommendations/feedback` (done/snooze/not_now — suppresses task from future recommendations)
- `GET /api/v1/routines`, `PATCH /api/v1/routines/{routine_type}` (sleep/meal/hygiene blocks, default-seeded)

Database tables: users, profiles, preferences, personalities, onboarding_states, consent_records,
subscription_records, notification_preferences, replan_requests, tasks, internal_reminders,
recommendation_feedback, routine_assumptions.

Backend tests: 161, all passing (full `pytest` run in this session).

Mobile app shells:
- iOS SwiftUI: bottom tab navigator (Now/Today/Capture/Insights/Settings), AuthService with `#if canImport(FirebaseAuth)` stubs, CaptureViewModel + CaptureView wired to backend. `xcodebuild → BUILD SUCCEEDED`.
- Android Kotlin/Compose: bottom nav, AuthViewModel, CaptureViewModel + CaptureScreen wired to backend. `./gradlew assembleDebug → BUILD SUCCESSFUL`.

## Jira Key Mapping
- TIME-039 (impl seq) → Jira TIME-38 (Routine Assumptions Model) — **Done (this session)**
- TIME-038 (impl seq) → Jira TIME-37 (Feedback Collection) — **Done (PR #29 merged 2026-07-05)**
- TIME-019 → TIME-25 (Android shell) — Done
- TIME-020 → TIME-26 (iOS Firebase Auth) — Done
- TIME-021 → TIME-27 (Android Firebase Auth) — Done
- TIME-022 → TIME-28 (Backend Onboarding State APIs) — Done
- TIME-033 → TIME-29 (Task Model + Internal Reminders) — Done
- TIME-037 → TIME-30 (LLM Gateway) — Done
- TIME-030 → TIME-31 (Capture Screen connect) — Done (PR #23)
- TIME-031 → TIME-32 (Today Screen timeline) — Done (PR #24)
- TIME-032 → TIME-33 (Now Screen context+recommendation) — Done (PR #25)
- TIME-034 → TIME-34 (Usable Time Calculator) — Done (PR #26)
- TIME-035 → TIME-35 (Task Scoring Service) — Done (PR #27)
- TIME-036 → TIME-36 (Recommendation API V1) — Done (PR #28, merged 2026-07-04)

## Last Completed Work
TIME-039 (Jira TIME-38): Routine Assumptions Model
- `routine_assumptions` table: sleep/breakfast/lunch/dinner/morning_hygiene/evening_hygiene blocks per user
- `GET /api/v1/routines` seeds 6 defaults on first call; `PATCH /api/v1/routines/{routine_type}` edits one
- NOT yet subtracted from `UsableTimeService` — deliberately deferred, see known_issues.md
- 9 new tests; full suite 161/161

TIME-038 (Jira TIME-37): Feedback Collection — **completes Phase 8**
- `POST /api/v1/recommendations/feedback` — records done/snooze/not_now; done also marks task status=done
- `RecommendationFeedbackRepository.get_suppressed_task_ids()` — excludes actively-snoozed tasks
  (snooze_until in future) and recently-dismissed tasks (not_now, 4h cooldown) from `GET /api/v1/recommendations`
- Fixed pre-existing Alembic multi-head issue (4 divergent heads accumulated from TIME-030/033/036
  each branching off the same parent without rebasing) — added a merge migration, now single head
- 16 tests for feedback + suppression, all passing; full suite 152/152

TIME-036 (Jira TIME-36): Recommendation API V1
- `GET /api/v1/recommendations` → {best: {task, why}, alternatives: [Task], usable_minutes}
- RecommendationService: TaskScorer.rank() + UsableTimeService.calculate() + LLM why

TIME-035 (Jira TIME-35): TaskScorer — priority (0.5) + deadline (0.35) + duration fit (0.15)
TIME-034 (Jira TIME-34): UsableTimeService — merges scheduled blocks, returns free-window minutes

## Current Active Task
TIME-040: Meal Tracking (Lightweight) — next in the autonomous build sequence (user directed
continuous autonomous build through the remaining ticket backlog, merging each PR without
waiting for review).

## Next Recommended Task
TIME-040: Meal Tracking (Lightweight)

## Important Decisions to Preserve
- Firebase added via Xcode UI (File > Add Package Dependencies), NOT in pbxproj — `#if canImport` guards ensure CLI builds work
- `google-services.json` and `GoogleService-Info.plist` are placeholders — real files needed from Firebase Console before auth works at runtime
- Native iOS (Swift/SwiftUI) + native Android (Kotlin/Compose)
- FastAPI + PostgreSQL + Firebase Auth + Redis/Celery + LLM abstraction
- Bottom tabs: Now, Today, Capture, Insights, Settings
- Calendar writes require approval; Replans require approval
- 14-day trial requires payment info; Free Basic Mode after trial expiry
- `not_now` feedback suppresses a task from recommendations for 4 hours (not permanently) —
  balances "don't nag" against not vanishing a still-pending task for the rest of the day (TIME-038)

## Known Problems
- `python-dotenv` cannot parse multi-line `.env` values → non-blocking (warnings only)
- Firebase SPM cannot be resolved via CLI — needs Xcode UI
- No Docker/Postgres available in this session's environment — `alembic upgrade head` was only
  verified offline (`--sql` mode); needs a real-DB check before deploy
- `phase_status.md`'s acceptance-criteria checkboxes for Phases 3–7 are stale relative to this file
  (see phase_status.md Staleness Warning) — needs a reconciliation pass
- `UsableTimeService` is UTC-only and doesn't yet subtract routine blocks (TIME-039) — see
  known_issues.md "RoutineAssumption data is not yet subtracted from usable time"

## Warnings for Next Session
- Read this file + phase_status.md before doing anything.
- The `.env` file is gitignored and contains real secrets — never commit it.
- Jira key mapping above is required — implementation seq numbers ≠ Jira ticket numbers.
- User has authorized merging PRs without waiting for review during this autonomous run
  (2026-07-04) — do not assume this stands for future sessions unless re-confirmed.
- `.claude/settings.local.json` and `.devcontainer/` are untracked leftovers from a prior session
  (the devcontainer firewall fix documented in known_issues.md was never committed) — not part of
  TIME-038, left alone; flag to the user if they want that committed separately.
