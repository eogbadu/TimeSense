# Changelog

All notable changes to TimeSense are documented here.

Format: `[DATE] TIME-### Short description`

---

## Unreleased

### Phase 14 — Beta Hardening and Launch Readiness

- [2026-07-05] TIME-057: App Store + Play Store prep — docs/launch/ with a publishable privacy policy, iOS + Android store listings, App Privacy / Play Data Safety label answers, App Review notes, and a required-assets checklist (all grounded in actual data practices; assets/console entry are the user's step)
- [2026-07-05] TIME-056: Security hardening — integration OAuth tokens now encrypted at rest (Fernet EncryptedString on Calendar/Slack/Teams/Notion; no migration), security-headers middleware, and in-process rate limiting on POST /capture + DELETE /privacy/account (429 + Retry-After). Audit confirmed Stripe webhook already verifies signatures
- [2026-07-05] TIME-055: Privacy — data export + account deletion — GET /api/v1/privacy/export (portable JSON bundle of all the user's data, OAuth tokens redacted) and DELETE /api/v1/privacy/account?confirm=true (erases the user + cascades all their data + deletes the Firebase Auth user); test conftest now enforces SQLite foreign keys so cascade is exercised
- [2026-07-05] TIME-054: Error monitoring + analytics (backend) — Sentry-optional error monitoring (no-op without a DSN) wired into the error handlers; a privacy-respecting analytics pipeline (analytics_events table + AnalyticsService gated on the `analytics` consent), emits task_captured from /capture, GET /api/v1/admin/analytics event counts. Client analytics deferred

### Fixes

- [2026-07-06] TIME-102: Visual polish — darkened light-mode secondary text for better contrast/legibility (chips, card hierarchy, and section headers were delivered across the screen redesigns)
- [2026-07-06] TIME-101: Settings home regrouped into AI Planning / Integrations / Privacy / Account for a more structured, mature feel
- [2026-07-06] TIME-100: Subscription redesigned — Current Plan card, 'Basic includes' checklist, and an indigo 'Premium unlocks' card + Upgrade CTA
- [2026-07-06] TIME-099: Privacy & Consent redesigned — signal rows with status labels (Calendar/Health/Location/Audio) + data controls (Delete/Export) + encrypted-never-sold note
- [2026-07-06] TIME-098: Calendar screen redesigned — hero + 'Connect your calendar' + Connect CTA + supported providers (Google/Apple) + privacy note
- [2026-07-06] TIME-097: Working Hours redesigned — an explainer banner ('why this matters'), Start/End rows, and a Repeat day selector (Mon-Fri)
- [2026-07-06] TIME-096: Renamed 'Learned Assumptions' to 'Learned Patterns' and redesigned it — explainer banner + icon rows with confidence/source + an add button
- [2026-07-06] TIME-095: Insights locked state now previews the AI value — a 'Your AI Insights' banner + sample preview cards (best focus window, patterns, schedule balance, routine consistency) instead of a bare paywall
- [2026-07-06] TIME-094: Redesigned Capture to feel AI-native — hero capture icon, clearer AI copy, quick type chips, a voice affordance, and a 'TimeSense can detect' row
- [2026-07-06] TIME-093: Redesigned the 'Why this recommendation?' screen — a Recommended-action + confidence-ring header, 'Signals analyzed' (Calendar/Time of day/Location/Priority/Energy with checks), 'Alternatives considered', and a plain-English summary
- [2026-07-06] TIME-092: Redesigned the Today page — date + progress header, an 'AI Recommended Now' card, and a 'Smart Plan' grouped into Morning/Afternoon/Evening with tap-to-complete rows
- [2026-07-06] TIME-091: Now context chips (Calendar/Routine/Location/Time/Tasks) now all fit on one row — removed the horizontal scroll
- [2026-07-06] TIME-090: Redesigned the Now page to the approved mockup — analysis banner, context chips, a richer Best Next Action card with an inline confidence bar and category icon, and an 'Other good options' list
- [2026-07-06] TIME-089: "Why This Recommendation?" is now a full breakdown — recommended action, the context used (calendar/time/energy/location/task), decision factors, alternatives considered, a confidence score, and a summary; opens as a sheet. Backed by a real explanation pipeline with an audit trail
- [2026-07-06] TIME-088: Renamed the Now recommendation-explanation link from "Why this?" to "Why This Recommendation?"
- [2026-07-06] TIME-058: v1 close-out — beta smoke-test script + manual beta checklist + go/no-go release checklist (docs/launch/); v1 is feature-complete
- [2026-07-06] TIME-087: On-device demos work — the app now reaches the Mac's dev backend over the LAN (via its .local name) with local-network HTTP allowed, instead of failing on localhost
- [2026-07-05] TIME-086: Working hours are configurable (Settings ▸ Working Hours) — auto-scheduling and feasibility now use your hours instead of a fixed 8am–9pm
- [2026-07-05] TIME-085: TimeSense now auto-places new tasks into the next open slot in your day (using its time estimate, your working hours, and existing blocks) — with a one-tap 'Undo' on Today
- [2026-07-05] TIME-084: Feasibility warnings — when the best task can't be finished before it's due (given its estimate, your working hours, and existing blocks), Now shows a gentle heads-up with the next realistic slot
- [2026-07-05] TIME-083: TimeSense learns your pace — completing a task briefly asks 'How long did that take?' (~15/30/60m), but only while it's still learning that kind of task, then stops. Feeds the per-user duration estimates
- [2026-07-05] TIME-082: Task duration brain — every task now gets a realistic time estimate from a seed lookup table (works without the LLM), plus a per-user learned table the assistant refines from real durations over time (foundation for scheduling + feasibility)
- [2026-07-05] TIME-081: 'Usable minutes' on Now now measures time left until your LOCAL midnight (was UTC), so the number is correct for your timezone
- [2026-07-05] TIME-080: Now is local-time-aware — fixed the greeting (was UTC-based) and added a gentle wind-down 'moment' when it's late locally and nothing is urgent, instead of always pushing a task
- [2026-07-05] TIME-079: 'Why this?' now consistently justifies the recommended task instead of occasionally arguing to rest/do it later — tightened the LLM prompt and reframed the time-of-day energy hints
- [2026-07-05] TIME-078: 'Why this?' now loads lazily on tap (new GET /now/why) so the Now screen stays instant — the LLM explanation is only fetched when you ask for it
- [2026-07-05] TIME-077: Now shows two alternative options and a real 'Why this?' — the LLM explains why the best task beats the alternatives given the time of day, likely energy, free time, and deadlines (deterministic fallback when the LLM is unavailable)
- [2026-07-05] TIME-076: Settings rows now work — Profile, Subscription, Notifications, Appearance (light/dark), Privacy, Calendar, About are real screens; added Sign Out and a working Delete My Data (erases account + signs out)
- [2026-07-05] TIME-075: Now hero card has a 'Why this?' explanation (hidden by default, expands on tap) — e.g. "Recommended because it's due today and it fits your 240 free minutes."
- [2026-07-05] TIME-074: Now quick actions fixed — Snooze/Not-now now work (record feedback; /now hides snoozed/dismissed tasks so a new best task appears) and the action labels no longer wrap
- [2026-07-05] TIME-073: Premium visual redesign (calm/minimal, Apple-like) — white cards on a soft-gray canvas, deep indigo accent, SF Pro typography, soft shadows, redesigned Now hero. Elevates every screen via the shared design tokens
- [2026-07-05] TIME-072: Capture extracts dates without the LLM — when OpenAI is unavailable (e.g. 429/quota), a rule-based parser pulls today/tomorrow/weekday/"Month Dayth"/"at 5pm" from the text so tasks still get a due date (and a cleaner title), and Now's best-task prioritization works
- [2026-07-05] TIME-071: Today tab now shows untimed pending tasks (your captured to-dos), not just scheduled blocks — so you can see your full list (Now still shows the single best next action by design)
- [2026-07-05] TIME-070: iOS recovers from 401s — a launch race showed "session expired" on a valid session with no way back to sign-in; APIClient now refreshes the token and retries on 401, and a persistent 401 signs out to the sign-in screen
- [2026-07-05] TIME-069: Add backend/run_dev.py dual-stack dev launcher — the iOS Simulator connects to IPv6 localhost (::1) but `uvicorn app.main:app` binds IPv4 only; run_dev.py serves both ::1 and 127.0.0.1. Documented in CLAUDE.md
- [2026-07-05] TIME-068: Now/Today now reload when you return to the tab (e.g. after capturing a task) and support pull-to-refresh — SwiftUI .task didn't re-run on tab switches since TabView keeps views mounted
- [2026-07-05] TIME-067: Fix day-view task visibility — iOS APIClient no longer mangles query strings (URL.appending(path:) was percent-encoding '?query' → 404 on Today and every query-param endpoint); backend Now now surfaces unscheduled just-captured tasks (were excluded as neither scheduled-today nor overdue)
- [2026-07-05] TIME-066: Fix iOS invisible UI — the project had no asset catalog, so DesignTokens named colors (TextPrimary/Surface/Background/etc.) resolved to invisible fallbacks and nearly the whole UI rendered white-on-white; added Assets.xcassets with all colorsets (light+dark) + an AppIcon set
- [2026-07-05] TIME-065: Sync DB user role from the Firebase token claim — `/users/me` now mirrors the claim into the DB `role`, so granting admin is one step (set the claim) instead of also updating the DB row; the claim is the single source of truth
- [2026-07-05] TIME-064: Load `.env` from the repo root regardless of working directory — `cd backend && uvicorn` previously loaded no env (looked for backend/.env), silently disabling real Firebase auth at runtime; config.py now resolves the root .env by absolute path
- [2026-07-05] TIME-063: Fix Alembic migration ordering — recommendation_feedback (FK→tasks) and tasks were parallel sibling branches, so a fresh `alembic upgrade head` could run feedback before tasks and fail; repointed feedback to depend on the tasks migration. A fresh Postgres now migrates end-to-end (tests missed it because they build schema via create_all)

### Auth & Native Capabilities

- [2026-07-05] TIME-062: Client Firebase config (iOS + Android) — linked firebase-ios-sdk (11.x) + GoogleSignIn to the iOS app and added GoogleService-Info.plist; replaced the Android google-services.json placeholder with the real timesense-eb7ec config. iOS builds + runs with real Firebase (web config still pending)
- [2026-07-05] TIME-061: Backend real Firebase token verification — robust service-account parse so the Admin SDK initializes with the real .env credential (project timesense-eb7ec); the backend now verifies real Firebase ID tokens (client config files still needed for end-to-end)

### iOS Signing & Native Capabilities

- [2026-07-05] TIME-060: iOS HealthKit sleep/wake read — HealthService reads Apple Health sleep analysis (read-only) and syncs the latest wake to POST /api/v1/sleep/events (completes the TIME-042 sleep/wake feature's mobile half); HealthKit entitlement + usage string + a "Connect Apple Health" Settings row
- [2026-07-05] TIME-059: iOS real Apple signing config — DEVELOPMENT_TEAM + bundle IDs + App Group aligned to the real Apple Developer account (com.aetheranalytics.timesense, Team WB5NV894N5); verified the App Store Connect key provisions against the account (blocked only on a registered device)

### Phase 13 — Integrations Expansion

- [2026-07-05] TIME-053: Google Assistant integration — Dialogflow fulfillment webhook exposing the same 5 actions as the iOS App Intents (what to do next, log lunch, start focus, mark done, replan day); POST /api/v1/assistant/webhook, backend-only, unit-tested intent→action mapping
- [2026-07-05] TIME-052: Siri Shortcuts / App Intents — 5 App Intents (what to do next, log lunch, start focus, mark done, replan day) exposed to Siri and the Shortcuts app via an AppShortcutsProvider; verified with a real iOS Simulator build + install/launch (Simulator runtime now available)
- [2026-07-05] TIME-051: Notion integration — read a Notion database's pages as candidate tasks (structured title + due extraction, no LLM), user-imported into Tasks; POST /api/v1/notion/connect, /scan (Premium-gated), /pending, /items/{id}/import|dismiss. Introduces a TaskSourceProvider abstraction, distinct from the chat-oriented MessageSourceProvider
- [2026-07-05] TIME-050: Microsoft Teams integration — read Teams chat messages via Microsoft Graph, LLM-detect action items, approve-before-task-creation; POST /api/v1/teams/connect, /scan (Premium-gated), /pending, /actions/{id}/confirm|reject. Extracts a shared source-neutral action-item detection service reused by Slack + Teams
- [2026-07-05] TIME-049: Slack integration — read recent Slack messages, LLM-detect action items, surface each as a pending suggestion the user must confirm before it becomes a Task (never auto-created); POST /api/v1/slack/connect, /scan (Premium-gated), /pending, /actions/{id}/confirm|reject

### Phase 12 — Admin Dashboard

- [2026-07-05] TIME-048: Admin dashboard foundation (web) — bootstraps web/ (Next.js + Firebase Auth) with a role-protected /admin dashboard (metrics, user search, invite codes, subscriptions, feedback review); adds the missing backend admin endpoints (subscriptions/feedback/integrations/metrics/waitlist) alongside it

### Phase 11 — Insights and Learning Summary

- [2026-07-05] TIME-047: Learned assumptions settings — real "Learned Assumptions" screen on iOS and Android (Settings > Preferences), view/edit the 6 RoutineAssumption blocks via the existing GET/PATCH /api/v1/routines endpoints, no backend changes
- [2026-07-05] TIME-046: Weekly insights generation — weekly_insights table + InsightsService aggregating task/meal/sleep/commute/feedback signals over a completed week into an LLM-summarized (fallback-templated) report; GET /api/v1/insights/weekly + /history (Premium-gated); real iOS and Android Insights screens

### Phase 10 — Notifications, Widgets, Ambient Surfaces

- [2026-07-05] TIME-045: Android widgets — Glance AppWidgets for Usable Time and Next Event, each reading its own ViewModel-written Preferences state (no shared cross-widget state needed)
- [2026-07-05] TIME-044: iOS widgets — WidgetKit extension with Usable Time, Next Up, and Do Next home-screen widgets, backed by an App-Group-shared snapshot the host app writes (no independent network/auth in the extension)
- [2026-07-05] TIME-043: Notification modes and learning prompts — notification_mode (gentle/balanced/active_coach) now drives morning check-in/evening check-out/learning-prompt behavior via NotificationService + a Celery beat schedule

### Phase 9 — Routines, Meals, Commute, Sleep/Wake

- [2026-07-05] TIME-042: Sleep/wake signal integration — POST /api/v1/sleep/events (health-data-consent gated), GET /api/v1/sleep/today; late wake (>=45min past the assumed sleep-routine wake time) proposes a morning replan via the existing approval flow
- [2026-07-05] TIME-041: Commute detection — POST /api/v1/commute/detect (location-consent gated), confirm/reject flow
- [2026-07-05] TIME-040: Meal tracking — POST /api/v1/meals, GET /api/v1/meals/today (skip inference), skipped_meals in recommendations
- [2026-07-05] TIME-039: Routine assumptions — GET/PATCH /api/v1/routines with default-seeded sleep/meal/hygiene blocks per user

### Phase 8 — Recommendation Engine V1

- [2026-07-04] TIME-038: Feedback collection — POST /api/v1/recommendations/feedback (done/snooze/not_now); recommendations exclude snoozed/recently-dismissed tasks
- [2026-07-04] Fix: merge 4 divergent Alembic migration heads accumulated across TIME-030/033/036 into a single head

### Phase 0 — Repository Bootstrap

- [2026-07-03] TIME-001: Initialize repository structure, project memory, docs, skills, and workflow files
