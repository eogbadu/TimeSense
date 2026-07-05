# Context Summary

**Last updated:** 2026-07-05

## Current Build State

Phases 0–2 merged to main. Phases 3 (subscriptions), 4 (mobile shells), early Phase 5 tasks,
Phase 8 (Recommendation Engine V1), Phase 9 (Routines/Meals/Commute/Sleep-Wake), Phase 10
(Notifications, Widgets, Ambient Surfaces), Phase 11 (Insights and Learning Summary), and Phase 12
(Admin Dashboard — TIME-048, first ticket to touch `web/`) complete. Phase 13 (Integrations
Expansion) next.

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
- `GET /api/v1/insights/weekly` (Premium-gated, generates+caches the most recently completed
  week's aggregate + LLM summary), `GET /api/v1/insights/history?limit=8`
- `GET /api/v1/admin/users?search=` (extended with search + real total), `GET /api/v1/admin/`
  `subscriptions`/`feedback`/`integrations`/`metrics`/`waitlist` (all new, admin-gated) — built for
  TIME-048's web admin dashboard alongside the already-existing `GET/POST /api/v1/invites/codes`
- No new endpoints for TIME-043 — `notification_mode` (gentle/balanced/active_coach) already had
  read/write via `PATCH /api/v1/users/me/preferences`; TIME-043 only added the behavior that acts
  on it (NotificationService.maybe_send_morning_checkin/evening_checkout/learning_prompt), driven
  by a Celery beat schedule rather than a user-facing route

Database tables: users, profiles, preferences, personalities, onboarding_states, consent_records,
subscription_records, replan_requests, notifications, notification_events, tasks,
internal_reminders, recommendation_feedback, routine_assumptions, meal_events, commute_events,
sleep_wake_events, weekly_insights. (Correction: there is no separate "notification_preferences"
table — the notification_mode field lives directly on user_preferences; a prior version of this
file listed that table incorrectly.)

Backend tests: 226, all passing (see Known Problems re: 2 flaky Stripe-network tests).

Mobile app shells:
- iOS SwiftUI: bottom tab navigator (Now/Today/Capture/Insights/Settings), AuthService with `#if canImport(FirebaseAuth)` stubs, CaptureViewModel + CaptureView wired to backend. `xcodebuild → BUILD SUCCEEDED`. Plus (TIME-044) a `TimeSenseWidgetExtension` WidgetKit target with three home-screen widgets (Usable Time, Next Up, Do Next) reading a shared App-Group snapshot the app writes. Insights tab (TIME-046) now shows a real weekly summary + stats grid behind the Premium gate.
- Android Kotlin/Compose: bottom nav, AuthViewModel, CaptureViewModel + CaptureScreen wired to backend. `./gradlew assembleDebug → BUILD SUCCESSFUL`. Plus (TIME-045) two Jetpack Glance AppWidgets (Usable Time, Next Event), each reading its own Preferences state written by NowViewModel/TodayViewModel. Insights tab (TIME-046) mirrors iOS's real content.
- Both platforms (TIME-047): Settings > Preferences has a "Learned Assumptions" screen to view/edit the 6 RoutineAssumption blocks via the existing GET/PATCH /api/v1/routines endpoints — no backend changes.

Web companion (TIME-048, new): Next.js 16 (App Router) + TypeScript + Tailwind 4 + Firebase Auth
(env-var-driven, no real project yet). Role-protected `/admin` dashboard: metrics/integration
status, user search, invite codes, subscriptions, feedback review. `npm run build`/`npm run lint`
both clean.

## Jira Key Mapping (recent — see decision_log.md/implementation_log.md for full history)
- TIME-048 (impl seq) → Jira TIME-47 (Admin Dashboard Foundation, Web) — **Done (PR #40 merged 2026-07-05)**
- TIME-047 (impl seq) → Jira TIME-46 (Learned Assumptions Settings) — **Done (PR #39 merged 2026-07-05)**
- TIME-046 (impl seq) → Jira TIME-45 (Weekly Insights Generation) — **Done (PR #38 merged 2026-07-05)**
- TIME-045 (impl seq) → Jira TIME-44 (Android Widgets) — **Done (PR #37 merged 2026-07-05)**
- TIME-044 (impl seq) → Jira TIME-43 (iOS Widgets) — **Done (PR #36 merged 2026-07-05)**
- TIME-043 (impl seq) → Jira TIME-42 (Notification Modes and Learning Prompts) — **Done (PR #35 merged 2026-07-05)**
- TIME-042 (impl seq) → Jira TIME-41 (Sleep/Wake Signal Integration) — **Done (PR #34 merged 2026-07-05)**
- TIME-041 (impl seq) → Jira TIME-40 (Commute Detection) — **Done (PR #32 merged 2026-07-05)**
- TIME-040 (impl seq) → Jira TIME-39 (Meal Tracking) — Done (PR #31, 2026-07-05)
- TIME-039 (impl seq) → Jira TIME-38 (Routine Assumptions Model) — Done (PR #30, 2026-07-05)
- TIME-038 (impl seq) → Jira TIME-37 (Feedback Collection) — Done (PR #29, 2026-07-05)
- Earlier tickets (TIME-019 through TIME-036) → Jira TIME-25 through TIME-36 — all Done;
  see `implementation_log.md` for the full ticket-by-ticket mapping if needed.

## Last Completed Work
TIME-048 (Jira TIME-47): Admin Dashboard Foundation (Web)
- Bootstrapped `web/` from scratch (no scaffold existed — first ticket in this run to touch the
  web platform): Next.js 16 + TypeScript + Tailwind 4 + Firebase Auth
- Role-protected `/admin` dashboard: Overview (metrics + integration status), Users (search +
  pagination), Invites (codes + waitlist), Subscriptions, Feedback — all consuming real backend
  data, no mocked/dead-end pages
- Confirmed with the user before proceeding: the ticket sequence implied the backend already had
  everything, but only user-listing and invite-code management existed as admin endpoints. Added
  GET /api/v1/admin/subscriptions/feedback/integrations/metrics/waitlist (all new, admin-gated) so
  the dashboard has real data everywhere rather than dead ends
- Also fixed GET /api/v1/admin/users: added a `search` param and a real `total` count (was
  hardcoded to `len(users)`, always equal to the page size)
- 11 new backend tests (17 total in test_admin.py); full suite 226/226 (excluding 2 known-flaky
  Stripe tests)
- `getAuth()` (Firebase) validates its API key eagerly and throws even during `next build`'s
  static prerendering when the key is empty — fixed by making auth construction lazy
  (`getFirebaseAuth()`), only touched at actual runtime use, guarded by `isFirebaseConfigured`
- This Next.js/React version's ESLint enforces `react-hooks/set-state-in-effect`, which flags any
  synchronous setState in an effect not immediately followed by async work in the same branch —
  fixed by deriving loading state from data (`data === null && error === null`) instead of a
  separate boolean, which also surfaced and fixed a latent bug (error message never cleared on a
  later successful fetch)
- `npm run build` and `npm run lint` both clean

Full history of TIME-034 through TIME-047 is in `implementation_log.md` and `change_summary.md`.

## Current Active Task
Phase 12 (Admin Dashboard) is now complete. Next up: TIME-049 (Slack Integration), starting Phase
13 (Integrations Expansion) — Slack OAuth, message read, action-item detection, user approval
before task creation. Also see known_issues.md — the deferred UsableTimeService timezone-awareness
pass (to actually subtract routine/meal/commute/sleep blocks from usable time, and to make Celery
beat/notification timing per-user-local instead of UTC-only) is unblocked and still worth
scheduling soon rather than continuing to defer it across more tickets.

## iOS HealthKit Decision Point (deferred from TIME-042, still open)
TIME-042 only built the backend contract (ingest a wake_time signal, gate on health_data consent,
trigger a morning replan suggestion). The actual iOS-side HealthKit read integration
(`ios/.../HealthService.swift`, `HKHealthStore` authorization request, Info.plist usage-description
strings, calling `POST /api/v1/sleep/events` after reading sleep analysis samples) was not built in
TIME-044 either — it needs a real device with HealthKit entitlements/authorization UI, which is a
different kind of iOS work than TIME-044's WidgetKit target (no HealthKit involved there). Still
worth a deliberate decision (own ticket vs. folding into a later iOS tranche) — flag to the user
before scoping that work.

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
