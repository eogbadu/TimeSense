# Change Summary

## 2026-07-05 — TIME-050 (Jira TIME-49) Microsoft Teams Integration

**What changed:**
- TeamsMessageSource (Microsoft Graph /chats/{id}/messages) reusing the MessageSourceProvider ABC
- teams_integrations + teams_action_items tables; TeamsService (connect/disconnect/scan/confirm/
  reject) mirroring SlackService, with the same approval gate (scan → pending; confirm → Task)
- POST /api/v1/teams/connect, /disconnect, /scan (Premium-gated), /pending, /actions/{id}/confirm,
  /actions/{id}/reject
- Extracted the LLM action-item detection into a shared source-neutral ActionItemDetectionService
  (Slack keeps a SlackDetectionService alias for compat)
- "teams" added to the TaskSource literal

**What did not change:**
- No auto-created tasks — scan only creates pending suggestions; confirm is the approval gate
- No real Azure AD app / OAuth callback / Graph change-notifications — token posted to /connect
- No unified Slack+Teams schema (deferred to a 3rd source), no token encryption (plain Text)

**Next:**
- TIME-051: Notion Integration

## 2026-07-05 — TIME-049 (Jira TIME-48) Slack Integration

**What changed:**
- MessageSourceProvider abstraction + SlackMessageSource (reads Slack via conversations.history)
- slack_integrations + slack_action_items tables; SlackService with connect/disconnect/scan/
  confirm/reject
- POST /api/v1/slack/connect, DELETE /disconnect, POST /scan (Premium-gated), GET /pending,
  POST /actions/{id}/confirm, POST /actions/{id}/reject
- LLM-based action-item detection (SlackDetectionService) with graceful non-action fallback
- "slack" added to the TaskSource literal

**What did not change:**
- No auto-created tasks — scan only creates pending suggestions; confirm is the approval gate
- No real Slack OAuth flow / Events API / signature verification — token posted to /connect like
  the calendar flow; no server-side OAuth callback
- No token encryption beyond how CalendarIntegration already stores tokens (plain Text)
- No background auto-scan

**Next:**
- TIME-050: Microsoft Teams Integration (same MessageSourceProvider abstraction)

## 2026-07-05 — TIME-048 (Jira TIME-47) Admin Dashboard Foundation (Web)

**What changed:**
- Bootstrapped `web/` from scratch: Next.js 16 (App Router) + TypeScript + Tailwind 4 + Firebase
  Auth (env-var-driven, no real project configured yet)
- Role-protected `/admin` dashboard: Overview (metrics + integration status), Users (search +
  pagination), Invites (list/create/disable codes + waitlist), Subscriptions, Feedback
- Backend: added GET /api/v1/admin/subscriptions, /feedback, /integrations, /metrics, /waitlist
  (all admin-gated, new); extended GET /admin/users with search + a real total count (was
  hardcoded wrong before)
- 11 new backend tests (17 total in test_admin.py)

**What did not change:**
- No public-facing web companion (landing page, signup, regular-user routes) — admin only
- No real Firebase project — same placeholder gap as iOS/Android
- No Stripe checkout/billing UI, no write actions beyond existing invite code create/disable
- No automated web test suite — verification is `npm run build`/`npm run lint` plus backend pytest

**Next:**
- TIME-049: Slack Integration — starts Phase 13

## 2026-07-05 — TIME-047 (Jira TIME-46) Learned Assumptions Settings

**What changed:**
- New "Learned Assumptions" screen on both iOS and Android, reached from Settings > Preferences
- Lists the 6 RoutineAssumption types (sleep/breakfast/lunch/dinner/morning+evening hygiene) with
  friendly labels, formatted time ranges, and an "Edited" indicator when customized
- Tapping a routine opens an edit flow (time pickers) that calls the existing
  PATCH /api/v1/routines/{routine_type} and updates the list in place

**What did not change:**
- No backend changes at all — reuses GET/PATCH /api/v1/routines from TIME-039 as-is
- No editing of any other learned data (meals, commute, sleep) — only routine blocks

**Next:**
- TIME-048: Admin Dashboard Foundation (Web) — starts Phase 12

## 2026-07-05 — TIME-046 (Jira TIME-45) Weekly Insights Generation

**What changed:**
- `weekly_insights` table + InsightsService aggregating tasks/meals/sleep/commute/feedback data
  over a completed Monday-Sunday week, with an LLM-generated (or templated-fallback) 2-3 sentence
  summary
- `GET /api/v1/insights/weekly` (generates the most recent completed week if not yet generated),
  `GET /api/v1/insights/history` — both Premium-gated
- A weekly Celery job (Monday 5am UTC) proactively generates each active user's insight
- Real iOS and Android Insights screens (summary + stats grid) replacing the static placeholders

**What did not change:**
- No "current week so far" view — only fully completed weeks
- No trend charts/graphs across multiple weeks beyond a simple history list
- No backend change to how meal skips are detected — most_skipped_meal only counts explicitly
  logged skips, a known simplification

**Next:**
- TIME-047: Learned Assumptions Settings

## 2026-07-05 — TIME-045 (Jira TIME-44) Android Widgets

**What changed:**
- Two Jetpack Glance home-screen widgets: Usable Time and Next Event, each reading its own
  Glance-managed Preferences state written directly by NowViewModel/TodayViewModel after a
  successful fetch (no shared cross-widget state needed — simpler than iOS since Android
  AppWidgets run in the same process as the app)
- NowViewModel/TodayViewModel converted to AndroidViewModel to get an Application Context
- Extracted a pure `nextUpcomingEvent()` function from TodayViewModel + 6 new JVM unit tests

**What did not change:**
- No best-next-action widget (Android ticket scope is 2 widgets, not iOS's 3)
- No periodic background refresh — app-triggered only, same policy as iOS
- No backend changes

**Next:**
- TIME-046: Weekly Insights Generation (Phase 11)
- Consider a third Android widget for full parity with iOS's best-next-action widget, if wanted

## 2026-07-05 — TIME-044 (Jira TIME-43) iOS Widgets

**What changed:**
- New TimeSenseWidgetExtension (WidgetKit) target with three widgets: Usable Time, Next Up,
  Do Next — all read a shared App Group snapshot (`group.com.timesense.app`) the host app writes
  after its normal `/now` and `/timeline/today` fetches
- NowViewModel/TodayViewModel now update that shared snapshot and call
  `WidgetCenter.shared.reloadAllTimelines()` after each successful load
- No backend changes — this ticket is entirely iOS/WidgetKit

**What did not change:**
- No independent network/auth in the widget extension (reads the snapshot only)
- No interactive widgets, no lock-screen circular/inline families, no APNs-triggered refresh
- No real Apple Developer Team/App Group registration (still an open question)

**Next:**
- TIME-045: Android Widgets
- A real device build will need the App Group registered against a real Apple Developer Team

## 2026-07-05 — TIME-043 (Jira TIME-42) Notification Modes and Learning Prompts

**What changed:**
- `notification_events` table: audit trail + once-per-day dedup for morning_checkin/
  evening_checkout/learning_prompt
- `NotificationService` gained three mode-gated methods: gentle -> evening check-out only;
  balanced -> morning + evening check-ins; active_coach -> both check-ins + a learning prompt
  that asks the user to confirm their still-default "sleep" RoutineAssumption (TIME-039), gated
  on a 14-day placeholder Learning Mode window
- `backend/app/workers/notification_tasks.py` — three Celery tasks + a UTC beat schedule
  (8am/10am/9pm) driving the above per active user

**What did not change:**
- No new preference storage/API — `notification_mode` already existed on UserPreferences
- No real Celery beat/worker execution test (no Redis/Docker in this environment)
- No data-driven Learning Mode end date — still a fixed 14-day placeholder
- No push notification delivery (APNs/FCM) — still just Notification rows

**Next:**
- TIME-044: iOS Widgets
- Consider the deferred UsableTimeService timezone-awareness ticket (now unblocked since all
  Phase 9 signals exist) before going too much further, since it also affects Celery beat times

## 2026-07-05 — TIME-042 (Jira TIME-41) Sleep/Wake Signal Integration

**What changed:**
- `sleep_wake_events` table: wake_time, sleep_start (nullable), source (healthkit/manual),
  replan_request_id (nullable FK)
- `POST /api/v1/sleep/events` (403 without `health_data` consent granted) — records the event and,
  if wake_time is >=45min past the user's "sleep" RoutineAssumption (TIME-039) assumed wake minute,
  proposes a morning replan via the existing NotificationService.propose_replan/ReplanRequest
  approval flow (TIME-015); dedupes so a second late wake the same day doesn't double-propose
- `GET /api/v1/sleep/today`
- No new approve/reject endpoints — a suggested replan goes through the existing
  `/api/v1/notifications/replans/{id}/approve|reject` routes like any other replan

**What did not change:**
- No iOS HealthKit read integration, entitlements, or permission UI — backend contract only, same
  split TIME-041 used for its location-permission piece; flagged as its own decision point
- No real per-user timezone handling — same UTC-only simplification as RoutineAssumption/
  UsableTimeService/CommuteService
- No automatic replan execution — user approval is still required

**Next:**
- TIME-043: Notification Modes and Learning Prompts (Phase 10)
- The deferred UsableTimeService timezone-awareness pass (subtracting routine/meal/commute/sleep
  blocks from usable time) is now unblocked since all Phase 9 signals exist

## 2026-07-05 — TIME-041 (Jira TIME-40) Commute Detection

**What changed:**
- `commute_events` table: derived commute windows (direction, start/end, estimated_minutes, status)
- `POST /api/v1/commute/detect` (403 without `location_tracking` consent granted) — haversine
  displacement (>500m) + elapsed-time (5–120min) heuristic on a submitted ping batch; creates a
  pending CommuteEvent + an approval_needed Notification if a commute is detected
- `GET /api/v1/commute/pending`, `POST /api/v1/commute/{id}/confirm`, `.../reject`
- Reused existing `consent_records` (location_tracking) and Notification/approval infrastructure
  rather than building new mechanisms for either

**What did not change:**
- No raw lat/lng persistence — only the derived window is stored
- No calendar-event-location correlation (no such table exists yet)
- No mobile location-permission UI or CoreLocation/FusedLocationProvider integration

**Next:**
- TIME-042: Sleep/Wake Signal Integration

## 2026-07-05 — TIME-040 (Jira TIME-39) Meal Tracking (Lightweight)

**What changed:**
- `meal_events` table: logs breakfast/lunch/dinner as eaten/skipped/eating_while_working
- `POST /api/v1/meals` — log a meal event; `GET /api/v1/meals/today` — today's status per meal,
  inferring "skipped" once that meal's TIME-039 routine window passes with nothing logged
- `GET /api/v1/recommendations` gained `skipped_meals: list[str]` — context only, no scoring changes

**What did not change:**
- No calories/macros/nutrition tracking (explicit product rule)
- TaskScorer ranking/weights unchanged — meal status is exposed, not scored
- No mobile UI for logging meals

**Next:**
- TIME-041: Commute Detection

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
