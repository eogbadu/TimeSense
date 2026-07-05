# Context Summary

**Last updated:** 2026-07-05

## Current Build State

Phases 0–2 merged to main. Phases 3 (subscriptions), 4 (mobile shells), early Phase 5 tasks,
Phase 8 (Recommendation Engine V1), Phase 9 (Routines/Meals/Commute/Sleep-Wake), Phase 10
(Notifications, Widgets, Ambient Surfaces), Phase 11 (Insights and Learning Summary), and Phase 12
(Admin Dashboard) complete. Phase 13 (Integrations Expansion) in progress — TIME-049 (Slack),
TIME-050 (Teams), TIME-051 (Notion), TIME-052 (Siri Shortcuts / App Intents) done; TIME-053 (Google
Assistant) next, plus a queued HealthKit ticket (deferred from TIME-042).

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
- `POST /api/v1/slack/connect` (Premium), `DELETE /api/v1/slack/disconnect`, `POST /api/v1/slack/`
  `scan` (Premium — reads messages, LLM-detects action items, creates *pending* suggestions only),
  `GET /api/v1/slack/pending`, `POST /api/v1/slack/actions/{id}/confirm` (approval gate — creates a
  Task, source=slack), `.../reject` (TIME-049)
- `POST /api/v1/teams/*` — same shape as slack (connect/disconnect/scan/pending/confirm/reject),
  reads MS Teams via Microsoft Graph, Task source=teams (TIME-050). Slack + Teams share one
  source-neutral `ActionItemDetectionService`
- `POST /api/v1/notion/*` (connect/disconnect/scan/pending + items/{id}/import|dismiss) — reads a
  Notion database's pages as candidate tasks (structured title/due extraction, NO LLM), user
  imports → Task source=notion (TIME-051). Uses a separate `TaskSourceProvider` abstraction, not
  the chat-oriented `MessageSourceProvider`
- No new endpoints for TIME-043 — `notification_mode` (gentle/balanced/active_coach) already had
  read/write via `PATCH /api/v1/users/me/preferences`; TIME-043 only added the behavior that acts
  on it (NotificationService.maybe_send_morning_checkin/evening_checkout/learning_prompt), driven
  by a Celery beat schedule rather than a user-facing route

Database tables: users, profiles, preferences, personalities, onboarding_states, consent_records,
subscription_records, replan_requests, notifications, notification_events, tasks,
internal_reminders, recommendation_feedback, routine_assumptions, meal_events, commute_events,
sleep_wake_events, weekly_insights, calendar_integrations, pending_calendar_actions,
slack_integrations, slack_action_items, teams_integrations, teams_action_items, notion_integrations,
notion_import_items. (Correction: there is no separate "notification_preferences" table — the
notification_mode field lives directly on user_preferences; a prior version of this file listed
that table incorrectly.)

Backend tests: 267, all passing (see Known Problems re: 2 flaky Stripe-network tests).

Mobile app shells:
- iOS SwiftUI: bottom tab navigator (Now/Today/Capture/Insights/Settings), AuthService with `#if canImport(FirebaseAuth)` stubs, CaptureViewModel + CaptureView wired to backend. `xcodebuild → BUILD SUCCEEDED`. Plus (TIME-044) a `TimeSenseWidgetExtension` WidgetKit target with three home-screen widgets (Usable Time, Next Up, Do Next) reading a shared App-Group snapshot the app writes. Insights tab (TIME-046) now shows a real weekly summary + stats grid behind the Premium gate.
- Android Kotlin/Compose: bottom nav, AuthViewModel, CaptureViewModel + CaptureScreen wired to backend. `./gradlew assembleDebug → BUILD SUCCESSFUL`. Plus (TIME-045) two Jetpack Glance AppWidgets (Usable Time, Next Event), each reading its own Preferences state written by NowViewModel/TodayViewModel. Insights tab (TIME-046) mirrors iOS's real content.
- Both platforms (TIME-047): Settings > Preferences has a "Learned Assumptions" screen to view/edit the 6 RoutineAssumption blocks via the existing GET/PATCH /api/v1/routines endpoints — no backend changes.
- iOS (TIME-052): 5 App Intents under `ios/TimeSense/Intents/` (what to do next, log lunch, start focus, mark done, replan day) + an AppShortcutsProvider exposing them to Siri/Shortcuts. **The iOS Simulator runtime is now installed** (iOS 18.0) — scheme builds + `simctl` runs work; use `xcodebuild -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'` going forward (see known_issues.md, RESOLVED).

Web companion (TIME-048, new): Next.js 16 (App Router) + TypeScript + Tailwind 4 + Firebase Auth
(env-var-driven, no real project yet). Role-protected `/admin` dashboard: metrics/integration
status, user search, invite codes, subscriptions, feedback review. `npm run build`/`npm run lint`
both clean.

## Jira Key Mapping (recent — see decision_log.md/implementation_log.md for full history)
- TIME-060 (net-new) → Jira TIME-53 (iOS HealthKit Sleep/Wake Read Integration) — **Done (PR #46 merged 2026-07-05)**
- TIME-059 (net-new) → Jira TIME-52 (iOS Real Apple Signing Configuration) — **Done (PR #45 merged 2026-07-05)**
- TIME-052 (impl seq) → Jira TIME-51 (Siri Shortcuts / App Intents) — **Done (PR #44 merged 2026-07-05)**
- TIME-051 (impl seq) → Jira TIME-50 (Notion Integration) — **Done (PR #43 merged 2026-07-05)**
- TIME-050 (impl seq) → Jira TIME-49 (Microsoft Teams Integration) — **Done (PR #42 merged 2026-07-05)**
- TIME-049 (impl seq) → Jira TIME-48 (Slack Integration) — **Done (PR #41 merged 2026-07-05)**
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
TIME-060 (Jira TIME-53): iOS HealthKit Sleep/Wake Read Integration
- `HealthService.swift` (HKHealthStore behind `#if canImport(HealthKit)`): requests sleepAnalysis
  read auth, reads the latest sleep window (allAsleepValues; earliest start + latest end = wake),
  POSTs {wake_time, sleep_start, source:"healthkit"} to /api/v1/sleep/events. Read-only. Publishes
  a HealthConnectState surfaced by a "Connect Apple Health" Settings row
- HealthKit entitlement + NSHealthShareUsageDescription added; completes the TIME-042 sleep/wake
  feature's mobile half — no backend changes
- Simulator build ✓; HealthKit really linked (verified in the Debug build's TimeSense.debug.dylib:
  HealthKit.framework load command + _OBJC_CLASS_$_HKHealthStore ref). App installs + launches
  cleanly under the new bundle id com.aetheranalytics.timesense. Live auth prompt + real sleep data
  + on-device run are the user's device step.

### (previous) TIME-059 (Jira TIME-52): iOS Real Apple Signing Configuration
- Wired the iOS project to the user's real Apple Developer account (Team WB5NV894N5, from .env):
  DEVELOPMENT_TEAM on app + widget targets; bundle IDs renamed com.timesense.app →
  com.aetheranalytics.timesense (+ .TimeSenseWidget); App Group group.com.timesense.app →
  group.com.aetheranalytics.timesense across both entitlements + WidgetSnapshot.appGroupID
- Simulator build ✓. Signed 'generic/platform=iOS' build with the App Store Connect API key
  authenticated with Apple and reached provisioning — blocked ONLY on "no registered device" (the
  user plugs in their iPhone to finish). Config validated against the real account. Temp .p8 key
  was materialized in scratchpad (decoding the .env's literal-\n), used, and deleted — never
  committed. Android applicationId untouched (separate Google Play concern).

### (previous) TIME-052 (Jira TIME-51): Siri Shortcuts / App Intents
- 5 App Intents under `ios/TimeSense/Intents/` (WhatToDoNext, LogLunch, StartFocus, MarkDone,
  ReplanDay) + an AppShortcutsProvider exposing them to Siri and the Shortcuts app with
  \(.applicationName)-prefixed phrases
- Intents call APIClient.shared and reuse existing /now, /meals, /tasks endpoints + the
  NowContext/NowTask decodables — no new networking. ReplanDay opens the app (replans require
  in-app approval, never headless)
- **Verified against the now-available iOS Simulator** (user installed a runtime this session):
  scheme build → BUILD SUCCEEDED; booted iPhone 16 sim + install/launch → app runs to its sign-in
  screen without crashing; all 5 intents present in the app's Metadata.appintents bundle
- Not yet: Siri *voice* invocation (real device only) and backend round-trip (real Firebase still
  placeholder — the app sits at the auth gate)

Full history of TIME-034 through TIME-052 is in `implementation_log.md` and `change_summary.md`.

## Current Active Task
Next up: TIME-053 (Google Assistant Integration) — "Expose TimeSense actions to Google Assistant."
Likely Android-side (App Actions / shortcuts.xml or a companion), analogous to TIME-052's iOS App
Intents. Two message-source integrations (Slack, Teams) share `ActionItemDetectionService`; Notion
stands alone on `TaskSourceProvider`; a 3rd chat source is the trigger to unify Slack+Teams tables
(decision_log.md). Also see known_issues.md — the deferred UsableTimeService timezone-awareness pass
(subtract routine/meal/commute/sleep from usable time + per-user-local Celery timing) is unblocked
and still worth scheduling soon.

## iOS device runs — remaining user steps (post TIME-059/060)
Real signing (Team WB5NV894N5, App ID com.aetheranalytics.timesense) and the HealthKit entitlement
are wired. For an actual on-device run the user: registers their iPhone's UDID (automatic when the
device is connected in their Xcode, or manually in the portal), then builds/runs from Xcode. The
live HealthKit authorization prompt + real sleep data are inherently device/Simulator-interactive
(not CLI-drivable). Real Firebase Auth is still a placeholder, so backend round-trips (intents,
HealthKit sync) can't be exercised end-to-end until a real Firebase project is configured.

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
