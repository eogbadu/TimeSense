# Context Summary

**Last updated:** 2026-07-05

## ⚠️ DO NOT MERGE PR #33 (feature/TIME-042-sleep-wake-signal) WITHOUT MAC VERIFICATION
PR #33 contains `ios/TimeSense/Core/Health/HealthService.swift`, written with no macOS/Xcode
access (this session runs on Linux) and never compiled. Per explicit user instruction, it must be
built and tested on a real Mac (`xcodebuild build`/`test`, see known_issues.md for exact steps)
before merging. The backend half of that same PR (sleep_wake_events, morning replan trigger) IS
fully tested — 194/194 — only the iOS file is unverified. Do not merge, and do not run
`python scripts/move_ticket.py TIME-41 done` until the user confirms the Xcode build passed.

## Current Build State

Phases 0–2 merged to main. Phases 3 (subscriptions), 4 (mobile shells), early Phase 5 tasks,
and Phase 8 (Recommendation Engine V1) complete. Phase 9 in progress (TIME-039–041 done, TIME-042
backend done / iOS unverified — see warning above).

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
- `POST /api/v1/sleep-wake` (triggers morning replan on late wake), `GET /api/v1/sleep-wake/today`
  — code-complete and fully tested, but NOT YET on `main`: it ships in PR #33 alongside the
  unverified iOS file, and the whole PR is held unmerged (see warning above) rather than splitting
  the backend out separately

Database tables on `main` through TIME-041: users, profiles, preferences, personalities,
onboarding_states, consent_records, subscription_records, notification_preferences,
replan_requests, tasks, internal_reminders, recommendation_feedback, routine_assumptions,
meal_events, commute_events. `sleep_wake_events` exists only on the unmerged PR #33 branch.

Backend tests: 194 passing on the PR #33 branch (181 on `main`); see Known Problems re: 2 flaky
Stripe-network tests.

Mobile app shells:
- iOS SwiftUI: bottom tab navigator (Now/Today/Capture/Insights/Settings), AuthService with `#if canImport(FirebaseAuth)` stubs, CaptureViewModel + CaptureView wired to backend. `xcodebuild → BUILD SUCCEEDED`.
- Android Kotlin/Compose: bottom nav, AuthViewModel, CaptureViewModel + CaptureScreen wired to backend. `./gradlew assembleDebug → BUILD SUCCESSFUL`.

## Jira Key Mapping (recent — see decision_log.md/implementation_log.md for full history)
- TIME-042 (impl seq) → Jira TIME-41 (Sleep/Wake Signal Integration) — **In Review, PR #33 OPEN
  AND UNMERGED — do not merge without Mac verification, see warning at top of this file**
- TIME-041 (impl seq) → Jira TIME-40 (Commute Detection) — Done (PR #32 merged 2026-07-05)
- TIME-040 (impl seq) → Jira TIME-39 (Meal Tracking) — Done (PR #31, 2026-07-05)
- TIME-039 (impl seq) → Jira TIME-38 (Routine Assumptions Model) — Done (PR #30, 2026-07-05)
- TIME-038 (impl seq) → Jira TIME-37 (Feedback Collection) — Done (PR #29, 2026-07-05)
- Earlier tickets (TIME-019 through TIME-036) → Jira TIME-25 through TIME-36 — all Done;
  see `implementation_log.md` for the full ticket-by-ticket mapping if needed.

## Last Completed Work
TIME-042 (Jira TIME-41): Sleep/Wake Signal Integration — backend done & verified, iOS unverified
- `sleep_wake_events`; `POST /api/v1/sleep-wake` triggers `MorningReplanService` which calls the
  existing `NotificationService.propose_replan()` when wake is >45min later than the sleep
  RoutineAssumption window (reused approval flow, no new mechanism)
- `HealthService.swift` written but NOT compiled/tested — see warning at top of this file
- 11 new backend tests; full suite 194/194 on the PR branch
- PR #33 open, held unmerged pending Mac build verification

## Current Active Task
Waiting on the user to build/verify PR #33 on macOS before it merges. Do NOT start work that
assumes TIME-042 is on `main` (e.g. anything using sleep_wake_events) until that happens. Once
merged: run `python scripts/move_ticket.py TIME-41 done`, then move on to TIME-043 (Notification
Modes and Learning Prompts, Phase 10) — the next backend-only ticket in the sequence, per the
user's "continue autonomously" instruction from earlier this session.

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
  (2026-07-04) — re-confirm at the start of a new session rather than assuming it still stands.
  EXCEPTION: PR #33 (TIME-042) is explicitly held unmerged pending Mac verification — this
  override does not apply to it.
- HealthKit capability + NSHealthShareUsageDescription (TIME-042) go through Xcode UI on macOS,
  never hand-edited into project.pbxproj here — same reasoning as the Firebase decision above

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
