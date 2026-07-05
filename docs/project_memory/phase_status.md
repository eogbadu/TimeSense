# Phase Status

## Current Phase
Phase 13: Integrations Expansion — TIME-049/050 done; TIME-051 (Notion) next.

## Staleness Warning (2026-07-04)
This file's "Completed Phases" and per-phase acceptance-criteria checkboxes were not kept
current between TIME-011 and TIME-037 — `context_summary.md` asserts Phases 3–5 (and parts
of 6/7) are done (backed by passing test_subscriptions.py, test_referrals.py, test_tasks.py,
test_timeline.py, test_now.py, test_recommendations.py), but the checkboxes below were never
ticked off session-to-session. Phase 8 below has been verified and reconciled as part of
TIME-038. Phases 3–7 checkboxes still need a reconciliation pass against actual code/tests
before being trusted — do not assume unchecked = not built.

## Completed Phases
- Phase 0: 2026-07-03 — Bootstrap files, docs, skills, memory, workflow docs. TIME-001 done.
- Phase 1: 2026-07-03 — Backend foundation. FastAPI, PostgreSQL, Redis/Celery, Firebase Auth, migrations. TIME-002–TIME-006 done.
- Phase 2: 2026-07-03 — Core data model and auth. User/Profile/Preferences, onboarding state, assistant personality, consent records, admin role enforcement. TIME-007–TIME-010 done.
- Phase 8: 2026-07-04 — Recommendation Engine V1. Usable time calculator, task scorer, GET /api/v1/recommendations (best + alternatives + LLM why), LLM Gateway, feedback collection (done/snooze/not_now) with suppression integrated into the recommendation flow. TIME-034–TIME-038 done (PRs #26–#28, TIME-038 in this session).

## Phase 2 Acceptance Criteria
- [x] Authenticated user can be created/resolved (get_or_create_user)
- [x] User preferences can be saved and read
- [x] Consent records can be created and read (append-only audit trail)
- [x] Assistant personality can be saved
- [x] Admin-only route protection works (403 for non-admins, 401 for unauthenticated)
- [x] Tests cover core auth and data model behavior (35 tests passing)

## Phase 3 Acceptance Criteria (upcoming)
- [ ] User can start 14-day Premium trial
- [ ] Stripe customer created for web subscriptions
- [ ] Subscription status updates from Stripe webhooks
- [ ] Apple/Google subscription notification handler stubs exist
- [ ] Expired/canceled users move to Free Basic Mode
- [ ] Premium gates work (feature flag check)
- [ ] Referral reward logic implemented or stubbed with tests
- [ ] Admin can view subscription/trial status

## Phase 8 Acceptance Criteria
- [x] GET /api/v1/recommendations returns best task with why string
- [x] Returns up to 2 alternatives
- [x] why falls back gracefully when LLM unavailable
- [x] GET /api/v1/now best_task uses TaskScorer ranking
- [x] POST /api/v1/recommendations/feedback records done/snooze/not_now
- [x] signal=done marks the task done
- [x] Snoozed/not_now tasks excluded from recommendations until snooze_until passes / cooldown expires
- [x] All tests pass (152 total in full suite)

## Phase 9 Progress
- [x] TIME-039 (Jira TIME-38): Routine Assumptions Model — routine_assumptions table, GET/PATCH
      /api/v1/routines, default seeding. NOT yet integrated into UsableTimeService (see known_issues.md).
- [x] TIME-040 (Jira TIME-39): Meal Tracking (Lightweight) — meal_events table, POST /api/v1/meals,
      GET /api/v1/meals/today (skip inference via TIME-039 routine windows), skipped_meals surfaced
      in GET /api/v1/recommendations as context only.
- [x] TIME-041 (Jira TIME-40): Commute Detection — commute_events table, POST /api/v1/commute/detect
      (gated on location_tracking consent) + confirm/reject flow, reusing existing consent/notification
      infrastructure. No calendar-event-location correlation yet (no such table exists).
- [x] TIME-042 (Jira TIME-41): Sleep/Wake Signal Integration — sleep_wake_events table,
      POST /api/v1/sleep/events (gated on health_data consent) + GET /api/v1/sleep/today; late wake
      (>=45min past the "sleep" RoutineAssumption's assumed wake minute) proposes a morning replan
      via the existing NotificationService.propose_replan/ReplanRequest approval flow. iOS HealthKit
      read integration is out of scope (backend contract only, per TIME-041's precedent).

## Phase 10 Progress
- [x] TIME-043 (Jira TIME-42): Notification Modes and Learning Prompts — notification_events table,
      NotificationService gained mode-gated maybe_send_morning_checkin/evening_checkout/
      learning_prompt methods (gentle/balanced/active_coach), a concrete routine-confirmation
      learning prompt, and a Celery beat schedule (untested — no Redis/Docker in this environment).
- [x] TIME-044 (Jira TIME-43): iOS Widgets — TimeSenseWidgetExtension (WidgetKit) with Usable Time/
      Next Up/Do Next widgets, backed by an App-Group-shared snapshot (no independent network/auth
      in the extension). Both targets verified with `xcodebuild -target ... -sdk iphonesimulator`
      (no Simulator runtimes installed in this environment, so scheme-based builds don't resolve a
      destination — see known_issues.md). Real device build still needs a real Apple Developer Team.
- [x] TIME-045 (Jira TIME-44): Android Widgets — Usable Time + Next Event Glance AppWidgets, each
      reading its own ViewModel-written Preferences state (no shared cross-widget state needed,
      simpler than iOS since Android AppWidgets share the app's process). No best-next-action
      widget (2-widget scope per implementation_sequence.md, not iOS's 3). Verified with
      `./gradlew assembleDebug` and `./gradlew test` (6 new unit tests, all passing) using the
      Android-Studio-bundled JBR as JAVA_HOME (no system `java` in this environment).

## Phase 11 Progress
- [x] TIME-046 (Jira TIME-45): Weekly Insights Generation — weekly_insights table,
      InsightsService aggregating tasks/meals/sleep/commute/feedback over a completed
      Monday-Sunday week into an LLM-summarized (fallback-templated) report;
      GET /api/v1/insights/weekly + /history (Premium-gated); real iOS and Android Insights
      screens. Weekly Celery job (Monday 5am UTC), untested in this environment (no Redis/Docker).
- [x] TIME-047 (Jira TIME-46): Learned Assumptions Settings — real "Learned Assumptions" screen
      on iOS and Android (Settings > Preferences) to view/edit the 6 RoutineAssumption blocks via
      the existing GET/PATCH /api/v1/routines endpoints; no backend changes. Both builds verified.

## Phase 12 Progress
- [x] TIME-048 (Jira TIME-47): Admin Dashboard Foundation (Web) — bootstrapped web/ from scratch
      (Next.js 16 + TypeScript + Tailwind 4 + Firebase Auth, no scaffold existed before this
      ticket). Role-protected /admin dashboard: metrics, integration status, user search, invite
      code management, subscriptions, feedback review. Added the missing backend admin endpoints
      (subscriptions/feedback/integrations/metrics/waitlist) since only user-listing and invite
      codes actually had admin endpoints before this ticket. 11 new backend tests (17 total in
      test_admin.py). `npm run build`/`npm run lint` clean.

## Phase 13 Progress
- [x] TIME-049 (Jira TIME-48): Slack Integration — MessageSourceProvider abstraction +
      SlackMessageSource; slack_integrations/slack_action_items tables; LLM action-item detection;
      scan creates *pending* suggestions (never Tasks) and confirm is the approval gate that
      creates a Task (source=slack). Premium-gated scan. No real Slack app (token posted to
      /connect like calendar). 14 new tests.
- [x] TIME-050 (Jira TIME-49): Microsoft Teams Integration — TeamsMessageSource (MS Graph) reusing
      the MessageSourceProvider abstraction; teams_integrations/teams_action_items tables; same
      scan→pending→confirm approval gate as Slack (Task source=teams). Extracted the LLM detection
      into a shared source-neutral ActionItemDetectionService (Slack keeps a compat alias). 12 new
      tests; Slack's 14 still green.

## Active Jira Tickets
- TIME-49 (impl TIME-050, Microsoft Teams Integration) — Done
- Next: TIME-051 (Notion Integration)

## Blockers
- None

## Next Phase
Phase 13 continues with TIME-050 (Teams), TIME-051 (Notion), etc.
