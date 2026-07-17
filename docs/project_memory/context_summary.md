# Context Summary

**Last updated:** 2026-07-17 (NOW-SCREEN DECLUTTER — TIME-248 (Jira TIME-2282, PR #273): removed the five static, non-tappable capsule chips (Calendar/Routine/Location/Time/Tasks) near the top of the Now screen (ContextChipsRow in NowView.swift) — a false affordance that duplicated the "analyzed your day" banner + the live context cards (ContextGrid/NowContextCards) + the "Why This Recommendation?" sheet. Decided in plan mode on industry-standard/user-friendliness grounds. iOS built. Future option (not built): a live tappable signal strip reflecting which signals drove the pick — needs per-signal state on /now (today only on /now/why). Earlier — SECOND ON-DEVICE FEEDBACK BATCH — TIME-244..247 (Jira TIME-2278..2281), all merged PRs #267-270: (244) Gmail scan found nothing — the query `is:unread newer_than:7d category:primary` was too narrow (Primary tab only, 7d), broadened gmail_source._QUERY → `in:inbox is:unread newer_than:30d` (still read-only format=metadata); (245) the Disconnect button wrapped to 2 lines on Google Calendar — ConnectionsView button lineLimit(1)+fixedSize+layoutPriority(1), name capped to 1 line; (246) the Why-sheet Energy signal only read a today sleep sample so connecting Apple Health did nothing unless you tracked sleep — the explainer's _health now falls back to today's DailyActivity (steps) → moderate energy "based on today's activity (N steps)" (mirrors context_builder which already did this); _health now returns a dict {energy,wake,sleep_hours,steps,source}; (247) an alternative's Why sheet mislabelled the real (higher-ranked) top pick as "a slightly weaker fit" because alt reasons only compared vs `best` — build_explanation now takes per-task alt_scores, a higher-scored alternative → "Ranked higher overall — the stronger pick right now", priority reason reworded "than this task", /now/why passes the score map. Tests: email 15, explainer +3. iOS built. Earlier — LIVE ON RENDER + POST-DEPLOY BATCH. Backend + Postgres + Redis + worker are DEPLOYED at https://timesense-api.onrender.com; Google Calendar OAuth works end-to-end; iOS works off the Mac LAN. TIME-233..238 (PRs #255-260) fixed the Render deploy cascade: (233) coerce postgres:// → postgresql+asyncpg:// + wire DATABASE_URL fromDatabase (API boots with zero hand-entered DB secrets); (234) bind gunicorn to $PORT (Render assigns it); (235) run `alembic upgrade head` from the container entrypoint (RUN_MIGRATIONS=1) not preDeployCommand (Render's preDeploy env lacks the wired DATABASE_URL) — keep api at 1 instance; (236) renamed redis→timesense-cache to force a fresh Free Key Value (Render blocks in-place Starter→Free downgrade; old Starter orphaned for the user to delete); (237) iOS resolveBaseURL sends physical-device builds to prodBaseURL=https://timesense-api.onrender.com (Simulator still localhost; API_BASE_URL scheme env still overrides); (238) migration d7e8f9a0b1c2 adds created_at/updated_at server_default now() to 10 tables (calendar_integrations + 9 more) whose hand-written migrations omitted it — fine on SQLite create_all, broke INSERTs on Postgres → fixed the Google Calendar connect 500. Alembic head = d7e8f9a0b1c2. Then the user tested on-device and filed a 5-fix batch TIME-239..243 (PRs #261-265, all merged): (243) recommendation reasoning now leads with a scheduled task's own time ("scheduled for 4:00 PM") instead of a nonsensical free-before-your-11am-meeting line for a 4pm appointment — recommendation_explainer.build_explanation, +test_explanation_reasoning.py; (242) opening an "also a good option" in the Why sheet mislabeled it as the recommended action — RecommendationExplanationSheet/RecommendedActionHeaderCard got an isTopPick flag (alternatives pass false → "About this option"/"Also a good option"); (241) email scan gave no feedback — iOS EmailTasksView.scan()+web /app/email now show a scan-result banner (scanSummary: "Scanned N emails · found M task(s)"); (240) connected providers had no Disconnect — new GET /api/v1/integrations/status ({google,microsoft,gmail,slack,notion} booleans) + the missing DELETE /api/v1/email/disconnect (calendar/slack/notion disconnect routes already existed), iOS ConnectionsView + web connections page load status on open and swap Connect↔Disconnect (each client maps provider→its disconnect path), +test_integrations_status.py; (239) tabs didn't visually move on swipe — a stock TabView doesn't animate content on selection change, so MainTabView is now a horizontal pager (5 screens offset by selected index, animated) + a custom .bar-material bottom bar; all screens stay mounted (per-tab state preserved), swipe stays discrete/thresholded so it won't fight vertical scroll or Today's row swipe. TRADE-OFF (239): all 5 screens mount at launch. FOLLOW-UP: on-device gesture-feel check for 239. Verified: backend pytest (status+reasoning tests pass), web npm build exit 0, iOS BUILD SUCCEEDED 0 errors. Earlier — DEPLOY-READY (Render) — TIME-228..231 (Jira TIME-2262..2265): repo is now deploy-ready. (228) backend container: gunicorn+uvicorn workers, non-root+curl+HEALTHCHECK, entrypoint.sh runs `alembic upgrade head` when RUN_MIGRATIONS=1 (compose backend sets it); (229) web container: next output:standalone + web/Dockerfile (node:20, NEXT_PUBLIC_* build args) + .dockerignore; (230) .env.example PRODUCTION override block + iOS Release URL documented; (231) render.yaml Blueprint (web+worker+beat+Postgres+Redis, secrets in sync:false group, migrations via preDeployCommand, DATABASE_URL needs +asyncpg) + docs/DEPLOY.md. Verified via review+pytest 535+npm build+YAML — Docker/Render NOT runnable here, user runs the actual build/deploy. TIME-232 (Jira TIME-2266) slimmed the blueprint for cost (~$48→~$20/mo): merged worker+beat into one worker service running embedded beat (celery worker --beat; keep at 1 instance), Redis→free plan, removed the web service (deploy web on Vercel free). Deferred: CI/CD (GitHub Actions), Redis-backed rate limiter (in-process today). USER OWNS: Render account, domain/TLS, secret values, prod OAuth redirect URIs, rotate exposed Android API key, store/legal (docs/launch/release_checklist.md). Earlier — NOTION CONNECT — TIME-226..227 (Jira TIME-2260..2261): added the missing Notion OAuth handshake (notion_oauth.py mirrors slack_oauth, Basic-auth non-expiring token; config notion_redirect_uri; /integrations/notion/{authorize,callback}, platform-aware) — Notion import flow already existed but only took a pasted token. Notion row added to web Connections + iOS ConnectionsView (generic authorize flow). docs/integrations_setup.md + .env.example updated (needs a PUBLIC Notion integration). Suite 535; web+iOS build clean. Follow-up: Notion import-review UI. Earlier — WEB COMPANION — Connections + Email review (TIME-223..225, Jira TIME-2257..2259): (223) OAuth callback is now platform-aware — signed state carries platform (mobile|web); decode_state/platform_from_state added, verify_state back-compat; config oauth_web_success/failure_redirect; authorize endpoints take a platform query param; default mobile → iOS unchanged; suite 531; (224) web /app/connections page + nav tab, connect Google/Outlook/Gmail/Slack via ?platform=web, reads ?status=connected&provider= on return, 403/503 handled; (225) web /app/email review — consent gate → scan → pending list Add task/Dismiss, 403/404 handled. web builds clean. Follow-ups: per-user connected-status endpoint; Outlook e2e; background email scan. NOTE (ops): to make OAuth actually connect on device you need a stable HTTPS URL — tunnel (ngrok) to test now, deploy backend+Postgres+Redis to a host (e.g. api.timesense.app) to go live; see docs/integrations_setup.md. Earlier — HOME UX BATCH — TIME-219..222 (Jira TIME-2253..2256): (219) Now/Today color refresh — added Cosmic.orange/red/yellow, spread warm colors across task types (shared taskCategoryStyle), warm→cool Today day-arc, "warmer dark" CosmicBackground (baseWarm #12172B) — direction picked from a color-preview artifact; (220) swipe between bottom tabs (MainTabView DragGesture); (221) Now "Tasks" card taps through to Today; (222) synced calendar events import into the task list as editable tasks (source="calendar", Task.calendar_event_id dedup, migration c6d7e8f9a0b1, POST /calendar/import, iOS imports after each sync, all-day skipped, one-way). Backend 528; iOS built. Earlier — DEV TESTING — TIME-218 (Jira TIME-2252): premium features were untestable on accounts past the 14-day intro trial (gate hidden in-app + PremiumUser endpoints 403). Added dev-only `premium_test_emails` config; SubscriptionService.is_premium also grants premium to listed emails (after sub + intro-trial, case-insensitive), empty by default. Set PREMIUM_TEST_EMAILS=you@example.com in backend/.env to test. Suite 526. Earlier — EMAIL → TASK DETECTION (Gmail v1) COMPLETE — TIME-214..217 (Jira TIME-2248..2251): read-only Gmail integration that detects tasks from recent unread/Primary email, on-demand, approval-gated — cloned the Slack pattern. TIME-214 Gmail OAuth connect (gmail_oauth: gmail.readonly, reuses Google app, own gmail_redirect_uri, + refresh_access_token = FIRST token-refresh in the codebase; EmailIntegration model + repo + service; /integrations/gmail/{authorize,callback}; migration a4b5c6d7e8f9). TIME-215 fetch+refresh+consent (email_content consent category; EmailSourceProvider+EmailMessage; GmailEmailSource fetches is:unread newer_than:7d category:primary via format=metadata — subject/sender/snippet only, NEVER the body; EmailService.fetch_recent refreshes expired tokens). TIME-216 scan→pending→approve (EmailActionItem model[message_id dedup]+repo+migration b5c6d7e8f9a0; EmailService.scan[consent+connected gated]→detect→dedup→pending, confirm=only Task path source="email", reject; /email/scan[premium,403 no-consent,404 not-connected], /email/pending, /email/actions/{id}/{confirm,reject}). TIME-217 iOS (ConnectionsView Gmail row + NavigationLink; new EmailTasksView: consent gate→Scan for tasks→pending list Add task/Dismiss; + email_content added to ConsentType Literal in schemas/consent.py). Backend suite 524; iOS BUILD SUCCEEDED. Read-only throughout, never sends/modifies mail, never auto-creates tasks. GOES LIVE once Google creds + the /integrations/gmail/callback redirect URI are registered (ops). FOLLOW-UPS (not started): Outlook/Microsoft (Graph Mail.Read); Android + web review screens (web needs a Connections page); background polling (Celery, refresh now exists); optional due-date extraction. Earlier — CONFIDENCE FIX — TIME-213 (Jira TIME-2247): recommendation confidence now reflects the pick's real 0-100 engine score via one score_to_confidence(score)=round(min(0.95,max(0.30,score/100)),2) helper (scoring/score.py), shown consistently on /now, /now/why, /now/recommendation. Was a flat 0.50-0.95 heuristic (compute_confidence, ignored the score) on /now+/now/why plus hardcoded per-candidate literals on /now/recommendation — two numbers that disagreed on one screen. Threaded per-task scores through _engine_rank_tasks/_ranked_candidates→build_explanation (so /now/why is right on alternatives too). Push eligibility unchanged (score_to_confidence(75)==0.75==threshold). Removed dead compute_confidence. No client change (iOS/web already render confidence*100). Suite 501. The confidence "seems off" thread is now CLOSED; deferred optional follow-ups: "margin over runner-up" nuance + cleaning vestigial per-candidate confidence= literals. Earlier — JIRA CLEANUP — the project had 2,239 issues but only 205 DISTINCT tickets; 2,034 were duplicates (all "To Do", e.g. TIME-108 had 65 copies) created by a bug in create_jira_tickets.py::get_existing_tickets() — it read only the first ~100 issues of the token-paginated search (never followed nextPageToken), so dedup was blind and every full run re-created all tickets. Fixed get_existing_tickets() to paginate the whole project; wrote scripts/dedupe_jira_tickets.py (resumable) which kept one canonical per summary (oldest Done, else oldest) and deleted 2,034 → 205 total, 0 duplicate summaries. Safety-verified all 42 memory-cited Jira keys kept. Then reconciled the 53 leftover "To Do" (canonical copies of logical TIME-118..170, all verified shipped work) → transitioned to Done via scripts/mark_todo_done.py. Project is now **205 tickets, ALL Done, 0 To Do**. STILL OPEN (paused): the CONFIDENCE-% issue — two inconsistent, score-decoupled confidence values (compute_confidence 0.5-0.95 flat heuristic on /now + /now/why vs hardcoded per-candidate literals on /now/recommendation); user was asked which fix direction but pivoted to the Jira question, so undecided. Earlier — UI FIX — TIME-212 (Jira TIME-2246): the iOS "Why this recommendation?" sheet (RecommendationExplanationSheet in NowView.swift) showed the plain-language Summary at the very bottom; moved it directly under the recommended-action header card, above "Signals analyzed". Layout-only; iOS BUILD SUCCEEDED. PR #223. Earlier — GEOFENCE BUG FIX — TIME-211 (Jira TIME-2245): leaving home fired "You're at Home" and arriving fired "You left Home" (consistent inversion). Root cause: since TIME-105, LocationService.swift derived crossing direction from requestState/CLRegionState, which reads the device's last CACHED location — stale right after a boundary crossing, so isInside was systematically inverted. Fix (fresh-location verify): on didEnter/didExit → requestLocation(); in didUpdateLocations compute inside/outside from real distance to the place center (ground truth), deduped via lastRegionState (extracted resolveCrossing helper); didFailWithError falls back to the raw event direction; pendingEvents is now [regionId: eventDirection]. Stationary seed/place-sync path (registerGeofence/reregisterGeofences → requestState → didDetermineState) preserved, still never notifies. Supersedes the TIME-105 requestState mechanism. iOS BUILD SUCCEEDED; ON-DEVICE WALK TEST STILL REQUIRED. PR #221. Earlier — DEFERRED FOLLOW-UPS DONE — TIME-208..210 shipped: (208) user_preference_fit is now CONTINUOUS = observed acceptance rate acc/(acc+rej) once an action type has ≥5 reactions (was a binary +0.2 bump), neutral 0.5 below the floor; (209) per-user WeeklyInsight acceptance columns — recommendations_shown/accepted, recommendation_acceptance_rate, mean_confidence (migration f3a4b5c6d7e8), populated from RecommendationEventRepository.acceptance_stats(...,user_id) scoped to the user's week, null when no impressions; (210) "Recommendations accepted" stat (rate + "N of M shown") on iOS StatsGrid + web Insights grid, rendered only when rate non-null. Backend suite 498; iOS BUILD SUCCEEDED; web build clean. Jira TIME-2242/2243/2244. ONLY remaining optional follow-up: Android acceptance/learned surfaces in CI (columns + endpoints already live). Earlier — GUARDRAILS→TELEMETRY→LEARNING PLAN COMPLETE — Phase 3 LEARNING TIME-202..204 shipped: revived the built-but-unused apply_feedback seam (build_feedback_summary from recommendation_events, wired into main /now + /now/recommendation + both push run_engine sites; no-op without history), USER_OFTEN_ACCEPTS boost (-15), time-of-day rule (AVOIDED_AT_THIS_TIME +20 for action types rejected repeatedly at the current part of day). Full loop LIVE end-to-end: capture(hardened)→recommend→impression logged→agree/disagree→outcome recorded→admin acceptance-rate/calibration→engine learns. Backend suite 493. "WHAT I LEARNED" SURFACE DONE (TIME-205..207): GET /api/v1/recommendations/learned (LearnedPreferencesService, non-premium) → plain-language prefers/avoids/avoids-at-time; shown in iOS Learned Patterns + web Insights (Android could follow). OPTIONAL FOLLOW-UPS (not started): per-user WeeklyInsight acceptance columns; fuller acceptance-rate-scaled user_preference_fit; Android build (learned surface + all mobile changes) in CI. Earlier — TELEMETRY: TIME-196..201 shipped = Phase 2 of the Guardrails→Telemetry→Learning plan — recommendation impression→outcome loop LIVE: /now logs a consent-gated impression on RecommendationEvent (typed columns surface/action_type/domain/score/outcome/…, migration e2f3a4b5c6d7) + returns recommendation_event_id; feedback (incl. agree/disagree) echoes the id and records the outcome; admin GET /api/v1/admin/recommendations/metrics = acceptance-rate + confidence-calibration; recommendation_events in privacy export. iOS/web built, Android unverified (no JDK). Backend suite 489. NEXT: Phase 3 LEARNING (not started) = revive the unused apply_feedback seam (wire feedback into the 3 run_engine sites, build a FeedbackSummary by joining feedback→impression on action_type), USER_OFTEN_ACCEPTS boost in penalties.py, make user_preference_fit real, time-of-day rules. Optional follow-up: per-user WeeklyInsight acceptance columns. Earlier — CAPTURE GUARDRAILS: TIME-189..195 shipped = Phase 1 of the Guardrails→Telemetry→Learning plan (Ultraplan cloud session lapsed unapproved; reconstructed locally from the approved direction). CaptureRequest validators + CaptureService output-safety/prompt-injection + dedupe + cross-client 2000-char cap + analytics enrichment; TIME-190 hardened a flaky calendar-sync test. Backend suite 477. NEXT PHASES (not started): Phase 2 telemetry = impression→outcome log on RecommendationEvent (add repo/read-path/typed columns, write on /now, link feedback→outcome incl. the new agree/disagree signals, acceptance-rate + calibration metrics, privacy export); Phase 3 learning = revive the unused apply_feedback seam + real user_preference_fit + time-of-day rules. Earlier — AGREE/DISAGREE: TIME-185..188 shipped — the Best Next Action screen now shows Agree/Disagree first; Agree→Done/Snooze, Disagree→a different recommendation. Backend agree/disagree feedback signals; disagree "demotes, don't hide" via RECENTLY_DISAGREED penalty (3h window, not the not_now 4h hide). iOS/Android/web all updated (Android compile-unverified). Backend suite 462. Standalone on the existing feedback endpoint; telemetry-ready. NOTE: a separate cloud "Ultraplan" refined the big Guardrails→Telemetry→Learning plan (session_01VDiczBU8ZD29hVijqxLGAu) — not yet implemented; agree/disagree is the natural front-end for its impression→outcome log. Earlier — PREMIUM MODEL CHANGE: TIME-178 = everyone is Premium free for their first 14 days, no payment — SubscriptionService.is_premium grants it by account age; TIME-179 = iOS AppState + Android AppViewModel now fetch /subscriptions/me/entitlement on sign-in and set isPremium — was hardcoded false, which had made mobile Insights show the gate to everyone. iOS built; Android no-JDK-unverified. Integrations track per plan "C": BACKEND (C-B) COMPLETE — TIME-177 Google, TIME-180 Outlook/Microsoft (provider+handshake), TIME-181 Slack — all three OAuth handshakes built + unit-tested at /api/v1/integrations/{provider}/{authorize,callback}, each activating once its CLIENT_ID/SECRET env are set. MOBILE (C-A) COMPLETE — TIME-182 iOS ConnectionsView (ASWebAuthenticationSession, built) + TIME-183 Android ConnectionsScreen (ACTION_VIEW + timesense://integrations deep-link, compile-unverified no-JDK). Settings ▸ Connections on both platforms opens /integrations/{provider}/authorize. **PLAN C FULLY DONE.** The ONLY thing left to make any integration live is the user setting the OAuth app credentials (GOOGLE_/MICROSOFT_/SLACK_ CLIENT_ID+SECRET + registering the redirect URIs). Android needs a CI/JDK build to confirm compilation. TIME-184 fixed the last failing test (imminent appointment now beats a context-switch nudge) — backend suite 458 passed, 0 failures. Earlier web TIME-168..176 merged — marketing site, /app companion, Insights, Privacy, Terms, web polish. INTEGRATIONS IN PROGRESS: TIME-177 done = backend OAuth handshake + Google Calendar connect (/integrations/google/authorize + /callback, signed state, server-side token exchange, encrypted storage; unit-tested; goes live once GOOGLE_CLIENT_ID/SECRET set). NEXT: TIME-178 Outlook/Microsoft calendar provider + handshake (net-new), TIME-179 Slack OAuth handshake (scan already built), then mobile "Connect" UI (needs OAuth apps to verify E2E). Known: 1 pre-existing unrelated test failure in test_calendar_sync — see known_issues)

## v1 STATUS: FEATURE-COMPLETE (2026-07-06)

The v1 build is closed out (TIME-058 / Jira TIME-86). The full loop works end-to-end on device:
sign in → capture → auto-scheduled into the day → Now recommends the best next action with a
justified "Why this?" + alternatives → complete → the assistant learns your durations. The
scheduling **"brain"** is done: duration estimation (seed lookup table + per-user learned overrides,
TIME-082/083), auto-placement with Undo (TIME-085), feasibility warnings (TIME-084), configurable
working hours (TIME-086), all grounded in local time (TIME-080/081). Premium UI pass done (TIME-073);
Settings fully functional incl. Sign Out + Delete (TIME-076). On-device dev reaches the Mac backend
over the LAN (TIME-087). Backend suite **329 passing**; iOS + web build clean (Android unverified —
no JDK locally). Smoke: `python scripts/smoke_test.py` all PASS. See docs/launch/release_checklist.md
+ beta_smoke_test.md.

**Next:** release-gating work (deploy backend behind HTTPS + point apps at the prod URL; store
assets/submission; human privacy-policy review; rotate the exposed Android API key) and the post-v1
feature backlog (per-weekday working hours, feasibility for all tasks, in-app calendar OAuth /
StoreKit purchase / data-export download). The user will file tickets for these after v1.

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
- `POST /api/v1/assistant/webhook` — Google Assistant / Dialogflow fulfillment (TIME-053);
  dispatches the same 5 actions as the iOS App Intents (what to do next / log lunch / start focus /
  mark done / replan day) to backend actions, returns spoken fulfillment text. Firebase-gated as the
  account-linked identity
- `GET /api/v1/admin/analytics` — admin event counts (TIME-054); analytics_events recorded by
  AnalyticsService gated on the `analytics` consent (emits task_captured from /capture)
- `GET /api/v1/privacy/export` (portable JSON of all the user's data, tokens redacted) +
  `DELETE /api/v1/privacy/account?confirm=true` (erase account + cascade all data + Firebase user) (TIME-055)
- No new endpoints for TIME-043 — `notification_mode` (gentle/balanced/active_coach) already had
  read/write via `PATCH /api/v1/users/me/preferences`; TIME-043 only added the behavior that acts
  on it (NotificationService.maybe_send_morning_checkin/evening_checkout/learning_prompt), driven
  by a Celery beat schedule rather than a user-facing route

Database tables: users, profiles, preferences, personalities, onboarding_states, consent_records,
subscription_records, replan_requests, notifications, notification_events, tasks,
internal_reminders, recommendation_feedback, routine_assumptions, meal_events, commute_events,
sleep_wake_events, weekly_insights, calendar_integrations, pending_calendar_actions,
slack_integrations, slack_action_items, teams_integrations, teams_action_items, notion_integrations,
notion_import_items, analytics_events. (Correction: there is no separate "notification_preferences" table — the
notification_mode field lives directly on user_preferences; a prior version of this file listed
that table incorrectly.)

Backend tests: 328, all passing (see Known Problems re: 2 flaky Stripe-network tests). The backend
verifies REAL Firebase ID tokens as of TIME-061 (real service account for project timesense-eb7ec
in .env; tests still mock verify_id_token and don't run the app lifespan). config.py loads the
repo-root .env from any CWD (TIME-064); /users/me syncs the DB role from the token claim (TIME-065).

**Full local stack verified working end-to-end this session:** web (localhost:3000, `cd web && npm
run dev`) → real Firebase email/password sign-in → backend (localhost:8000, `cd backend && uvicorn
app.main:app`, Homebrew Postgres 14 on :5432 with a `timesense` role+db created by hand) → admin
dashboard with live data. The web signs in with Email/Password (not Google — must be enabled in the
console). Admin = Firebase custom claim `role: admin` (now auto-mirrored to the DB via TIME-065).

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
- **Web track (companion website + app)** TIME-168..172 — all **Done, merged 2026-07-09** (the "TIME-168..172" IDs are embedded in each ticket's summary; Jira auto-numbers the actual issue keys separately — e.g. TIME-171 = Jira **TIME-2205**, TIME-172 = Jira **TIME-2206**; use those keys with move_ticket.py): TIME-168 cosmic marketing landing (PR #162), TIME-169 logo-returns-to-top (PR #163), TIME-170 companion web app /app Now·Today·Capture for signed-in users (PR #164), TIME-171 web Insights tab (Premium weekly insight + non-Premium upgrade gate; PR #165, Jira TIME-2205 Done), TIME-172 public /privacy Privacy Policy linked from footer (PR #166, Jira TIME-2206 Done), TIME-173 public /terms Terms of Service linked from footer + cross-linked with Privacy (PR #170, Jira TIME-2207 Done). No App Store/Play links yet — user doesn't have the real app URLs; site keeps the web "Open the app" CTA. Web is still companion-only (not the primary product). A real user test account exists for the /app auth chain: `webdemo@timesense.app` (role: user, non-Premium → sees the Insights gate).
- TIME-112..116 → Jira TIME-112..116 (**Deterministic recommendation engine** rebuild per recommendation-engine-build-spec.md — foundation (types/time/location/maps-wrapper/travel-feasibility/normalize), decision core (candidates/scoring/penalties/ranking/selection/feedback + orchestrator; NO LLM in selection), **integrated into /now** (context_builder maps DB→UserContext; engine drives best_task), **real Google maps provider** gated by GOOGLE_MAPS_API_KEY + user_places store + /api/v1/places, and **iOS place-sync**) — **Done (PRs #106-110 merged 2026-07-07)**. LIVE in /now. Remaining to fully activate location driving-time: set GOOGLE_MAPS_API_KEY on the server. NEXT: LLM explanation layer (final phase, explains the already-selected recommendation only).
- TIME-103..111 → Jira TIME-103..111 (Location-aware feature end-to-end: geofence arrival notifications, Settings deep-link, reliable state, radius tuning, multiple places, **location shapes the recommendation**, errands never lead while home; + delete tasks & swipe-to-reveal Done/Delete on Today) — **Done (PRs #97-105 merged 2026-07-07)**
- TIME-103 (net-new) → Jira TIME-103 (Location-aware background arrival notifications — geofence + local notification; NEEDS ON-DEVICE TESTING) — **Done (PR #97 merged 2026-07-07)**
- TIME-094..102 → Jira TIME-94..102 (App-wide screen redesign pass, screens 3,5-12) — **Done (PRs #88-96 merged 2026-07-06)**: Capture, Insights, Learned Patterns, Working Hours, Calendar, Privacy & Consent, Subscription, Settings home, Visual polish (contrast)
- TIME-093 (net-new) → Jira TIME-93 ('Why this recommendation' screen: Signals analyzed) — **Done (PR #87 merged 2026-07-06)**
- TIME-092 (net-new) → Jira TIME-92 (Redesign Today page to approved mockup) — **Done (PR #86 merged 2026-07-06)**
- TIME-091 (net-new) → Jira TIME-91 (Context chips fit on one row) — **Done (PR #85 merged 2026-07-06)**
- TIME-090 (net-new) → Jira TIME-90 (Redesign Now page to approved mockup) — **Done (PR #84 merged 2026-07-06)**
- TIME-089 (net-new) → Jira TIME-89 (Rich structured 'Why This Recommendation?' + pipeline) — **Done (PR #83 merged 2026-07-06)**
- TIME-088 (net-new) → Jira TIME-88 (Rename to 'Why This Recommendation?') — **Done (PR #82 merged 2026-07-06)**
- TIME-088 (net-new) → Jira TIME-88 (Rename Now 'Why this?' → 'Why This Recommendation?') — **Done (PR #82 merged 2026-07-06)**
- TIME-058 (impl seq, final) → Jira TIME-86 (Beta Smoke Test & Release Checklist, v1 close-out) — **Done (PR #81 merged 2026-07-06)**
- TIME-087 (net-new) → Jira TIME-85 (On-device dev: reach Mac backend over LAN) — **Done (PR #80 merged 2026-07-06)**
- TIME-086 (net-new) → Jira TIME-84 (Configurable working hours) — **Done (PR #79 merged 2026-07-05)**
- TIME-085 (net-new) → Jira TIME-83 (Best-time auto-scheduling with Undo) — **Done (PR #78 merged 2026-07-05)**
- TIME-084 (net-new) → Jira TIME-82 (Feasibility warnings + scheduling core) — **Done (PR #77 merged 2026-07-05)**
- TIME-083 (net-new) → Jira TIME-81 (Learn actual durations) — **Done (PR #76 merged 2026-07-05)**
- TIME-082 (net-new) → Jira TIME-80 (Task duration brain) — **Done (PR #75 merged 2026-07-05)**
- TIME-081 (net-new) → Jira TIME-79 (Usable-time cap uses local midnight) — **Done (PR #74 merged 2026-07-05)**
- TIME-080 (net-new) → Jira TIME-78 (Local-time-aware Now) — **Done (PR #73 merged 2026-07-05)**
- TIME-079 (net-new) → Jira TIME-77 ('Why this?' justifies the pick) — **Done (PR #72 merged 2026-07-05)**
- TIME-078 (net-new) → Jira TIME-76 (Lazy-load 'Why this?' on tap) — **Done (PR #71 merged 2026-07-05)**
- TIME-077 (net-new) → Jira TIME-75 (Now alternatives + richer LLM 'Why this?') — **Done (PR #70 merged 2026-07-05)**
- TIME-076 (net-new) → Jira TIME-74 (Make Settings rows functional) — **Done (PR #69 merged 2026-07-05)**
- TIME-075 (net-new) → Jira TIME-73 ('Why this?' reasoning on Now) — **Done (PR #68 merged 2026-07-05)**
- TIME-074 (net-new) → Jira TIME-72 (Fix Now quick actions) — **Done (PR #67 merged 2026-07-05)**
- TIME-073 (net-new) → Jira TIME-71 (Premium visual redesign, calm/minimal) — **Done (PR #66 merged 2026-07-05)**
- TIME-072 (net-new) → Jira TIME-70 (Rule-based date fallback for capture) — **Done (PR #65 merged 2026-07-05)**
- TIME-071 (impl seq-ish) → Jira TIME-69 (Today shows untimed pending tasks) — **Done (PR #64 merged 2026-07-05)**
- TIME-070 (net-new) → Jira TIME-68 (iOS recover from 401 / session-expiry) — **Done (PR #63 merged 2026-07-05)**
- TIME-069 (net-new) → Jira TIME-67 (Dual-stack dev server launcher) — **Done (PR #62 merged 2026-07-05)**
- TIME-068 (net-new) → Jira TIME-66 (Refresh Now/Today on tab return + pull-to-refresh) — **Done (PR #61 merged 2026-07-05)**
- TIME-067 (net-new) → Jira TIME-65 (Fix day-view task visibility) — **Done (PR #60 merged 2026-07-05)**
- TIME-066 (net-new) → Jira TIME-64 (Fix iOS missing color assets, invisible UI) — **Done (PR #59 merged 2026-07-05)**
- TIME-057 (impl seq) → Jira TIME-63 (App Store & Play Store Prep, docs) — **Done (PR #58 merged 2026-07-05)**
- TIME-056 (impl seq) → Jira TIME-62 (Security Review & Hardening) — **Done (PR #57 merged 2026-07-05)**
- TIME-055 (impl seq) → Jira TIME-61 (Privacy: Data Export + Account Deletion) — **Done (PR #56 merged 2026-07-05)**
- TIME-054 (impl seq) → Jira TIME-60 (Error Monitoring + Analytics, backend) — **Done (PR #55 merged 2026-07-05)** — Phase 14 start
- TIME-065 (net-new) → Jira TIME-59 (Sync DB role from token claim) — **Done (PR #54 merged 2026-07-05)**
- TIME-064 (net-new) → Jira TIME-58 (Load .env from repo root) — **Done (PR #53 merged 2026-07-05)**
- TIME-063 (net-new) → Jira TIME-57 (Fix Alembic migration ordering) — **Done (PR #50 merged 2026-07-05)**
- TIME-062 (net-new) → Jira TIME-56 (Client Firebase Config iOS+Android) — **Done (PR #49 merged 2026-07-05)**
- TIME-053 (impl seq) → Jira TIME-55 (Google Assistant Integration) — **Done (PR #48 merged 2026-07-05)**
- TIME-061 (net-new) → Jira TIME-54 (Backend Real Firebase Token Verification) — **Done (PR #47 merged 2026-07-05)**
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
TIME-062 (Jira TIME-56): Client Firebase Config (iOS + Android)
- iOS: linked firebase-ios-sdk (pinned 11.x → 11.15.0; 12.x needs Swift tools 6.1 > this Xcode 16.0)
  + GoogleSignIn-iOS (8.x) to the TimeSense target via the xcodeproj gem; added
  GoogleService-Info.plist (project timesense-eb7ec, bundle com.aetheranalytics.timesense —
  gitignored, not committed). The real `#if canImport(FirebaseAuth)` AuthService now compiles (it
  imports GoogleSignIn for signInWithGoogle → had to add that package too)
- Android: replaced the placeholder google-services.json with the real timesense-eb7ec config
  (google-services plugin + firebase-auth deps already wired)
- Committed project.pbxproj + Package.resolved; .gitignore now ignores xcuserdata/ + .swiftpm/
- Verified: iOS Simulator BUILD SUCCEEDED; app launches with FirebaseApp.configure() on the real
  plist. Remaining: web/.env.local (user's apiKey/appId), console sign-in providers, device run

### (previous) TIME-053 (Jira TIME-55): Google Assistant Integration
- `backend/app/integrations/google_assistant.py` — Dialogflow fulfillment webhook exposing the same
  5 actions as the iOS App Intents (WhatToDoNext/StartFocus/LogLunch/MarkDone/ReplanDay); reuses the
  /now best-task logic (TaskRepository + UsableTimeService + TaskScorer), MealRepository,
  TaskRepository. POST /api/v1/assistant/webhook, Firebase-gated (account-linked stand-in)
- Backend-only per the ticket's stated file; ReplanDay opens the app (no headless replan). Honest
  limits: Actions-on-Google conversational actions were shut down June 2023, so this is the
  Dialogflow webhook contract + intent→action mapping (unit-tested), not a live Assistant round-trip;
  account-linking/OAuth out of scope. 10 new tests; suite 281/281 (excl. 2 flaky Stripe)

### (previous) TIME-061 (Jira TIME-54): Backend Real Firebase Token Verification
- `app/core/firebase.py` now robustly parses the real .env service account (project
  timesense-eb7ec), which is stored single-line with newlines flattened to literal `\n`: try
  compact `json.loads`, else `json.loads(raw.replace("\\n","\n"), strict=False)`. The Admin SDK now
  initializes (verified out-of-band: logs "initialized … for project: timesense-eb7ec") and
  `get_current_user` → `verify_id_token` now checks REAL client tokens
- 4 new unit tests (fabricated key, never the real one); full suite 271/271 (excl. 2 flaky Stripe)
- Client config still needed (NOT in .env): iOS GoogleService-Info.plist, Android
  google-services.json, web NEXT_PUBLIC_FIREBASE_API_KEY/APP_ID/AUTH_DOMAIN — from the
  timesense-eb7ec console per registered app. Real key stays in .env, never committed.

### (previous) TIME-060 (Jira TIME-53): iOS HealthKit Sleep/Wake Read Integration
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

Full history of TIME-034 through TIME-052 + net-new TIME-059/060/061 is in `implementation_log.md`
and `change_summary.md`.

## Current Active Task
No specific ticket in flight. Candidate next steps (ask the user): (a) client Firebase config so a
client can actually sign in end-to-end — iOS GoogleService-Info.plist + Firebase SPM, Android
google-services.json, web NEXT_PUBLIC_FIREBASE_* from the timesense-eb7ec console (the backend
already verifies real tokens as of TIME-061); (b) remaining Phase 13 items in
tickets/implementation_sequence.md (TIME-054+); (c) the deferred UsableTimeService timezone-awareness
pass (subtract routine/meal/commute/sleep from usable time + per-user-local Celery timing). Note the
impl-seq vs Jira offset changed once net-new tickets (TIME-059/060/061) were inserted — always
confirm the Jira key from the creation output, don't assume internal-minus-1. Two message-source
integrations (Slack, Teams) share `ActionItemDetectionService`; Notion stands alone on
`TaskSourceProvider`; a 3rd chat source is the trigger to unify Slack+Teams tables (decision_log.md).

## iOS device runs — remaining user steps (post TIME-059/060)
Real signing (Team WB5NV894N5, App ID com.aetheranalytics.timesense) and the HealthKit entitlement
are wired. For an actual on-device run the user: registers their iPhone's UDID (automatic when the
device is connected in their Xcode, or manually in the portal), then builds/runs from Xcode. The
live HealthKit authorization prompt + real sleep data are inherently device/Simulator-interactive
(not CLI-drivable). The BACKEND now verifies real Firebase tokens (TIME-061), but the CLIENT apps
still lack their Firebase config (iOS GoogleService-Info.plist, Android google-services.json, web
apiKey/appId/authDomain — from the timesense-eb7ec console; iOS also needs Firebase SPM resolved in
Xcode). So a client can't yet obtain a real token to send — client-side sign-in end-to-end is the
remaining gap.

## Important Decisions to Preserve
- Firebase iOS SDK (11.15.0) + GoogleSignIn are now IN the pbxproj as SPM packages (TIME-062), linked to the TimeSense target; the `#if canImport(FirebaseAuth)` guards still protect any toolchain that can't resolve them. Pinned to 11.x because 12.x needs Swift tools 6.1 > Xcode 16.0
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
