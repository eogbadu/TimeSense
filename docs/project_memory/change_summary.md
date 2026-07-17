# Change Summary

## 2026-07-17 — TIME-250 (Capture: live "detected" results)

- The bottom Capture section now shows what TimeSense actually detected after a capture (time,
  priority, task type, schedule fit) instead of a static "can detect" poster; idle keeps the
  capability tiles for onboarding. Uses fields the /capture response already returns (no backend
  change). Expanded CapturedTask + lastCaptured; shared DetectTile. iOS built.

## 2026-07-17 — TIME-249 (Capture: tap outside to dismiss keyboard)

- Tapping outside the Capture text field now lowers the keyboard and unfocuses the field
  (contentShape + onTapGesture on the scroll content); controls still work. iOS built.

## 2026-07-17 — TIME-248 (remove Now screen's static signal-chip row)

- Removed the five hard-coded, non-tappable chips (Calendar/Routine/Location/Time/Tasks) near the top
  of the Now screen — a false affordance that duplicated the live context cards + the Why sheet. Now:
  analyzed banner → recommendation → context cards. iOS built. (Future option, not built: a live
  tappable signal strip.)

## 2026-07-17 — TIME-244..247 (second on-device feedback batch)

- (244) Gmail scan found nothing — broadened the query from `is:unread newer_than:7d category:primary`
  to `in:inbox is:unread newer_than:30d`; (245) the Disconnect button no longer wraps on long provider
  rows (lineLimit/fixedSize); (246) the Why-sheet Energy signal now uses Apple Health *activity*
  (steps) when there's no sleep sample, so connecting Health actually powers it; (247) an alternative's
  Why sheet no longer calls the higher-ranked top pick "a slightly weaker fit" — reasons are now
  score-aware ("Ranked higher overall").
- Tests: email 15, explainer +3 (activity energy ×2, rank-aware alt ×1). iOS build clean.

## 2026-07-17 — TIME-239..243 (post-deploy UX + reasoning bug batch)

- Five on-device fixes after the first Render deploy: (243) scheduled tasks are now explained by
  their own time, not a nonsensical free-before-next-meeting line; (242) opening an alternative in
  the Why sheet no longer mislabels it as the recommended action (isTopPick flag); (241) email scan
  shows a result banner (scanned/found counts) on iOS + web; (240) connected providers show a
  Disconnect button — new GET /integrations/status + DELETE /email/disconnect; (239) tabs now slide
  on tap/swipe via a horizontal pager + custom bottom bar (a stock TabView doesn't animate).
- New tests: test_integrations_status.py (3), test_explanation_reasoning.py (2). iOS/web build clean.
- Trade-off (239): all five screens mount at launch. Follow-up: on-device gesture-feel check.

## 2026-07-17 — TIME-233..238 (Render deploy debugging — backend LIVE)

- Fixed the deploy cascade on a real Render account; backend + Postgres + Redis + worker are LIVE at
  https://timesense-api.onrender.com, Google Calendar OAuth works E2E, iOS works off-LAN.
- (233) coerce postgres:// → postgresql+asyncpg:// + wire DATABASE_URL fromDatabase (zero hand-entered
  DB secrets); (234) bind gunicorn to $PORT; (235) run migrations from the entrypoint not preDeploy
  (Render preDeploy lacks the wired DATABASE_URL); (236) rename redis→cache to force a fresh Free
  instance (Render blocks in-place Starter→Free); (237) iOS device builds point at the deployed API;
  (238) migration d7e8f9a0b1c2 adds created_at/updated_at server_default now() to 10 tables that
  broke INSERTs on Postgres (fixed the Google Calendar connect 500).

## 2026-07-14 — TIME-214..217 (Email → task detection, Gmail v1)

- New read-only Gmail integration: connect (OAuth + encrypted tokens + refresh), fetch recent
  unread/Primary emails (subject/snippet only, never bodies), detect tasks via the shared detector,
  and review/approve them. Gated on a new email_content consent + premium; never auto-creates tasks.
- Backend: gmail_oauth, EmailIntegration/EmailActionItem, EmailService (connect/fetch/scan/confirm/
  reject), /integrations/gmail/* + /email/* routers, migrations a4b5c6d7e8f9 + b5c6d7e8f9a0.
- iOS: Gmail connect row + new EmailTasksView (consent → scan → approve/dismiss). Suite 524; iOS built.
- Follow-ups: Outlook; Android/web review UIs; background polling; due-date extraction.

## 2026-07-11 — TIME-213 (score-based, consistent recommendation confidence)

- Confidence now reflects the pick's real 0-100 engine score via one score_to_confidence() helper,
  shown consistently on /now, /now/why, /now/recommendation (was a flat 0.50-0.95 heuristic on two
  surfaces + hardcoded literals on a third, which disagreed). Push eligibility unchanged (75/0.75
  aligned). Removed dead compute_confidence. No client change. Suite 501.

## 2026-07-11 — Jira: marked the 53 leftover "To Do" tickets Done

- The 53 remaining "To Do" (canonical copies of logical TIME-118..170) were all verified shipped work;
  transitioned to Done via scripts/mark_todo_done.py. Project now 205 tickets, all Done, 0 To Do.

## 2026-07-11 — Jira cleanup (removed 2,034 duplicate tickets)

- Project had 2,239 issues but only 205 distinct tickets; deleted the 2,034 duplicates (one canonical
  kept per summary) → 205 total, 0 duplicate summaries.
- Root cause fixed: create_jira_tickets.py get_existing_tickets() now paginates the whole project via
  nextPageToken (was reading only the first ~100 issues, so every full run re-created all tickets).
- New scripts/dedupe_jira_tickets.py (resumable one-off). No app code changed.

## 2026-07-11 — TIME-212 ("Why this recommendation?" sheet — summary at top)

- The iOS explanation sheet showed the plain-language Summary at the very bottom; moved it directly
  under the action header (above "Signals analyzed"). Layout-only; iOS built.

## 2026-07-11 — TIME-211 (fix inverted geofence arrive/leave notifications)

- Bug: leaving home said "You're at Home", arriving said "You left Home". The TIME-105 requestState/
  CLRegionState approach read the stale cached location right at the crossing, inverting the direction.
- Fix: on enter/exit request a fresh fix and derive inside/outside from the real distance to the place
  center (didUpdateLocations), deduped; fall back to the raw event direction on fix failure. Seed/place-
  sync path unchanged. iOS built; on-device walk test still required.

## 2026-07-10 — TIME-208..210 (acceptance-rate learning + per-user acceptance on Insights)

- TIME-208: user_preference_fit is now continuous — the observed acceptance rate acc/(acc+rej) once an
  action type has ≥5 reactions (was a binary +0.2 bump); neutral 0.5 below the floor.
- TIME-209: WeeklyInsight gains recommendations_shown/accepted, recommendation_acceptance_rate,
  mean_confidence (migration f3a4b5c6d7e8), from the impression→outcome log scoped to the user's week;
  null when no impressions.
- TIME-210: "Recommendations accepted" stat surfaced on iOS + web Insights (rate + "N of M shown").
  Suite 498; iOS built; web build clean. Android parity = CI follow-up.

## 2026-07-10 — TIME-205..207 ("What TimeSense has learned" transparency surface)

- New GET /api/v1/recommendations/learned (LearnedPreferencesService) → plain-language prefers/avoids/
  avoids-at-time from recommendation_events (not premium-gated).
- Surfaced in iOS Learned Patterns (built) and the web Insights page (built + screenshot). Suite 495.

## 2026-07-10 — TIME-202..204 (Learning — Phase 3, engine learns from telemetry)

- Revived the built-but-unused apply_feedback seam: build_feedback_summary (from recommendation_events)
  wired into the main /now, /now/recommendation, and both push run_engine sites (no-op without history).
- USER_OFTEN_ACCEPTS boost (-15 penalty); time-of-day rule (AVOIDED_AT_THIS_TIME +20) — action types
  rejected repeatedly at the current part of day get demoted.
- Completes the Guardrails→Telemetry→Learning plan. Suite 493.

## 2026-07-10 — TIME-196..201 (Recommendation telemetry — Phase 2, impression→outcome loop)

- RecommendationEvent → real impression→outcome log: typed columns + migration + repository
  (record_impression/set_outcome/acceptance_stats/calibration_buckets).
- /now logs a consent-gated impression + returns its id; feedback echoes the id and records the
  outcome (agree/disagree/snooze); admin GET /admin/recommendations/metrics = acceptance rate +
  calibration. recommendation_events added to privacy export. iOS/web built; Android unverified.
- Full loop live. Optional follow-up: per-user WeeklyInsight acceptance columns. Suite 489.

## 2026-07-10 — TIME-189..195 (Capture guardrails — Phase 1 of Guardrails→Telemetry→Learning)

- Backend: CaptureRequest validators (tz/type_hint/lat-lng/dates/whitespace), CaptureService output
  clamps (minutes/dates/title) + prompt-injection fencing, near-duplicate dedupe, enriched analytics.
- Clients: 2000-char cap on iOS/web/Android capture inputs (Android leaner payload intentional).
- TIME-190 hardened a flaky time-dependent calendar-sync test (pinned clock). Suite 477 passed.
- Reconstructed from the (lapsed) Ultraplan cloud plan; approved direction, shipped standalone.

## 2026-07-10 — TIME-185..188 (Agree/Disagree on the Best Next Action screen)

- Two-stage feedback replacing Done/Snooze/Not-now: Agree → Done/Snooze in place; Disagree →
  record + surface a different recommendation.
- **TIME-185 backend:** first-class agree/disagree signals; disagree "demotes, don't hide" via a
  new RECENTLY_DISAGREED reason code + 3h demote window + penalty (not the not_now 4h hide). 462 tests.
- **TIME-186 iOS / TIME-187 Android / TIME-188 web:** two-stage button swap (local stage reset per
  task id) + agree/disagree feedback calls; Android also gained its first Now feedback plumbing.
- Standalone on the existing feedback endpoint; signals are telemetry-ready for the impression log.
  iOS built; web built + screenshotted; Android compile-unverified (no JDK).

## 2026-07-10 — TIME-184 (imminent appointment > context-switch nudge)

- One penalty in scoring/penalties.py: a generic context_switch nudge (work/home/sleep) is suppressed
  when a calendar event is within the hour, so an imminent appointment reliably surfaces.
- Fixes the long-standing flaky test_calendar_sync test (near-tie at "night"). Suite 458 passed, 0 failures.

## 2026-07-10 — TIME-182 & TIME-183 (mobile "Connect" UI — plan C complete)

- **TIME-182 (iOS):** Settings ▸ Connections (ConnectionsView) — Connect buttons for Google/Outlook/
  Slack that GET /integrations/{provider}/authorize and open the consent URL in an
  ASWebAuthenticationSession (callback scheme "timesense"). iOS BUILD SUCCEEDED; new file registered
  in the Xcode target.
- **TIME-183 (Android):** the same screen via an ACTION_VIEW intent + a timesense://integrations
  deep-link filter (MainActivity singleTask). Compile unverified (no JDK); mirrors existing patterns.
- Plan "C" done: backend handshakes (Google/Outlook/Slack) + mobile Connect UI on both platforms.
  Everything activates once the provider OAuth app credentials are set.

## 2026-07-10 — TIME-180 & TIME-181 (Outlook + Slack OAuth handshakes)

- **TIME-180:** net-new `MicrosoftCalendarProvider` (Graph /me/calendarView + /me/events) registered
  as "microsoft", plus `microsoft_oauth` + `/integrations/microsoft/{authorize,callback}`. The Google
  callback was refactored into a shared `_authorize`/`_callback` both calendar providers use.
- **TIME-181:** `slack_oauth` (v2 authorize + oauth.v2.access, ok-check) + `/integrations/slack/*`
  storing the token via `SlackService.connect` (scan→task already existed).
- All three OAuth handshakes (Google/Outlook/Slack) now built + unit-tested; each activates when its
  CLIENT_ID/SECRET are set. Suite 457 passed. Backend integrations track (plan "C→B") complete.

## 2026-07-10 — TIME-178 & TIME-179 (universal intro trial + mobile Premium wiring)

- **TIME-178 (backend):** `SubscriptionService.is_premium` grants Premium for the account's first
  `intro_trial_days` (14) with no payment; `/me/entitlement` routes through it (status "trialing").
  Unlocks every Premium gate for new users. 444 tests pass; existing gate tests age the account.
- **TIME-179 (mobile):** iOS `AppState` + Android `AppViewModel` fetch `/subscriptions/me/entitlement`
  on sign-in and set `isPremium` (was hardcoded false). Fixes mobile Insights (everyone saw the gate)
  and unblocks the Premium-gated Connect flows. iOS BUILD SUCCEEDED; Android unverified (no JDK).
- Diagnosis that prompted this: mobile Insights UI + backend were both fine, but `isPremium` was never
  wired, so the real insights were unreachable for all users.

## 2026-07-09 — TIME-177 (backend OAuth handshake + Google Calendar)

- New /api/v1/integrations/google/authorize (Premium → consent URL + signed state) and /callback
  (verify state → exchange code server-side → store tokens encrypted via CalendarService.connect →
  deep-link back). New oauth_state.py (HS256 signed/expiring state) + google_oauth.py (URL + exchange).
- Scope calendar.events (writes still approval-gated). 503 until GOOGLE_CLIENT_ID/SECRET set.
- 11 new tests; suite 442 passed (+1 pre-existing unrelated failure — see known_issues). Backend only.

## 2026-07-09 — TIME-174/175/176 (web polish: dev badge, Why explainer, app-icon logo)

- **TIME-174:** `devIndicators:false` in next.config — removes the Next dev "N" badge.
- **TIME-175:** web Now "Why this recommendation?" disclosure → GET /api/v1/now/why (summary,
  colour-coded signals, decision factors, alternatives). New WhyPanel.tsx + appTypes WhyResponse.
- **TIME-176:** reusable SVG `Mark` (gradient ring + sparkle) replaces the plain `.orb` in all
  wordmarks; new app/icon.svg favicon; dropped the 1.2 MB PNG favicon (kept as OG image).
- Web-only, no backend changes; `cd web && npm run build` passes; all verified via screenshots.

## 2026-07-09 — TIME-173 (Terms of Service page)

- New public `web/app/terms/page.tsx` (linked from the footer, cross-linked with Privacy) — a
  TimeSense-specific ToS: service scope (suggestions you approve), accounts, subscriptions & billing
  (14-day trial requires payment, Free Basic after; Apple/Google/Stripe; no card numbers), acceptable
  use, content + AI license, third-party connections, disclaimers callout, liability, termination.
- Reuses the `.legal` styles from TIME-172; no new CSS. `cd web && npm run build` passes; verified
  via headless Chrome. **No app-store links** (real URLs still pending). No backend changes.

## 2026-07-09 — TIME-171 & TIME-172 (Web companion + marketing polish)

- **TIME-171 Insights (web):** new `web/app/app/insights/page.tsx` + Insights tab in the /app shell.
  Fetches `GET /api/v1/insights/weekly`; Premium users get their weekly summary + coloured stat cards,
  non-Premium users (403 SUBSCRIPTION_REQUIRED) get a cosmic upgrade gate with preview mini-charts and
  an "Upgrade in the mobile app" CTA. Completes Now·Today·Capture·Insights for signed-in users.
- **TIME-172 Privacy Policy (web):** new public `web/app/privacy/page.tsx` (linked from the footer) —
  a TimeSense-specific, plain-language policy (opt-in-only audio, approval-first calendar, AI parsing
  under no-training terms, sub-processors, export/delete). New scoped `.legal` prose styles in globals.css.
- Both: `cd web && npm run build` passes; verified via headless Chrome. No backend changes.

## 2026-07-05 — TIME-057 (Jira TIME-63) App Store & Play Store Prep

- New docs/launch/: privacy_policy.md, app_store_listing.md (metadata + review notes + App Privacy
  labels), play_store_listing.md (metadata + Data Safety), store_assets_checklist.md, README.md
- Docs-only; grounded in the real product (consents, integrations, OpenAI, encrypted tokens,
  export/delete). Assets + console entry + legal review are the user's step.

## 2026-07-05 — TIME-056 (Jira TIME-62) Security Review and Hardening

- Token encryption at rest: EncryptedString (Fernet) on Calendar/Slack/Teams/Notion access/refresh
  tokens — ciphertext at rest, plaintext via ORM, no migration (impl=Text); tolerates legacy plaintext
- SecurityHeadersMiddleware (nosniff/DENY/no-referrer/CSP/+HSTS in prod)
- In-process rate limiting on POST /capture (30/min) + DELETE /privacy/account (5/hr) → 429
- Audit: Stripe webhook already verifies signatures (documented). 7 new tests; suite 306/306
- Follow-up: Redis-backed rate limiting for multi-instance

## 2026-07-05 — TIME-055 (Jira TIME-61) Privacy: Data Export + Account Deletion

- PrivacyService: export_data (portable JSON of all user-owned tables, tokens redacted) +
  delete_account (delete user → DB cascade erases everything; analytics purged; Firebase user
  deleted best-effort)
- GET /api/v1/privacy/export, DELETE /api/v1/privacy/account?confirm=true
- Test conftest now enforces SQLite FKs so cascade is tested like Postgres
- 7 new tests; suite 299/299 (excl. 2 flaky); verified via a real-Postgres round-trip
- Deferred: per-consent-type revocation cleanup (follow-up)

## 2026-07-05 — TIME-054 (Jira TIME-60) Error Monitoring + Analytics (backend) — Phase 14 start

- Sentry-optional monitoring (`app/core/monitoring.py`, no-op without SENTRY_DSN) wired into the
  lifespan + error handlers (500s captured with path/method context)
- Analytics pipeline: analytics_events table + AnalyticsService.track() gated on the `analytics`
  consent; emits task_captured from /capture; GET /api/v1/admin/analytics counts
- 9 new tests; suite 292/292 (excl. 2 flaky). Client (iOS/Android) analytics deferred to a follow-up

## 2026-07-05 — TIME-064 / TIME-065 (Jira TIME-58 / TIME-59) Local-run + auth cleanups

- **TIME-064:** config.py resolves the root `.env` by absolute path so `cd backend && uvicorn` loads
  real settings (was silently loading none → real Firebase auth broke at runtime). Removed the temp
  backend/.env symlink.
- **TIME-065:** `/users/me` now syncs the DB `user.role` from the Firebase token claim (the single
  source of truth), so granting admin is one step. require_admin unchanged. Suite 283/283.

Both surfaced while bringing the full stack up locally for the user's admin dashboard.

## 2026-07-05 — TIME-063 (Jira TIME-57) Fix Alembic migration ordering

**What changed:** recommendation_feedback (g7h8i9j0k1l2, FK→tasks) now depends on the tasks
migration (a1b2c3d4e5f7) instead of being a parallel sibling; merge migration e55970716568 tuple
updated. A fresh Postgres `alembic upgrade head` now completes (was failing with "relation tasks
does not exist"). Found while standing up a real local Postgres; masked by tests' create_all.

**Verified:** single head; fresh-DB migrate clean (31 tables); backend boots + health 200; suite
281/281.

## 2026-07-05 — TIME-062 (Jira TIME-56) Client Firebase Config (iOS + Android)

**What changed:**
- iOS: added firebase-ios-sdk (pinned 11.x → 11.15.0; 12.x needs Swift tools 6.1 > Xcode 16.0) +
  GoogleSignIn-iOS (8.x); linked FirebaseAuth/FirebaseCore/GoogleSignIn to TimeSense; added
  GoogleService-Info.plist (gitignored). Real AuthService now compiles + app runs with real Firebase.
- Android: replaced placeholder google-services.json with the real timesense-eb7ec config.
- Committed project.pbxproj + Package.resolved; added .gitignore rules for xcuserdata/ + .swiftpm/.

**Verified:** iOS Simulator build SUCCEEDED; app launches with FirebaseApp.configure() on the real
plist (no crash).

**Still needed:** web/.env.local (web apiKey/appId), console sign-in providers, on-device run.

## 2026-07-05 — TIME-053 (Jira TIME-55) Google Assistant Integration

**What changed:**
- backend/app/integrations/google_assistant.py — Dialogflow webhook fulfillment dispatching the same
  5 actions as the iOS App Intents (WhatToDoNext/StartFocus/LogLunch/MarkDone/ReplanDay); reuses /now
  best-task logic, MealRepository, TaskRepository
- POST /api/v1/assistant/webhook (Firebase-gated as the account-linked identity)
- 10 new tests

**What did not change / limits:**
- No Dialogflow agent / Actions-on-Google setup (and that platform was shut down June 2023) — this
  is the webhook contract + intent→action mapping, unit-tested
- No account-linking/OAuth (Firebase token stands in); ReplanDay opens the app (no headless replan);
  no new backend actions invented; no Android App Actions (that's the iOS App Intents surface)

**Next:**
- Client Firebase config (console) for end-to-end sign-in; further Phase 13 items

## 2026-07-05 — TIME-061 (Jira TIME-54) Backend Real Firebase Token Verification

**What changed:**
- `app/core/firebase.py` now robustly parses the real .env service account (single-line, newlines
  flattened to literal `\n`) via `json.loads(raw.replace("\\n","\n"), strict=False)`. The Admin SDK
  now actually initializes for project timesense-eb7ec, so the backend verifies REAL Firebase ID
  tokens (get_current_user already called verify_id_token).
- 4 new unit tests (test_firebase_init.py) using a fabricated key.

**Verified:**
- Out-of-band real init logs "initialized … for project: timesense-eb7ec" (was silently failing);
  full suite 271/271 excluding 2 known-flaky.

**What did not change / still needed:**
- Client Firebase config is NOT in .env — iOS GoogleService-Info.plist, Android google-services.json,
  web apiKey/appId/authDomain must come from the Firebase console per registered app. Backend is the
  only piece unblocked by the .env credential.
- Real service account stays in .env (gitignored), never committed.

**Next:**
- Client Firebase config (console downloads) for true end-to-end sign-in; then TIME-053 (Google Assistant)

## 2026-07-05 — TIME-060 (Jira TIME-53) iOS HealthKit Sleep/Wake Read Integration

**What changed:**
- HealthService.swift (HKHealthStore behind #if canImport(HealthKit)): requests sleepAnalysis read
  auth, reads the latest sleep window, POSTs wake_time/sleep_start/source=healthkit to the existing
  /api/v1/sleep/events. Read-only.
- HealthKit entitlement + NSHealthShareUsageDescription; a "Connect Apple Health" row in Settings
- Completes the mobile half of the TIME-042 sleep/wake feature; no backend changes

**Verified:**
- Simulator build ✓ (HealthKit really linked — confirmed via the debug dylib's load commands +
  HKHealthStore symbol); app installs/launches under the new bundle id com.aetheranalytics.timesense
- Live Health auth prompt / real sleep data / on-device run are the user's device step

**What did not change:**
- No backend changes; no HealthKit writes; no background HKObserverQuery sync (foreground read only)

**Next:**
- TIME-053: Google Assistant Integration

## 2026-07-05 — TIME-059 (Jira TIME-52) iOS Real Apple Signing Configuration

**What changed:**
- iOS project now points at the user's real Apple Developer account (Team WB5NV894N5) with the
  registered App ID: app+widget bundle IDs renamed com.timesense.app → com.aetheranalytics.timesense
  (+ .TimeSenseWidget), App Group group.com.timesense.app → group.com.aetheranalytics.timesense
  across both entitlements + WidgetSnapshot.appGroupID

**Verified:**
- Simulator build succeeds after the rename
- Signed 'Any iOS Device' build with the App Store Connect API key authenticated with Apple and
  reached provisioning — blocked only by "no registered device" (the user's remaining step). Config
  validated against the real account.

**What did not change:**
- Android applicationId (com.timesense.app) — separate Google Play concern, untouched
- No on-device install (no device attached), no Firebase/plist changes

**Next:**
- TIME-060: iOS HealthKit sleep/wake read integration (now that signing + entitlements can provision)

## 2026-07-05 — TIME-052 (Jira TIME-51) Siri Shortcuts / App Intents

**What changed:**
- 5 App Intents (WhatToDoNext, LogLunch, StartFocus, MarkDone, ReplanDay) + an AppShortcutsProvider
  exposing them to Siri and the Shortcuts app, under ios/TimeSense/Intents/
- Intents reuse APIClient + existing /now, /meals, /tasks endpoints; ReplanDay opens the app
  (replans require approval)
- The iOS Simulator gap is resolved (user installed a runtime): verified with a real scheme build +
  Simulator install/launch + App Intents metadata extraction

**What did not change:**
- No new backend endpoints; no new networking layer
- No Siri voice E2E (device-only) and no backend round-trip E2E (real Firebase still placeholder) —
  build + Simulator run + intent registration are the verified bar

**Next:**
- TIME-053: Google Assistant Integration
- Then a dedicated HealthKit ticket (deferred from TIME-042) — now buildable/Simulator-verifiable,
  but on-device runs still need a real Apple Developer account for the HealthKit entitlement

## 2026-07-05 — TIME-051 (Jira TIME-50) Notion Integration

**What changed:**
- New TaskSourceProvider abstraction (distinct from MessageSourceProvider) — for structured
  external task sources; NotionTaskSource reads a Notion database's pages, extracting title + due
  from structured properties (no LLM)
- notion_integrations + notion_import_items tables; NotionService (connect/disconnect/scan/import/
  dismiss) with the same approval gate (scan → pending; import → Task, source=notion, due carried)
- POST /api/v1/notion/connect, /disconnect, /scan (Premium-gated), /pending,
  /items/{id}/import, /items/{id}/dismiss
- notion settings in config.py; "notion" added to TaskSource

**What did not change:**
- No LLM detection — Notion rows are already structured tasks (the reason for its own abstraction)
- No auto-import — import is the explicit approval gate
- No real Notion OAuth app / callback; no write-back to Notion; no ongoing sync; token plain Text

**Next:**
- TIME-052: Siri Shortcuts / App Intents

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
