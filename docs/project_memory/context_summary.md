# Context Summary

**Last updated:** 2026-07-05

## Current Build State

Phases 0–2 merged to main. Phases 3 (subscriptions), 4 (mobile shells), early Phase 5 tasks,
and Phase 8 (Recommendation Engine V1) complete. Phase 9 in progress (TIME-039, TIME-040 done).

Backend API endpoints implemented:
- `GET /api/v1/health`, `GET /api/v1/auth/me`
- `GET/PATCH /api/v1/users/me`, profiles, preferences
- Onboarding state machine, personality, consent records
- Admin routes
- `POST/GET/PATCH/DELETE /api/v1/tasks` (soft-delete)
- `POST /api/v1/capture` (LLM parse → Task)
- Notifications, replan requests
- `GET /api/v1/now`, `GET /api/v1/today`
- `GET /api/v1/recommendations` (best + up to 2 alternatives + LLM "why" + usable_minutes + skipped_meals)
- `POST /api/v1/recommendations/feedback` (done/snooze/not_now — suppresses task from future recommendations)
- `GET /api/v1/routines`, `PATCH /api/v1/routines/{routine_type}` (sleep/meal/hygiene blocks, default-seeded)
- `POST /api/v1/meals`, `GET /api/v1/meals/today` (skip inference via routine windows)

Database tables: users, profiles, preferences, personalities, onboarding_states, consent_records,
subscription_records, notification_preferences, replan_requests, tasks, internal_reminders,
recommendation_feedback, routine_assumptions, meal_events.

Backend tests: 172, all passing (see Known Problems re: 2 intermittently-flaky Stripe tests).

Mobile app shells:
- iOS SwiftUI: bottom tab navigator (Now/Today/Capture/Insights/Settings), AuthService with `#if canImport(FirebaseAuth)` stubs, CaptureViewModel + CaptureView wired to backend. `xcodebuild → BUILD SUCCEEDED`.
- Android Kotlin/Compose: bottom nav, AuthViewModel, CaptureViewModel + CaptureScreen wired to backend. `./gradlew assembleDebug → BUILD SUCCESSFUL`.

## Jira Key Mapping (recent — see decision_log.md/implementation_log.md for full history)
- TIME-040 (impl seq) → Jira TIME-39 (Meal Tracking) — **Done (this session)**
- TIME-039 (impl seq) → Jira TIME-38 (Routine Assumptions Model) — Done (PR #30, 2026-07-05)
- TIME-038 (impl seq) → Jira TIME-37 (Feedback Collection) — Done (PR #29, 2026-07-05)
- TIME-036 (impl seq) → Jira TIME-36 (Recommendation API V1) — Done (PR #28, 2026-07-04)
- Earlier tickets (TIME-019 through TIME-035) → Jira TIME-25 through TIME-35 — all Done;
  see `implementation_log.md` for the full ticket-by-ticket mapping if needed.

## Last Completed Work
TIME-040 (Jira TIME-39): Meal Tracking (Lightweight)
- `meal_events` table; `POST /api/v1/meals`, `GET /api/v1/meals/today`
- Skip inferred from TIME-039 routine windows once they pass with nothing logged
- `skipped_meals` surfaced in `GET /api/v1/recommendations` as context only (no scoring change)
- 20 new/changed tests; full suite 172/172

Full history of TIME-034 through TIME-039 is in `implementation_log.md` and `change_summary.md`.

## Current Active Task
TIME-041: Commute Detection — next in the autonomous build sequence (user directed continuous
autonomous build through the remaining ticket backlog, merging each PR without waiting for review).

## Important Decisions to Preserve
- Firebase added via Xcode UI (File > Add Package Dependencies), NOT in pbxproj — `#if canImport` guards ensure CLI builds work
- `google-services.json` / `GoogleService-Info.plist` are placeholders — need real Firebase Console files
- Native iOS (Swift/SwiftUI) + native Android (Kotlin/Compose); web is companion only
- FastAPI + PostgreSQL + Firebase Auth + Redis/Celery + LLM abstraction
- Bottom tabs: Now, Today, Capture, Insights, Settings
- Calendar writes require approval; Replans require approval
- 14-day trial requires payment info; Free Basic Mode after trial expiry
- `not_now` feedback suppresses a task from recommendations for 4h, not permanently (TIME-038)
- Routine/meal blocks are UTC-minute-of-day only — not yet subtracted from usable time, deferred
  until UsableTimeService gains real timezone awareness (see Known Problems)
- User has authorized merging PRs without waiting for review during this autonomous run
  (2026-07-04) — re-confirm at the start of a new session rather than assuming it still stands

## Known Problems
- `python-dotenv` cannot parse multi-line `.env` values → non-blocking (warnings only)
- Firebase SPM cannot be resolved via CLI — needs Xcode UI
- No Docker/Postgres available in this session's environment — `alembic upgrade head` only
  verified offline (`--sql` mode); needs a real-DB check before deploy
- `phase_status.md`'s acceptance-criteria checkboxes for Phases 3–7 predate this file's tracking
  and need a reconciliation pass (see phase_status.md Staleness Warning)
- `UsableTimeService` is UTC-only and doesn't yet subtract routine/meal blocks — full details in
  known_issues.md
- `test_referrals.py::test_conversion_extends_subscriptions` / `test_no_double_conversion`
  intermittently fail on real Stripe network calls in this sandbox — rerun before assuming a
  regression (known_issues.md)

## Warnings for Next Session
- Read this file + phase_status.md before doing anything.
- The `.env` file is gitignored and contains real secrets — never commit it.
- `.claude/settings.local.json` and `.devcontainer/` are untracked leftovers from a prior session
  (an already-documented devcontainer firewall fix that was never committed) — not part of any
  ticket in this session, left alone; flag to the user if they want that committed separately.
