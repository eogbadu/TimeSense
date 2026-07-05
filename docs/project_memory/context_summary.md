# Context Summary

**Last updated:** 2026-07-05

## Current Build State

Phases 0–2 merged to main. Phases 3 (subscriptions), 4 (mobile shells), early Phase 5 tasks,
Phase 8 (Recommendation Engine V1), and Phase 9 (Routines/Meals/Commute/Sleep-Wake) complete.
Phase 10 (Notifications, Widgets, Ambient Surfaces) in progress (TIME-043 done; TIME-044/045
are iOS/Android widget tickets next).

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
- `POST /api/v1/commute/detect` (location-consent gated), `GET /api/v1/commute/pending`,
  `POST /api/v1/commute/{id}/confirm`/`.../reject`
- `POST /api/v1/sleep/events` (health-data-consent gated, late wake proposes a morning replan),
  `GET /api/v1/sleep/today`
- No new endpoints for TIME-043 — `notification_mode` (gentle/balanced/active_coach) already had
  read/write via `PATCH /api/v1/users/me/preferences`; TIME-043 only added the behavior that acts
  on it (NotificationService.maybe_send_morning_checkin/evening_checkout/learning_prompt), driven
  by a Celery beat schedule rather than a user-facing route

Database tables: users, profiles, preferences, personalities, onboarding_states, consent_records,
subscription_records, replan_requests, notifications, notification_events, tasks,
internal_reminders, recommendation_feedback, routine_assumptions, meal_events, commute_events,
sleep_wake_events. (Correction: there is no separate "notification_preferences" table — the
notification_mode field lives directly on user_preferences; a prior version of this file listed
that table incorrectly.)

Backend tests: 198, all passing (see Known Problems re: 2 flaky Stripe-network tests).

Mobile app shells:
- iOS SwiftUI: bottom tab navigator (Now/Today/Capture/Insights/Settings), AuthService with `#if canImport(FirebaseAuth)` stubs, CaptureViewModel + CaptureView wired to backend. `xcodebuild → BUILD SUCCEEDED`.
- Android Kotlin/Compose: bottom nav, AuthViewModel, CaptureViewModel + CaptureScreen wired to backend. `./gradlew assembleDebug → BUILD SUCCESSFUL`.

## Jira Key Mapping (recent — see decision_log.md/implementation_log.md for full history)
- TIME-043 (impl seq) → Jira TIME-42 (Notification Modes and Learning Prompts) — **Done (this session)**
- TIME-042 (impl seq) → Jira TIME-41 (Sleep/Wake Signal Integration) — **Done (PR #34 merged 2026-07-05)**
- TIME-041 (impl seq) → Jira TIME-40 (Commute Detection) — **Done (PR #32 merged 2026-07-05)**
- TIME-040 (impl seq) → Jira TIME-39 (Meal Tracking) — Done (PR #31, 2026-07-05)
- TIME-039 (impl seq) → Jira TIME-38 (Routine Assumptions Model) — Done (PR #30, 2026-07-05)
- TIME-038 (impl seq) → Jira TIME-37 (Feedback Collection) — Done (PR #29, 2026-07-05)
- Earlier tickets (TIME-019 through TIME-036) → Jira TIME-25 through TIME-36 — all Done;
  see `implementation_log.md` for the full ticket-by-ticket mapping if needed.

## Last Completed Work
TIME-043 (Jira TIME-42): Notification Modes and Learning Prompts
- `notification_events` table (audit trail + once-per-day dedup); NotificationService gained
  `maybe_send_morning_checkin`/`maybe_send_evening_checkout`/`maybe_send_learning_prompt`/
  `maybe_send_routine_learning_prompt`, gated on the pre-existing `UserPreferences.notification_mode`
  (gentle/balanced/active_coach — that field already existed, this ticket only added behavior)
- Mode mapping: gentle -> evening check-out only; balanced -> both check-ins; active_coach -> both
  check-ins + a concrete learning prompt confirming the still-default "sleep" RoutineAssumption
  (TIME-039), gated on a 14-day placeholder Learning Mode window (reuses the existing trial length,
  not a new number — the real data-driven learning-period-end is still deferred per decision_log.md)
- `backend/app/workers/notification_tasks.py` — 3 Celery tasks + a UTC beat schedule
  (8am/10am/9pm); untested in this environment (no Redis/Docker), same precedent as health_task.py
- 9 new tests (service-layer against db_session, matching test_notifications.py's pattern); full
  suite 198/198 (excluding 2 known-flaky Stripe tests)
- Corrected a stale claim in this file: there is no separate "notification_preferences" table —
  notification_mode lives on user_preferences

Full history of TIME-034 through TIME-042 is in `implementation_log.md` and `change_summary.md`.

## Current Active Task
Phase 10 (Notifications, Widgets, Ambient Surfaces) is in progress. Next up: TIME-044 (iOS
Widgets), which is entirely native iOS/WidgetKit work — no backend changes expected. Also see
known_issues.md — the deferred UsableTimeService timezone-awareness pass (to actually subtract
routine/meal/commute/sleep blocks from usable time, and to make Celery beat/notification timing
per-user-local instead of UTC-only) is unblocked and still worth scheduling soon rather than
continuing to defer it across more tickets.

## iOS HealthKit Decision Point (deferred from TIME-042)
TIME-042 only built the backend contract (ingest a wake_time signal, gate on health_data consent,
trigger a morning replan suggestion). The actual iOS-side HealthKit read integration
(`ios/.../HealthService.swift`, `HKHealthStore` authorization request, Info.plist usage-description
strings, calling `POST /api/v1/sleep/events` after reading sleep analysis samples) was not built —
it needs real device/Xcode testing this environment can't do, and touches Apple's health-data
entitlement request flow, which is worth a deliberate decision (own ticket vs. folding into an iOS
tranche) rather than bundling into the backend ticket. Flag to the user before scoping that work.

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
- `test_referrals.py::test_conversion_extends_subscriptions` / `test_no_double_conversion` fail on
  real Stripe network calls in this sandbox (intermittent at first, now consistent this session) —
  reproduces identically on `main`, unrelated to any code change (known_issues.md)
- No calendar-event-location correlation for commute detection (TIME-041) — no CalendarEvent table
  with location data exists in this codebase yet

## Warnings for Next Session
- Read this file + phase_status.md before doing anything.
- The `.env` file is gitignored and contains real secrets — never commit it.
- `.claude/settings.local.json` and `.devcontainer/` are untracked leftovers from a prior session
  (an already-documented devcontainer firewall fix that was never committed) — not part of any
  ticket in this session, left alone; flag to the user if they want that committed separately.
