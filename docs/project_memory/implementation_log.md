# Implementation Log

## 2026-07-05 — TIME-069 (Jira TIME-67): Dual-stack dev server launcher

Found while the user ran the app on the Simulator: it failed with `nw_endpoint_flow_failed
[::1.8000]`. Root cause — the documented `uvicorn app.main:app` binds IPv4 (127.0.0.1) only, but
macOS resolves `localhost` to IPv6 `::1` first, so the Simulator (calling localhost:8000) couldn't
connect. Added `backend/run_dev.py` which binds an AF_INET6 socket with IPV6_V6ONLY=0 (dual-stack)
and serves app.main:app on it, so both ::1 and 127.0.0.1 respond. Documented in CLAUDE.md's Commands
(use `python run_dev.py` for Simulator dev; plain `uvicorn --reload` stays IPv4-only for reload
loops). Verified both loopbacks return 200. Not committed to production serving (containers bind
0.0.0.0 behind a proxy) — local-dev convenience only.

## 2026-07-05 — TIME-068 (Jira TIME-66): Refresh Now/Today on tab return (+ pull-to-refresh)

Follow-up to TIME-067: even though the backend now surfaces captured tasks, the Now/Today screens
didn't update after a capture. They load once via SwiftUI `.task { }`, but TabView keeps tab views
mounted so `.task` doesn't re-run on tab switch. Fix: NowView + TodayView now
`.onChange(of: appState.selectedTab)` reload when their tab becomes active (appState.selectedTab
drives the TabView selection), plus `.refreshable` pull-to-refresh on both. Initial `.task` kept for
first appearance. iOS BUILD SUCCEEDED. (No backend change.)

## 2026-07-05 — TIME-067 (Jira TIME-65): Fix day-view task visibility (Today 404 + Now ignores captured tasks)

Two bugs found while using the running app:

### Today tab "Couldn't load today — 404" (iOS)
APIClient built the request URL with `URL.appending(path:)`, which percent-encodes the WHOLE string
as a single path component — so any `?query` (Today sends `/timeline/today?date=YYYY-MM-DD`) turned
into `%3Fdate=...`, producing a non-existent path → 404. This broke EVERY query-param endpoint
(insights history, admin search, etc.), not just Today. Fix: build the URL as
`baseURL.absoluteString + path` so the query survives. (The date was already ISO `yyyy-MM-dd`, so no
format issue.)

### Captured task never appears on Now (backend)
GET /now's candidate set was only scheduled-today + overdue tasks. A freshly captured task has no
scheduled_start and no due_at, so it was neither → never surfaced. Fix: also include unscheduled
pending tasks as "do it whenever" candidates.

### Verification
- Backend: new test_now test (unscheduled captured task → best_task); full suite 307/307 (302 via
  --ignore + 5 referral subset), excl. 2 flaky.
- iOS: BUILD SUCCEEDED. (Full signed-in E2E needs the user's login; the URL fix is a one-line
  construction change verified by build + reasoning.)

## 2026-07-05 — TIME-066 (Jira TIME-64): Fix iOS missing color assets (invisible UI)

### Bug (found while the user tried to sign in on the Simulator)
Almost the entire iOS UI was invisible — the user reported only a "Continue with Apple" button on the
sign-in screen. Root cause: `DesignTokens.Color` references named asset-catalog colors
(`Color("TextPrimary")`, `"Surface"`, `"Background"`, `"AccentColor"`, `"TextSecondary"`,
`"Destructive"`, `"Success"`), but **the project had no asset catalog at all**. Every token color
resolved to an invisible fallback, so all text/surfaces/brand rendered white-on-white; only
hardcoded-black elements (the Apple button) showed.

### Fix
- Created `ios/TimeSense/Assets.xcassets` with a colorset for each token (light + dark variants;
  neutral text/surface palette + indigo accent #4A6CF7), plus an empty `AppIcon.appiconset` (actool
  requires the app-icon set named by ASSETCATALOG_COMPILER_APPICON_NAME).
- Registered the catalog in the TimeSense target's resources (xcodeproj gem).

### Verification
- Simulator build → BUILD SUCCEEDED (first attempt failed on the missing AppIcon set until the empty
  one was added). Installed + launched + screenshotted the sign-in screen: brand header, Continue
  with Apple, Continue with Google, "or" divider, and Continue with Email all now render.

### Lesson (recorded in known_issues.md)
Prior iOS "verification" this session (BUILD SUCCEEDED + app launches to its sign-in screen) did NOT
catch this — the one visible element looked plausible in a screenshot, so "app runs to sign-in" was
mistaken for a healthy UI. **Visual verification must confirm the intended UI actually renders, not
just that the app launches.**

## 2026-07-05 — TIME-057 (Jira TIME-63): App Store and Play Store Prep

Documentation deliverable (no code). Created `docs/launch/`:
- `privacy_policy.md` — complete, publishable privacy policy grounded in the real implementation:
  Firebase auth; all 6 consent types (audio_storage/audio_training/location_tracking/health_data/
  calendar_details/analytics); integrations (Calendar/Slack/Teams/Notion, tokens encrypted at rest
  per TIME-056); LLM/OpenAI processing of captured text; Stripe/StoreKit/Play billing; raw-audio
  opt-in; data export + deletion rights (TIME-055); retention; children; contact. Bracketed
  company/legal details for the user; flagged for legal review.
- `app_store_listing.md` — iOS name/subtitle/promo/description/keywords/what's-new (within Apple
  limits) + App Review notes (demo account, permissions, subscription) + App Privacy nutrition-label
  answers per data type.
- `play_store_listing.md` — Android title/short+full description/category + Play Data Safety form
  answers + content-rating notes.
- `store_assets_checklist.md` — exact icon/screenshot sizes + counts per device class, feature
  graphic, and submission prerequisites the USER must produce.
- `README.md` — index + submission runbook.

Non-goals (the user's steps): actual screenshots/icons/feature-graphics, console data entry + binary
upload, legal review. Verified by review for completeness + consistency with the codebase's data
practices; no tests (docs-only).

## 2026-07-05 — TIME-056 (Jira TIME-62): Security Review and Hardening

### Audit (already secure — documented, unchanged)
- Auth: verify_id_token(check_revoked=True); require_admin on the token claim; /users/me mirrors it.
- Stripe webhook already verifies signatures (construct_event → 400 on bad sig, 503 unconfigured).
- Admin routes all require AdminUser (403 otherwise); privacy delete needs confirm; export redacts tokens.

### New hardening
- **Token encryption at rest** — `app/core/crypto.py`: Fernet `encrypt_token`/`decrypt_token` + an
  `EncryptedString` TypeDecorator (impl=Text → NO migration). Key from settings.token_encryption_key
  or derived from secret_key when unset. `decrypt_token` tolerates legacy plaintext (returns as-is on
  InvalidToken). Applied to access_token/refresh_token on Calendar/Slack/Teams/Notion integrations —
  ciphertext at rest, plaintext through the ORM. Closes the logged 'tokens stored as plain Text' issue.
- **Security headers** — `SecurityHeadersMiddleware`: X-Content-Type-Options nosniff, X-Frame-Options
  DENY, Referrer-Policy no-referrer, X-XSS-Protection 0, CSP default-src 'none', + HSTS in production.
- **Rate limiting** — `app/core/rate_limit.py`: in-process fixed-window RateLimiter keyed by
  (name, auth-token-or-IP); plain async-function dependencies (`capture_rate_limit`,
  `account_delete_rate_limit`) applied to POST /capture (30/min) and DELETE /privacy/account (5/hr);
  429 + Retry-After when exceeded. Single-instance/in-memory (Redis is a follow-up).
- config: token_encryption_key + rate-limit knobs.

### Gotchas
- FastAPI does NOT inject `Request` into a class-instance `__call__` dependency (it treats `request`
  as a required field → 422); exposed the limiters as plain async functions instead.
- Shared in-process limiters accumulate state across tests (same auth token) → added an autouse
  conftest fixture (`_reset_all()`) to reset between tests.

### Verification
- 7 new tests (test_security.py): crypto round-trip + legacy-plaintext tolerance; token ciphertext
  at rest (raw column) vs plaintext via ORM; security headers present; rate limiter blocks at limit +
  is per-caller. Suite 306/306 (excl. 2 flaky). Live backend confirmed emitting the headers. No
  migration (EncryptedString renders as TEXT).

## 2026-07-05 — TIME-055 (Jira TIME-61): Privacy Review and Data Export

Self-service GDPR/CCPA-style data portability + erasure (Phase 14).

### Export
- `PrivacyService.export_data(user_id)` — a `_USER_DATA` registry of (label, model, user-column)
  drives a generic serializer that gathers the user's rows across every user-owned table (incl. the
  differently-named FK columns: InviteCode.created_by_id, ReferralCode.owner_id,
  ReferralConversion.referred_user_id) into a JSON bundle. OAuth `access_token`/`refresh_token` are
  redacted; UUIDs/datetimes are JSON-safe.
- `GET /api/v1/privacy/export` (authed) → the bundle.

### Deletion
- `PrivacyService.delete_account(user_id)` — deletes the User row so DB-level ON DELETE CASCADE
  erases all user_id-owned rows (self-maintaining — future tables auto-covered), explicitly purges
  analytics_events (their FK is SET NULL, which would only anonymize), and deletes the Firebase Auth
  user best-effort (graceful when Firebase is unconfigured, e.g. tests).
- `DELETE /api/v1/privacy/account?confirm=true` (authed) → 204; requires confirm=true (irreversible).

### Test infra
- Enabled SQLite FK enforcement in `tests/conftest.py` (`PRAGMA foreign_keys=ON` via a connect
  listener) so ON DELETE CASCADE is exercised like Postgres. Verified the whole suite still passes
  with it on (287 pre-existing + 7 new).

### Verification
- 7 new tests (test_privacy.py): export includes data + redacts tokens; delete erases + cascades;
  requires confirm (400 otherwise); only affects own data; both require auth. Suite 299/299 (excl. 2
  flaky).
- Real-Postgres round-trip: created a user+task, exported (task present, token redacted), deleted →
  user row gone + tasks cascaded to 0.

### Deferred (Non-Goal)
- Per-consent-type revocation cleanup (e.g. revoking health_data auto-purging sleep data) — a
  separate follow-up noted since the consent ticket. This ticket is full-account export + deletion.

## 2026-07-05 — TIME-054 (Jira TIME-60): Error Monitoring and Analytics (backend) — starts Phase 14

Phase 13 (Integrations Expansion, TIME-049–053) is complete; this is the first Phase 14 (Beta
Hardening & Launch Readiness) ticket.

### Monitoring
- `app/core/monitoring.py` — Sentry-optional: `init_monitoring()` initializes Sentry only when
  `settings.sentry_dsn` is set AND sentry-sdk imports; else a clean no-op (graceful pattern).
  `capture_exception(exc, context)` delegates or no-ops; never raises. `send_default_pii=False`,
  `traces_sample_rate=0`.
- Wired into `main.py` lifespan (`init_monitoring()`) and `app/core/errors.py` (the 500 handler +
  a new catch-all Exception handler both call `capture_exception` with path/method context).
- `config.sentry_dsn` (default ""); `sentry-sdk[fastapi]==2.19.2` added to requirements (imported
  lazily inside the functions, so tests run without it installed).

### Analytics (privacy-respecting)
- `AnalyticsEvent` model (user_id nullable FK, event_name, properties JSON text) + migration
  `q7r8s9t0u1v2`; `AnalyticsRepository` (create, counts_by_event).
- `AnalyticsService.track(event_name, user_id=None, properties=None)` — records a user-attributed
  event ONLY if that user granted the existing **`analytics` consent** (ConsentRepository); system
  events (user_id None) record without a check; never raises (best-effort, rides along the request).
- Emits `task_captured` from `POST /api/v1/capture` (properties={source}).
- `GET /api/v1/admin/analytics` (admin-gated) → per-event counts + total.

### Verification
- 9 new tests (test_monitoring_analytics.py): monitoring no-op/safe-capture; analytics
  records-with-consent / skips-without / system-event; capture emits (and skips without consent);
  admin counts + 403. Full suite 292/292 (287 via --ignore + 5 referral subset), excl. 2 flaky.
- Single alembic head; migration applies cleanly to the live Postgres.

### Deferred (Non-Goal)
- Client-side analytics (iOS Analytics.swift / Android analytics/) — follow-up ticket; this
  establishes the backend pipeline + event schema + consent gating first.

## 2026-07-05 — TIME-065 (Jira TIME-59): Sync DB user role from the Firebase token claim

### Why
Authorization had two independent role sources: backend admin endpoints gate on the Firebase custom
claim (require_admin → token role), but GET /users/me returns the DB user.role and the web dashboard
gates on that. Granting admin took two steps (set the claim AND update the DB row) — surfaced when
setting up the first admin.

### Change
- `UserService.get_or_create_user` gains an optional `role` param: on an existing user, if the
  passed role differs from the stored one, update it (persisted by the request's session commit —
  get_db commits on success); on create, pass it through to `repo.create` (which already accepted
  `role`). The claim is the source of truth — a cache refresh, including downgrades if the claim is
  removed.
- `GET /users/me` passes `current_user.role` (the token claim) into get_or_create_user, so the DB
  role mirrors the claim on the call the web makes.
- require_admin unchanged (still reads the token claim; the DB now just mirrors it).

### Tests / Verification
- 2 new tests in test_users.py: a fresh user with an admin claim returns role=admin from /users/me;
  granting then removing the claim downgrades the DB role. Full suite 283/283 (excl. 2 flaky).
- Now granting admin is one step (set the Firebase claim); the DB syncs on next /users/me.

## 2026-07-05 — TIME-064 (Jira TIME-58): Load .env from repo root regardless of CWD

### Bug
Running the documented `cd backend && uvicorn app.main:app` loaded NO env: config.py used
`env_file=".env"` (relative to CWD), so it looked for `backend/.env`, but the real `.env` is at the
repo root. It silently fell back to defaults — the default `DATABASE_URL` happens to match local
Postgres (so the DB worked), but `firebase_project_id`/`firebase_service_account_json` were empty,
so real token verification failed at runtime with "A project ID is required to access the auth
service." Found while bringing the full stack up locally for the user.

### Fix
- config.py: `env_file=(str(_ROOT_ENV), ".env")` where `_ROOT_ENV = Path(__file__).resolve().
  parents[3] / ".env"` — resolves the repo-root .env by absolute path (found from any CWD), with a
  CWD-relative `.env` kept as an optional local override. Missing files are ignored by pydantic; in
  Docker, injected env vars still take precedence.
- Removed the temporary `backend/.env` symlink used during bring-up — the fix stands on its own.

### Verification
- From `backend/` with no symlink: `settings.firebase_project_id == "timesense-eb7ec"`, service
  account present. Backend restarted via `cd backend && uvicorn` → health 200, `get_firebase_app().
  project_id == "timesense-eb7ec"`, and real token verification works (the user's admin dashboard
  loads end-to-end).
- Full suite 281/281 (excl. 2 flaky) — loading the real .env doesn't affect tests (conftest
  overrides the DB via SQLite + dependency injection and mocks verify_id_token).

## 2026-07-05 — TIME-063 (Jira TIME-57): Fix Alembic migration ordering (tasks before recommendation_feedback)

### Bug
Bringing up a real local Postgres for the running app, `alembic upgrade head` failed on a fresh DB
with `relation "tasks" does not exist` at the `add_recommendation_feedback` migration. Root cause:
`g7h8i9j0k1l2` (recommendation_feedback, FK → tasks.id) and `a1b2c3d4e5f7` (tasks) were **parallel
sibling branches** off the same parent `f6a7b8c9d0e1` (an artifact of the earlier 4-head merge).
Alembic linearized the siblings with feedback *before* tasks, so the FK target didn't exist yet.
Masked from the test suite because tests build the schema from models via `Base.metadata.create_all`,
not by running migrations — so no test ever exercised the migration order.

### Fix
- `g7h8i9j0k1l2` down_revision: `f6a7b8c9d0e1` → `a1b2c3d4e5f7` (tasks now guaranteed first).
- Merge migration `e55970716568` down_revision tuple: dropped `a1b2c3d4e5f7` (no longer a head),
  now `('a7b8c9d0e1f2','b8c9d0e1f2a3','g7h8i9j0k1l2')`.

### Verification
- `alembic heads` → single head `p6q7r8s9t0u1`.
- Dropped + recreated an empty Postgres `timesense` DB and ran `alembic upgrade head` → completes
  end-to-end (31 tables; tasks/recommendation_feedback/users all present). Backend then boots and
  `GET /api/v1/health` → 200.
- Full suite 281/281 (excl. 2 flaky) — unaffected (uses create_all).
- Safe change: no DB had ever successfully migrated from scratch in the old order, so there's no
  already-migrated alembic_version graph to disrupt.

## 2026-07-05 — TIME-062 (Jira TIME-56): Client Firebase Config (iOS + Android)

Interactive session with the user, who registered the iOS/Android/web apps in the real Firebase
project **timesense-eb7ec** and supplied the config files. Wired the iOS + Android clients to real
Firebase (web pending the user's apiKey/appId).

### iOS
- Added the **firebase-ios-sdk** Swift Package and linked **FirebaseAuth + FirebaseCore** to the
  TimeSense target (done programmatically via the xcodeproj gem — the user was blocked on Xcode's
  product-selection dialog; the package *reference* had been added by an earlier Xcode attempt but
  no products were linked, which is why they never appeared in the target's "+" list).
- **Pinned Firebase to 11.x** (resolved to **11.15.0**): the reference Xcode created defaulted to
  12.15.0, which requires Swift tools 6.1 — newer than this Xcode 16.0 / Swift 6.0. Changed the
  requirement to `upToNextMajorVersion 11.0.0`.
- Added the **GoogleSignIn-iOS** package (8.x) and linked **GoogleSignIn** — the real AuthService
  (previously never compiled, hidden behind `#if canImport(FirebaseAuth)`) imports GoogleSignIn for
  its `signInWithGoogle`; the first build after linking Firebase surfaced `no such module
  'GoogleSignIn'`.
- Added **GoogleService-Info.plist** to the app target (project_id timesense-eb7ec, bundle id
  com.aetheranalytics.timesense) — **gitignored, NOT committed** (repo convention; each dev supplies
  their own).

### Android
- Replaced the placeholder `android/app/google-services.json` (was project_id
  "timesense-placeholder") with the user's real one (project timesense-eb7ec). The
  com.google.gms.google-services plugin + firebase-auth deps were already wired (TIME-018-era).

### Repo hygiene
- Committed the reproducible bits: `project.pbxproj` (SPM package refs + product links + plist file
  ref) and `Package.resolved` (pins Firebase 11.15.0, GoogleSignIn, gRPC, abseil, …).
- Added depth-agnostic `.gitignore` rules `xcuserdata/` and `.swiftpm/` — the existing
  `*.xcodeproj/xcuserdata/` pattern is root-anchored and missed the nested `ios/...` dirs.

### Verification
- `xcodebuild -resolvePackageDependencies` → resolved Firebase 11.15.0 + full dep graph
- Simulator build (`-scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'
  CODE_SIGNING_ALLOWED=NO`) → **BUILD SUCCEEDED** — the real FirebaseAuth/GoogleSignIn AuthService
  now compiles
- Booted iPhone 16 sim, installed + launched → app runs (status 0), `FirebaseApp.configure()` runs
  against the real plist without crashing
- Remaining user steps: enable sign-in providers (Apple/Google) in the console; run on a device for
  real interactive sign-in; web/.env.local still needs the web apiKey/appId

## 2026-07-05 — TIME-053 (Jira TIME-55): Google Assistant Integration

### Created
- `backend/app/integrations/google_assistant.py` — Dialogflow fulfillment: `parse_intent(body)`
  (reads queryResult.intent.displayName), `fulfillment_response(text)` (builds the Dialogflow
  WebhookResponse), and `GoogleAssistantService.handle(intent, user_id)` dispatching the same 5
  actions as the iOS App Intents (TIME-052): WhatToDoNext, StartFocus, LogLunch, MarkDone, ReplanDay.
  Intent name matching is case/space-insensitive (`_normalize`). Best-task selection reuses the /now
  logic (TaskRepository + UsableTimeService + TaskScorer)
- `backend/app/api/v1/assistant.py` — POST /api/v1/assistant/webhook, gated on the existing Firebase
  CurrentUser (the account-linked identity stand-in); returns the Dialogflow fulfillment JSON
- `backend/tests/test_google_assistant.py` — 10 tests (each intent's text + side effects: lunch
  logged, best task → done; unknown-intent fallback; no-tasks case; auth required)

### Modified
- `backend/app/api/v1/__init__.py` — register the assistant router

### Design notes
- Backend-only, matching the ticket's stated file (`backend/app/integrations/google_assistant.py`)
  and scope ("Actions on Google / Dialogflow integration"). The on-device shortcut surface was the
  iOS App Intents work (TIME-052); this is the Assistant/Dialogflow backend counterpart, exposing
  the identical 5 actions.
- ReplanDay does NOT headlessly replan — it returns "open the app to approve" (replans require in-app
  approval, same rule as everywhere else).
- Honest scope limits (Non-Goals): Google shut down conversational Actions on Google Assistant in
  June 2023, so this implements the Dialogflow-webhook *contract* (request/response shapes +
  intent→action mapping), verifiable by unit tests, not a live Assistant round-trip. Real Actions-
  on-Google account linking (which would supply the user identity) is out of scope; the webhook is
  gated on the Firebase token as the account-linked stand-in.
- 10 new tests; full suite 281/281 (excluding 2 known-flaky Stripe tests).

## 2026-07-05 — TIME-061 (Jira TIME-54): Backend Real Firebase Token Verification

### What changed
- `app/core/firebase.py` — extracted `_load_service_account(raw) -> dict | None` and made
  `init_firebase()` use it. The .env's FIREBASE_SERVICE_ACCOUNT_JSON is real (project
  timesense-eb7ec) but stored single-line with every newline (structural + private_key) flattened
  to literal `\n`, so the old `json.loads(raw)` failed → the Admin SDK never initialized → real
  auth was never actually exercised (tests always mock verify_id_token). The helper tries compact
  `json.loads` first, then falls back to `json.loads(raw.replace("\\n","\n"), strict=False)` (the
  `strict=False` tolerates the real newlines that end up inside the private_key string), returning
  None on empty/garbage so the existing ADC/projectId fallback still applies.
- `tests/test_firebase_init.py` (new) — 4 unit tests for the helper using a FABRICATED service
  account (never the real key): compact JSON parses; a pretty-printed-then-flattened-to-literal-`\n`
  string parses and recovers a well-formed PEM private_key; empty/`{}`/blank → None; garbage → None.

### Verification
- `pytest tests/test_firebase_init.py` → 4/4. Full suite 271/271 (excluding 2 known-flaky Stripe).
- Out-of-band (not in the committed test, to avoid the real key touching the repo): ran the real
  `init_firebase()` with the actual .env value → logs "Firebase Admin SDK initialized with service
  account for project: timesense-eb7ec" and `get_firebase_app().project_id == "timesense-eb7ec"`.
  Before this fix it silently warned "Firebase init failed". `get_current_user` already calls
  `firebase_admin.auth.verify_id_token`, so the backend now verifies REAL client ID tokens.

### Scope boundary (what's still needed for client end-to-end)
- The .env has only the BACKEND service account. Real sign-in from a client additionally needs
  per-app CLIENT config, which is NOT in .env and must be downloaded/registered in the Firebase
  console for project timesense-eb7ec: iOS `GoogleService-Info.plist`, Android
  `google-services.json`, and web `NEXT_PUBLIC_FIREBASE_API_KEY`/`APP_ID`/`AUTH_DOMAIN`. Those are
  separate follow-ups (and iOS also needs the Firebase SDK resolved via Xcode SPM — a standing gap).
- The real service account private key stays only in .env (gitignored) — never committed.

## 2026-07-05 — TIME-060 (Jira TIME-53): iOS HealthKit Sleep/Wake Read Integration

### Created
- `ios/TimeSense/Core/Health/HealthService.swift` — HKHealthStore wrapper behind
  `#if canImport(HealthKit)` (real branch compiles on iOS; `#else` stub mirrors AuthService's
  Firebase-stub pattern). `connectAndSync()` requests read auth for sleepAnalysis, reads the most
  recent sleep window (earliest asleep start + latest asleep end = wake, grouped within a 6h window
  using `HKCategoryValueSleepAnalysis.allAsleepValues`), and POSTs {wake_time, sleep_start,
  source:"healthkit"} to /api/v1/sleep/events via APIClient. Read-only — never writes to HealthKit.
  Publishes a HealthConnectState (idle/requesting/syncing/synced/noData/unavailable/error)

### Modified
- `ios/TimeSense/TimeSense.entitlements` — added com.apple.developer.healthkit (+ empty
  healthkit.access array)
- `ios/TimeSense.xcodeproj/project.pbxproj` — registered HealthService.swift; added
  INFOPLIST_KEY_NSHealthShareUsageDescription (project uses GENERATE_INFOPLIST_FILE) — read-only
  copy, no NSHealthUpdate since TimeSense only reads
- `ios/TimeSense/Features/Settings/SettingsView.swift` — a "Connect Apple Health" row (Button →
  HealthService.connectAndSync()) with inline status (spinner/checkmark/no-data/error)

### Design notes
- Completes the sleep/wake feature's mobile half (backend contract shipped in TIME-042). No backend
  changes — POST /api/v1/sleep/events already exists (gates on health_data consent, proposes a
  morning replan on a late wake); the response's replan_suggested is surfaced in the sync state.
- Unblocked by two things resolved this session: the Simulator (HealthKit runs there) and TIME-059's
  real Apple signing (the healthkit entitlement can now provision on device).

### Verification
- Simulator build → **BUILD SUCCEEDED**, zero new warnings
- Confirmed HealthKit is really linked (not the stub): the Debug build's real code lives in
  `TimeSense.debug.dylib` (Xcode debug-dylib split — the launcher executable itself has no
  frameworks), and `otool -L` on the dylib shows `HealthKit.framework`, `nm` shows
  `_OBJC_CLASS_$_HKHealthStore` referenced, and `HKCategoryValueSleepAnalysis`/`HealthService`
  strings are present. `canImport(HealthKit)` verified true for the iphonesimulator SDK
- Built `Info.plist` contains the NSHealthShareUsageDescription
- Booted iPhone 16 sim, installed + launched under the NEW bundle id **com.aetheranalytics.timesense**
  (also validates TIME-059's rename end-to-end) → app runs cleanly (launchctl status 0), no crash
  from the HealthKit addition
- Not doable headlessly: the live HealthKit authorization prompt + real sleep data + on-device run —
  those are inherently device/interactive and are the user's step (register a device UDID, run from
  their Xcode). HealthKit auth can also be exercised in the Simulator interactively but not via CLI.

## 2026-07-05 — TIME-059 (Jira TIME-52): iOS Real Apple Signing Configuration

### What changed
- Set `DEVELOPMENT_TEAM = WB5NV894N5` (the user's real Apple Developer Team, from .env) on both
  the TimeSense app and TimeSenseWidgetExtension targets (Debug + Release), via the xcodeproj gem
- Renamed `PRODUCT_BUNDLE_IDENTIFIER`: app `com.timesense.app` → `com.aetheranalytics.timesense`;
  widget `com.timesense.app.TimeSenseWidget` → `com.aetheranalytics.timesense.TimeSenseWidget`
  (both configs). `com.aetheranalytics.timesense` is the user's registered App ID (from .env
  APPLE_BUNDLE_ID)
- Renamed the shared App Group `group.com.timesense.app` → `group.com.aetheranalytics.timesense`
  in all three places that must agree: `TimeSense.entitlements`, `TimeSenseWidget.entitlements`,
  and `WidgetSnapshot.appGroupID` (the widget reads the app's snapshot via this group)

### Files changed
- `ios/TimeSense.xcodeproj/project.pbxproj`, `ios/TimeSense/TimeSense.entitlements`,
  `ios/TimeSenseWidget/TimeSenseWidget.entitlements`, `ios/TimeSense/Core/Widgets/WidgetSnapshot.swift`

### Verification
- Simulator build: `xcodebuild -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone
  16' CODE_SIGNING_ALLOWED=NO` → **BUILD SUCCEEDED** after the rename
- **Real signed-device build (best-effort, per the ticket):** ran `xcodebuild -destination
  'generic/platform=iOS' -allowProvisioningUpdates -authenticationKey{ID,IssuerID,Path}` with the
  user's App Store Connect API key (materialized to a temp .p8 in scratchpad — the .env value is a
  single line with literal `\n` escapes, so it had to be decoded to real newlines; validated with
  `openssl pkey`; the temp key was deleted after use and never committed). Result: the key
  **authenticated with Apple successfully** and signing got all the way to provisioning-profile
  generation, failing only with: *"Your team has no devices from which to generate a provisioning
  profile. Connect a device… No profiles for 'com.aetheranalytics.timesense' were found."* Apple
  raised NO complaint about the team, bundle IDs, app group, or certificate — meaning the project
  is now correctly configured to sign against the real account; the sole remaining step is
  registering a device UDID (i.e. the user plugging in their iPhone via their own Xcode). This is
  the exact "needs physical hardware" boundary and is expected — a *development* profile requires a
  registered device, and there's none in this headless environment.
- Note: automatic signing may have registered the two App IDs in the user's account during the
  attempt (benign — they need to exist anyway); it failed before creating a profile.

## 2026-07-05 — TIME-052 (Jira TIME-51): Siri Shortcuts / App Intents

### Created
- `ios/TimeSense/Intents/TimeSenseAppIntents.swift` — 5 AppIntents:
  - WhatToDoNext (GET /api/v1/now → spoken best task + usable minutes)
  - LogLunch (POST /api/v1/meals lunch/eaten)
  - StartFocus (GET /now → "Focus on {best task}")
  - MarkDone (GET /now → PATCH /api/v1/tasks/{bestTaskId} status=done)
  - ReplanDay (openAppWhenRun=true — replans require in-app approval, never headless)
- `ios/TimeSense/Intents/TimeSenseShortcuts.swift` — AppShortcutsProvider exposing each intent
  with natural, \(.applicationName)-prefixed Siri phrases + SF Symbols

### Modified
- `ios/TimeSense.xcodeproj/project.pbxproj` — registered the Intents group (via the xcodeproj gem)
- `scripts/create_jira_tickets.py` — added the TIME-052 ticket definition

### Design notes
- Intents call the app's single network path (APIClient.shared), reuse the existing
  NowContext/NowTask decodables, and define minimal inline request/response types — no new
  networking layer. Read/simple-write intents run headless; ReplanDay opens the app because the
  product rule "replans require approval" means it must be reviewed in-app, not auto-applied.
- Unauthenticated intent runs surface a friendly "open TimeSense and sign in" dialog rather than a
  raw error (via a shared friendlyMessage() mapping APIError.unauthorized).
- **Environment unblocked:** the user installed an iOS Simulator runtime (iOS 18.0), resolving the
  long-standing "no Simulator runtimes" gap (known_issues.md, now marked RESOLVED). This ticket is
  therefore verified to a higher bar than any prior iOS ticket:
  - `xcodebuild -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'
    CODE_SIGNING_ALLOWED=NO` → BUILD SUCCEEDED, zero new warnings
  - Booted iPhone 16 sim, `simctl install` + `launch` → app runs to its sign-in screen without
    crashing (screenshot captured); confirms it's at the auth gate (expected — real Firebase still
    a placeholder, so headless intent→backend round-trips can't be exercised end-to-end yet)
  - All 5 intents present in the built `TimeSense.app/Metadata.appintents/extract.actionsdata`
    bundle — concrete proof the App Intents extracted/registered (earlier builds logged "Extracted
    no relevant App Intents symbols")
- Real *Siri voice* invocation is a real-device follow-up (Siri isn't in the Simulator); the
  Shortcuts-app registration path is what the Simulator verifies.

## 2026-07-05 — TIME-051 (Jira TIME-50): Notion Integration

### Created
- `backend/app/integrations/task_source_base.py` — **new** TaskSourceProvider ABC + SourceTask
  dataclass. Deliberately separate from MessageSourceProvider: a task source (Notion, later
  Todoist/Things) holds already-structured task-like items, so no LLM detection is needed —
  structured field extraction does the work
- `backend/app/integrations/notion_source.py` — NotionTaskSource querying the Notion API
  POST /v1/databases/{id}/query; `_extract_title` (from the title-type property) and `_extract_due`
  (first date-type property) pull structured fields, no LLM
- `backend/app/models/notion.py` — NotionIntegration (token) + NotionImportItem (import queue,
  status pending|imported|dismissed, carries title/notes/due_at)
- `backend/migrations/versions/p6q7r8s9t0u1_add_notion_integration.py` — both tables
- `backend/app/repositories/notion_repository.py`, `schemas/notion.py`, `services/notion_service.py`
  (connect/disconnect/scan_database/list_pending/import_item/dismiss + NotionNotConnected),
  `api/v1/notion.py`
- `backend/tests/test_notion.py` — 15 tests (5 real property-extraction unit tests + scan/import/
  dismiss + premium gate + isolation)

### Modified
- `backend/app/core/config.py` — notion_client_id/secret + notion_version ("2022-06-28")
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/models
- `backend/app/schemas/task.py` — added "notion" to the TaskSource literal

### Design notes
- Per the user's direction, Notion got its OWN abstraction rather than being bent into the
  MessageSourceProvider shape. Justification: a Notion database row is already a discrete task, so
  the honest operation is structured title/due extraction + explicit user import — not LLM sifting
  of chat noise. This is why there's no ActionItemDetectionService here. The framing is
  import/dismiss (not detect/confirm) to reflect it.
- Same approval-gate discipline as every other external signal: scan_database() creates *pending*
  NotionImportItem rows only; import_item() is the single path that creates a Task (source="notion",
  carrying the extracted due_at). Nothing auto-imports.
- Structured extraction handles Notion's property model: the title lives in whichever property has
  type=="title" (name varies per database); due comes from the first date-type property. Only these
  two fields — richer per-database field mapping is an explicit Non-Goal.
- No real Notion OAuth app (empty NOTION_CLIENT_ID/SECRET) — mobile client posts the token to
  /notion/connect like the other integrations; no server-side OAuth callback. Token plain Text,
  same cross-integration encryption deferral (known_issues.md).
- 15 new tests; full suite 262/262 (excluding 2 known-flaky Stripe tests). Single alembic head,
  both tables compile offline.

## 2026-07-05 — TIME-050 (Jira TIME-49): Microsoft Teams Integration

### Created
- `backend/app/services/action_item_detection.py` — shared, source-neutral
  ActionItemDetectionService (extracted from SlackDetectionService); one copy of the LLM
  action-item-detection prompt now serves both Slack and Teams
- `backend/app/integrations/teams_source.py` — TeamsMessageSource(MessageSourceProvider) reading
  Microsoft Graph /chats/{id}/messages, stripping the HTML message body to plain text
- `backend/app/models/teams.py` — TeamsIntegration (token) + TeamsActionItem (approval queue),
  parallel to the Slack models
- `backend/migrations/versions/o5p6q7r8s9t0_add_teams_integration.py` — both tables
- `backend/app/repositories/teams_repository.py`, `schemas/teams.py`, `services/teams_service.py`
  (connect/disconnect/scan_conversation/confirm/reject + TeamsNotConnected), `api/v1/teams.py`
- `backend/tests/test_teams.py` — 12 tests mirroring test_slack.py

### Modified
- `backend/app/services/slack_service.py` — now imports the shared ActionItemDetectionService;
  keeps `SlackDetectionService` as a backward-compatible alias + re-exports Detection, so the
  merged test_slack.py imports stay green (verified: 14/14 still pass)
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/models
- `backend/app/schemas/task.py` — added "teams" to the TaskSource literal

### Design notes
- Teams is the same shape as Slack, so per the rule of three I generalized the one genuinely
  shared piece (LLM detection) into ActionItemDetectionService and kept the per-source
  models/repos/service/schemas/api parallel — matching the repo's own per-feature-table precedent
  (commute/meal/sleep are similarly parallel). Unifying the Slack+Teams tables into one
  source-tagged message-source schema is deliberately deferred to a third source (decision_log.md +
  the ticket's Non-Goals) to avoid a churny migration of just-merged Slack tables.
- Same approval gate as Slack: scan_conversation() creates *pending* TeamsActionItem rows only;
  confirm() is the single path that creates a Task (source="teams", links created_task_id).
- Reuses the MessageSourceProvider ABC built in TIME-049 — TeamsMessageSource is a new provider,
  not a re-architecture.
- No real Azure AD app: MICROSOFT_CLIENT_ID/SECRET are empty placeholders (present since the
  Phase-6 Outlook scaffold). Mobile client POSTs the Graph token to /teams/connect like
  /slack/connect — no server-side OAuth callback / Graph change-notifications in this ticket.
- Token stored as plain Text, matching Slack/Calendar — cross-integration encryption still the
  same deferred item (known_issues.md).
- 12 new tests (Teams) + Slack's 14 still green; full suite 247/247 (excluding 2 known-flaky Stripe
  tests). Single alembic head; both new tables compile offline.

## 2026-07-05 — TIME-049 (Jira TIME-48): Slack Integration

### Created
- `backend/app/integrations/message_source_base.py` — MessageSourceProvider ABC + SourceMessage
  dataclass (a read-only chat/comms source abstraction, for Slack now + Teams later)
- `backend/app/integrations/slack_source.py` — SlackMessageSource calling Slack's
  conversations.history Web API (handles Slack's `{"ok": false}` 200-response quirk)
- `backend/app/models/slack.py` — SlackIntegration (token storage, same shape as
  CalendarIntegration) + SlackActionItem (approval queue, mirrors PendingCalendarAction)
- `backend/migrations/versions/n4o5p6q7r8s9_add_slack_integration.py` — both tables
- `backend/app/repositories/slack_repository.py` — SlackIntegrationRepository +
  SlackActionItemRepository (incl. exists_for_message for scan-dedup)
- `backend/app/schemas/slack.py`, `backend/app/services/slack_service.py`,
  `backend/app/api/v1/slack.py`
- `backend/tests/test_slack.py` — 14 tests (LLM detection unit tests + scan/confirm/reject API
  tests + premium gate + isolation)

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/models
- `backend/app/schemas/task.py` — added "slack" to the TaskSource literal

### Design notes
- The approval gate is the whole point: `scan_channel()` reads messages, runs LLM detection, and
  creates *pending* SlackActionItem rows — NEVER Tasks. `confirm()` is the single path that turns a
  detected item into a Task (source="slack", links created_task_id back onto the item). This mirrors
  the calendar request→approve pattern exactly, satisfying the product's "never auto-create from
  external signals without approval" rule.
- `SlackDetectionService` is split out from `SlackService` so the LLM detection logic is unit-
  testable in isolation. It reuses LLMGateway and degrades gracefully (is_action_item=False) on any
  LLM error — identical fallback discipline to CaptureService.
- Followed the repo's actual flat-file integration convention (calendar_base.py / google_calendar.py)
  rather than the integration-provider-pattern skill's idealized `slack/` subdirectory layout —
  repo is source of truth.
- No real Slack app: SLACK_CLIENT_ID/SECRET/SIGNING_SECRET are empty placeholders in .env (already
  present from an earlier scaffold). The mobile client does OAuth and POSTs the token to
  /slack/connect, exactly like /calendar/connect — no server-side OAuth callback, no Events API /
  signature verification in this ticket (slack_signing_secret stays unused).
- Token stored as plain Text, matching how CalendarIntegration already stores tokens — a cross-
  integration encryption-at-rest pass is separate future work (known_issues.md).
- 14 new tests; full suite 235/235 (excluding 2 known-flaky Stripe tests). `alembic heads` single
  head; offline `--sql` compiles both tables cleanly.

## 2026-07-05 — TIME-048 (Jira TIME-47): Admin Dashboard Foundation (Web)

### Created — web/ (bootstrapped from scratch; first ticket to touch this platform)
- Next.js 16 (App Router) + TypeScript + Tailwind 4, scaffolded via `create-next-app` then
  customized (`npm install firebase`, minimal landing page, real README)
- `lib/firebase.ts` — Firebase app init + a **lazy** `getFirebaseAuth()` getter. `getAuth()`
  validates the API key eagerly and throws `auth/invalid-api-key` immediately when it's empty —
  even during `next build`'s static prerendering of `/_not-found` — so auth is never constructed
  at module-eval time, only on first actual use at runtime, guarded by `isFirebaseConfigured`
- `lib/auth.tsx` — auth context/hook (sign in, sign out, get ID token, current user)
- `lib/api.ts` — `apiFetch()` + `useAdminApi()` hook attaching the Firebase ID token as a Bearer
  header, mirroring ApiClient.swift/ApiClient.kt
- `app/admin/layout.tsx` — role gate (checks GET /api/v1/users/me `role` client-side for UX; the
  real security boundary stays server-side via the existing `AdminUser` FastAPI dependency) + nav
- `app/admin/page.tsx` (metrics + integration status), `users/page.tsx` (search+pagination),
  `invites/page.tsx` (list/create/disable codes + waitlist), `subscriptions/page.tsx`,
  `feedback/page.tsx`
- `.env.local.example` documenting the Firebase + API base URL env vars (none configured — same
  placeholder gap as iOS/Android, open_questions.md)

### Created/Modified — backend (extending admin.py beyond the ticket sequence's literal scope)
- `backend/app/schemas/admin.py` — AdminSubscriptionSummary/ListResponse, AdminFeedbackSummary/
  ListResponse, AdminIntegrationProviderStatus/StatusResponse, AdminMetricsResponse
- `backend/app/api/v1/admin.py` — new GET /admin/subscriptions, /admin/feedback,
  /admin/integrations, /admin/metrics, /admin/waitlist (all AdminUser-gated); extended
  GET /admin/users with a `search` param and fixed `total` (was hardcoded to `len(users)`)
- Repository additions: `user_repository.list_all(search)`/`count_all()`,
  `subscription_repository.list_all()`/`count_by_status()`,
  `recommendation_feedback_repository.list_recent_across_users()` (joins User+Task for display),
  `calendar_repository.count_by_provider()`, `invite_repository.count_waiting()`/`count_active()`
- `backend/tests/test_admin.py` — extended the existing 6-test file to 17 (11 new), covering each
  new/changed endpoint's data correctness + 403-without-admin-role + cross-aggregation correctness

### Design notes
- The ticket sequence's scope line ("Files: web/app/admin/") implied the backend already exposed
  everything needed. In reality only user-listing and invite-code management existed as admin
  endpoints — subscriptions/feedback/integrations/metrics/waitlist had none. Confirmed with the
  user before proceeding: build the missing endpoints rather than ship a dashboard with dead ends.
- Discovered mid-implementation that "view the waitlist" (already committed to in scope) also had
  no backend endpoint — added `GET /api/v1/admin/waitlist` (reusing the existing `WaitlistEntryOut`
  schema, no new schema needed) rather than silently dropping that part of the scope.
- A real, non-lint-blocking discovery: this Next.js/React version's ESLint config enforces a strict
  `react-hooks/set-state-in-effect` rule that flags ANY synchronous `setState` call in an effect
  body that isn't immediately followed by async work in the same branch — including the extremely
  common "setLoading(true) at the top of a data-fetching effect" pattern once other early-return
  branches exist nearby. Fixed by deriving loading state from data (`data === null && error ===
  null`) instead of a separate boolean, per React's own "you might not need an effect" guidance —
  cleaner code, not a workaround. Also fixed a latent bug this surfaced: `error` was never reset
  on a subsequent successful fetch, so a transient failure would blank the UI's error message
  permanently even after later successful loads.
- `npm audit` flags a moderate postcss XSS advisory transitively bundled inside this Next.js
  version; `npm audit fix --force` would downgrade Next.js 16→9 (a completely wrong "fix" from an
  audit database that hasn't caught up with this very new release) — left alone, not actioned.

## 2026-07-05 — TIME-047 (Jira TIME-46): Learned Assumptions Settings

### Created
- `ios/TimeSense/Features/Settings/LearnedAssumptionsViewModel.swift` — GET /api/v1/routines,
  PATCH per routine_type, updates the in-memory list in place on success
- `ios/TimeSense/Features/Settings/LearnedAssumptionsView.swift` — list of the 6 routine types
  with friendly labels + formatted time ranges + an "Edited" badge when is_customized; tapping a
  row opens a sheet with two `DatePicker(.hourAndMinute)` fields (start/end) + Save/Cancel
- `android/.../features/settings/LearnedAssumptionsViewModel.kt` — same two endpoints, OkHttp
- `android/.../features/settings/LearnedAssumptionsScreen.kt` — same list shape; editing uses a
  Material3 `TimePicker` inside an `AlertDialog`, with Starts/Ends toggle buttons since Material3
  doesn't have a two-field time-range picker built in

### Modified
- `ios/TimeSense/Features/Settings/SettingsView.swift` — added a "Learned Assumptions"
  `NavigationLink` row to the Preferences section; extracted `SettingsRowLabel` (icon+title, no
  chevron) from the existing `SettingsRow` so the real `NavigationLink` doesn't double up its own
  disclosure indicator with a second manually-drawn one
- `ios/TimeSense.xcodeproj/project.pbxproj` — registered the two new Swift files (xcodeproj gem)
- `android/.../features/settings/SettingsScreen.kt` — `SettingsItem` gained an `onClick` param
  (previously a no-op `.clickable {}` on every row); added the new row wired to it
- `android/.../navigation/MainNavHost.kt` — registered `"learned_assumptions"` as a new destination
  in the existing single-NavHost tab structure, with `SettingsScreen` now taking an
  `onLearnedAssumptionsClick` callback rather than a `NavController` directly

### Design notes
- Pure UI ticket, no backend changes — GET/PATCH /api/v1/routines (TIME-039) already supported
  everything needed.
- Android has no built-in Material3 "time range" picker, so the edit dialog reuses one
  `TimePicker` with Starts/Ends toggle buttons rather than pulling in a third-party dependency for
  a two-field picker — a deliberate scope-minimizing choice.
- Verified with `xcodebuild -target TimeSense -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO` (BUILD
  SUCCEEDED, zero new warnings) and `./gradlew assembleDebug && ./gradlew test` (BUILD SUCCESSFUL,
  Android-Studio-bundled JBR as JAVA_HOME per known_issues.md).

## 2026-07-05 — TIME-046 (Jira TIME-45): Weekly Insights Generation

### Created
- `backend/app/models/insight.py` — WeeklyInsight model (unique on user_id+week_start)
- `backend/migrations/versions/m3n4o5p6q7r8_add_weekly_insights.py` — weekly_insights table
- `backend/app/repositories/insight_repository.py` — get_by_week/create/list_recent
- `backend/app/schemas/insight.py` — WeeklyInsightResponse
- `backend/app/services/insights_service.py` — InsightsService.get_or_generate_for_week()
  aggregates from 5 existing tables (Task, RecommendationFeedback, MealEvent, SleepWakeEvent,
  CommuteEvent) over a Monday-Sunday range, then calls LLMGateway for a 2-3 sentence summary
  with a templated fallback — identical pattern to RecommendationService._explain(). Idempotent:
  once a week is generated it's returned as-is, never silently recomputed.
- `backend/app/api/v1/insights.py` — GET /insights/weekly (generates the most recently completed
  week on first call), GET /insights/history?limit=8 — both Premium-gated via the existing
  PremiumUser dependency
- `backend/app/workers/insights_tasks.py` — one Celery task generating the just-completed week
  for every active user, scheduled Monday 5am UTC; untested in this environment (no Redis/Docker),
  same precedent as notification_tasks.py
- `backend/tests/test_insights.py` — 17 tests (aggregation math at the service layer, API-layer
  premium gate/wiring/isolation)
- `ios/TimeSense/Features/Insights/InsightsViewModel.swift` — fetches GET /insights/weekly
- `android/.../features/insights/InsightsViewModel.kt` — same, OkHttp/kotlinx.serialization

### Modified
- `backend/app/repositories/task_repository.py` — count_created_in_range/count_completed_in_range
- `backend/app/repositories/recommendation_feedback_repository.py` — count_signals_in_range
- `backend/app/repositories/meal_repository.py` — count_skipped_by_type_in_range
- `backend/app/repositories/sleep_wake_repository.py` — count_late_wakes_in_range
- `backend/app/repositories/commute_repository.py` — count_confirmed_in_range
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/model
- `backend/app/workers/celery_app.py` — registered insights_tasks + Monday 5am beat schedule
- `ios/TimeSense/Features/Insights/InsightsView.swift` — real content (summary card + stats grid)
  replacing the static placeholder, still gated behind the existing isPremium check; registered the
  new ViewModel file into project.pbxproj via the xcodeproj gem (same tooling as TIME-044)
- `android/.../features/insights/InsightsScreen.kt` — real content, same states/gate

### Design notes
- `most_skipped_meal` only reflects meals explicitly logged with status=skipped — it does not
  backfill inferred-but-never-logged skips from MealRepository.get_today_status's live, read-time-
  only computation. Tie-breaks pick the alphabetically-first meal type on equal counts (deterministic
  for tests): `min(items, key=lambda kv: (-count, meal_type))`.
- `tasks_completed`/`tasks_total` use Task.updated_at/created_at as proxies for completion/capture,
  since Task has no explicit completed_at field yet — approximate, documented as such.
- Only fully-completed Monday-Sunday weeks are summarized (no noisy "this week so far" view).
- Verified with `xcodebuild -target TimeSense -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO` (BUILD
  SUCCEEDED, zero new warnings) and `./gradlew assembleDebug && ./gradlew test` (BUILD SUCCESSFUL,
  using the Android-Studio-bundled JBR as JAVA_HOME per known_issues.md).
- Found (but did not fix, out of scope) a latent bug in `tests/test_recommendations.py`'s
  `_MockProvider`: it constructs `LLMResponse(content=..., model="mock")` without the required
  `provider` field, which raises inside the try/except and silently falls through to the fallback
  "why" text rather than actually exercising the mocked LLM path. My own test_insights.py mock hit
  the identical mistake first and I caught it there — flagging test_recommendations.py's version in
  known_issues.md since it means that test isn't verifying what it appears to verify.

## 2026-07-05 — TIME-045 (Jira TIME-44): Android Widgets

### Created
- `android/app/src/main/java/com/timesense/app/widgets/UsableTimeWidget.kt` +
  `UsableTimeWidgetReceiver.kt` — Glance AppWidget rendering usable minutes remaining today, with
  an "Open TimeSense" empty state before the first sync
- `android/app/src/main/java/com/timesense/app/widgets/NextEventWidget.kt` +
  `NextEventWidgetReceiver.kt` — Glance AppWidget rendering the next upcoming non-done event, or
  "Nothing scheduled"
- `android/app/src/main/java/com/timesense/app/widgets/WidgetColors.kt` — mirrors the literal
  day/night color values from `ui/theme/Theme.kt` (kept private there) so widgets get real
  day/night parity with the rest of the app without a Glance Material3 dependency
- `android/app/src/main/res/xml/usable_time_widget_info.xml`,
  `android/app/src/main/res/xml/next_event_widget_info.xml` — AppWidgetProviderInfo resources,
  `updatePeriodMillis="0"` (app-triggered refresh only, no periodic polling)
- `android/app/src/main/res/layout/glance_default_loading_layout.xml` — placeholder Glance
  requires for `initialLayout`/`previewLayout`, replaced at runtime by the actual Glance content
- `android/app/src/test/java/com/timesense/app/features/today/NextEventSelectionTest.kt` — 6 JVM
  unit tests for the new pure `nextUpcomingEvent()` selection function

### Modified
- `android/gradle/libs.versions.toml`, `android/app/build.gradle.kts` — added
  `androidx.glance:glance-appwidget:1.1.1` (latest stable; 1.2.0+ are alpha/beta/rc)
- `android/app/src/main/AndroidManifest.xml` — registered both widget receivers
- `android/app/src/main/java/com/timesense/app/features/now/NowViewModel.kt` — converted
  `ViewModel` → `AndroidViewModel` (needed an Application Context to call Glance's update APIs);
  calls `UsableTimeWidget.updateUsableMinutes()` after a successful `/now` fetch
- `android/app/src/main/java/com/timesense/app/features/today/TodayViewModel.kt` — same
  `AndroidViewModel` conversion; extracted the next-event selection into a standalone top-level
  `nextUpcomingEvent(tasks, now)` function (kept free of Android types so it's a plain JVM test,
  no Robolectric/instrumentation needed) and calls `NextEventWidget.updateNextEvent()`/
  `.clearNextEvent()` after a successful `/timeline/today` fetch

### Design notes
- Unlike iOS's WidgetKit extension (a separate process needing a shared App Group), Android
  AppWidgets run in the same app process — so each widget just reads its own Glance-managed
  Preferences state, written directly by the one ViewModel that owns that data. No shared
  cross-widget blob or App-Group-equivalent was needed, simpler than TIME-044's iOS design.
- Ticket scope intentionally matches `tickets/implementation_sequence.md` exactly: two widgets
  (usable-time, next-event), not iOS's three — no best-next-action widget on Android in this
  ticket, per the ticket's Non-Goals; a third widget can follow later for platform parity if wanted.
- `androidx.glance.color.ColorProvider(day, night)` (not `androidx.glance.unit.ColorProvider`,
  which only takes a single `Color` or `@ColorRes`) is the two-arg day/night constructor;
  `GlanceModifier.background(...)` needs the `androidx.glance.background` extension, not
  `androidx.glance.appwidget.background` — both were found by iterating on real compiler errors
  from `./gradlew assembleDebug`, not guessed correctly on the first pass.
- Environment note: this sandbox has no `java` on PATH and no `JAVA_HOME` set, but
  `/Applications/Android Studio.app/Contents/jbr` (JetBrains Runtime, JDK 21) is installed and
  works as `JAVA_HOME` for Gradle. Both `./gradlew assembleDebug` and `./gradlew test` succeeded
  with `JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"` set. All 6 new
  unit tests pass; only pre-existing, unrelated warnings (deprecated `Divider` in
  `TimelineCard.kt`, JDK 21 deprecating source/target 8) appear in the build output.

## 2026-07-05 — TIME-044 (Jira TIME-43): iOS Widgets

### Created
- New `TimeSenseWidgetExtension` target (WidgetKit app-extension, iOS 17.0, embedded in the
  TimeSense host app) — added programmatically via the `xcodeproj` Ruby gem (installed this
  session with `gem install xcodeproj --user-install`) rather than hand-editing project.pbxproj,
  since a new native target touches build phases, embed/copy-files phases, and a target
  dependency that are error-prone to write by hand
- `ios/TimeSense/Core/Widgets/WidgetSnapshot.swift` — Codable snapshot (usableMinutes, bestTask,
  nextEvent, updatedAt), persisted as JSON in a shared App Group UserDefaults suite
  (`group.com.timesense.app`); compiled into both the app and extension targets
- `ios/TimeSenseWidget/TimeSenseWidgetBundle.swift`, `SnapshotProvider.swift`,
  `UsableTimeWidget.swift`, `NextEventWidget.swift`, `BestNextActionWidget.swift` — the extension's
  own sources; all three widgets share one `TimelineProvider` that only reads the snapshot
- `ios/TimeSenseWidget/Info.plist` — physical plist (GENERATE_INFOPLIST_FILE=NO), matching Apple's
  own widget-extension template keys (CFBundleIdentifier/Executable/Name via build-setting
  substitution, NSExtension/NSExtensionPointIdentifier = com.apple.widgetkit-extension)
- `ios/TimeSense/TimeSense.entitlements`, `ios/TimeSenseWidget/TimeSenseWidget.entitlements` — App
  Group entitlement, wired via CODE_SIGN_ENTITLEMENTS on both targets

### Modified
- `ios/TimeSense/Features/Now/NowViewModel.swift` — after a successful `/now` fetch, updates
  usableMinutes/bestTask on the shared snapshot (preserving nextEvent) and calls
  `WidgetCenter.shared.reloadAllTimelines()`
- `ios/TimeSense/Features/Today/TodayViewModel.swift` — after a successful `/timeline/today`
  fetch, derives the next non-done, not-yet-ended event and updates nextEvent on the shared
  snapshot (preserving usableMinutes/bestTask), then reloads timelines
- `ios/TimeSense.xcodeproj/project.pbxproj` — new target, entitlements wiring, embed phase

### Design notes
- The widget extension has zero network/auth code — it only ever reads the App-Group-shared
  snapshot the host app writes after its own authenticated fetches. This avoids duplicating
  Firebase's in-memory-only ID token (APIClient.swift never persists it to Keychain) into a
  second process, which would have required a new Keychain-sharing mechanism.
- Widgets use DesignTokens.Typography/Spacing (pure value constants, safe to share) but not
  DesignTokens.Color, since those are named-asset-catalog colors and no Assets.xcassets exists
  in this project yet for even the host app — widgets use system semantic colors instead.
- Timeline refresh policy re-requests at the earlier of 30 minutes or the next event's start time,
  using the last-known snapshot in between — no push-triggered instant refresh in this ticket.
- Environment note: this sandbox's Xcode install has no Simulator runtimes downloaded
  (`xcrun simctl list runtimes` is empty), so scheme-based `xcodebuild build -scheme TimeSense`
  fails with "Found no destinations" regardless of this ticket's changes. Verified instead with
  `xcodebuild build -target TimeSense -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO` (and the same
  for `-target TimeSenseWidgetExtension`), which compiles/links without needing a destination.
  Both targets build cleanly with zero new warnings (one pre-existing, unrelated warning in
  CaptureViewModel.swift). A real device/App Store build still needs a real Apple Developer Team
  (open_questions.md) for the App Group entitlement to take effect.

## 2026-07-05 — TIME-043 (Jira TIME-42): Notification Modes and Learning Prompts

### Created
- `backend/app/models/notification_event.py` — NotificationEvent model (event_type
  morning_checkin/evening_checkout/learning_prompt, notification_id FK) — audit trail + dedup
- `backend/migrations/versions/l2m3n4o5p6q7_add_notification_events.py` — notification_events table
- `backend/app/workers/notification_tasks.py` — three thin Celery tasks (send_morning_checkins,
  send_evening_checkouts, send_learning_prompts) wrapping the NotificationService methods via
  asyncio.run() + AsyncSessionLocal; not covered by tests (no Redis/Docker in this environment,
  same precedent as the pre-existing app.workers.health_task)
- `backend/tests/test_notification_orchestration.py` — 9 tests, service-layer against db_session
  (matching test_notifications.py's existing pattern for non-HTTP-triggered flows)

### Modified
- `backend/app/repositories/notification_repository.py` — added NotificationEventRepository
  (record/has_sent_today)
- `backend/app/repositories/user_repository.py` — added list_active_ids() for the worker loop
- `backend/app/services/notification_service.py` — added maybe_send_morning_checkin(),
  maybe_send_evening_checkout(), maybe_send_learning_prompt(), maybe_send_routine_learning_prompt()
- `backend/app/workers/celery_app.py` — registered notification_tasks module + a UTC beat_schedule
  (8am/10am/9pm) for the three tasks
- `backend/app/models/__init__.py` — registered NotificationEvent

### Design notes
- `notification_mode` (gentle|balanced|active_coach) already existed on UserPreferences from an
  earlier ticket but had no behavior attached to it anywhere — this ticket is purely about giving
  it real effect, not adding new preference storage/API.
- Mode mapping: gentle -> evening check-out only (lightest touch); balanced -> both check-ins, no
  learning prompts; active_coach -> both check-ins + learning prompts. This maps directly onto the
  product brief's "Active Coach / Learning Mode" framing rather than inventing an unrelated concept.
- The learning prompt is concrete, not a stub: it checks the user's "sleep" RoutineAssumption
  (TIME-039) and, if still `is_customized = False` and the account is within a 14-day placeholder
  Learning Mode window (reusing the existing 14-day trial length rather than a new arbitrary
  number), asks the user to confirm/adjust the assumed sleep block.
- The 14-day window is explicitly a placeholder — decision_log.md already has an unimplemented
  decision that the learning period should end "based on enough data, not fixed days"; this ticket
  doesn't attempt that, to avoid inventing a second, conflicting partial implementation.
- Dedup (once per event_type per user per UTC day) follows the same created-at-date-check pattern
  already used by SleepWakeEvent/CommuteEvent, rather than a new mechanism.
- Celery beat schedule times (8am/10am/9pm) are UTC, not per-user-local — same known UTC-only
  simplification as RoutineAssumption/CommuteService/MorningReplanService (known_issues.md).

## 2026-07-05 — TIME-042 (Jira TIME-41): Sleep/Wake Signal Integration

### Created
- `backend/app/models/sleep_wake.py` — SleepWakeEvent model (wake_time, sleep_start, source
  healthkit/manual, replan_request_id FK)
- `backend/migrations/versions/k1l2m3n4o5p6_add_sleep_wake_events.py` — sleep_wake_events table
- `backend/app/repositories/sleep_wake_repository.py` — create/get_latest_today/has_replan_on_date/
  set_replan_request
- `backend/app/schemas/sleep_wake.py` — SleepWakeEventIn, SleepWakeEventResponse
- `backend/app/services/morning_replan.py` — MorningReplanService.record_wake_event() gates on
  health_data consent, compares wake_time minute-of-day against the user's "sleep" RoutineAssumption
  end_minute (TIME-039), and calls the existing NotificationService.propose_replan() when the wake
  is >= 45 minutes late, linking the resulting ReplanRequest back onto the event to dedupe same-day
- `backend/app/api/v1/sleep.py` — POST /sleep/events, GET /sleep/today
- `backend/tests/test_sleep_wake.py` — 8 tests

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered sleep router/model

### Design notes
- No new replan mechanism: reuses `NotificationService.propose_replan`/`ReplanRequest` (TIME-015)
  exactly as-is, including the existing `/api/v1/notifications/replans/{id}/approve|reject` routes —
  a sleep-triggered replan looks identical to any other replan to the approval flow.
- Consent-gated on the existing `health_data` consent type (already defined in
  `ConsentRepository.VALID_CONSENT_TYPES`, unused until now) — same 403-without-consent pattern as
  TIME-041's `location_tracking` gate.
- Wake-time-vs-assumption comparison uses the same UTC-minute-of-day simplification already used by
  RoutineAssumption/UsableTimeService/CommuteService (see known_issues.md) rather than inventing a
  fourth partial timezone approach.
- iOS HealthKit read integration is explicitly out of scope for this ticket (backend contract only),
  same backend/mobile split TIME-041 used for its location-permission piece — flagged as its own
  decision point per context_summary.md's note on this being the first backend/mobile-split ticket.
- Found the Jira ticket key (TIME-41) already existed with a stale "In Review" status before any
  code for this ticket existed in this session — likely an abandoned artifact from an earlier
  attempt. Overwrote its description via `create_jira_tickets.py` and moved it back to
  "In Progress" before starting; no code from that prior attempt was present in the repo.

## 2026-07-05 — TIME-041 (Jira TIME-40): Commute Detection

### Created
- `backend/app/models/commute.py` — CommuteEvent model (direction, detected_start/end,
  estimated_minutes, status pending/confirmed/rejected, notification_id FK)
- `backend/migrations/versions/j0k1l2m3n4o5_add_commute_events.py` — commute_events table
- `backend/app/repositories/commute_repository.py` — create/get/list_pending/set_status
- `backend/app/schemas/commute.py` — LocationPingIn, CommuteDetectRequest, CommuteEventResponse
- `backend/app/services/commute_service.py` — haversine-based detect_from_pings() heuristic
  (>500m displacement, 5–120 min elapsed, direction from first ping's UTC hour); propose_commute()
  gates on location_tracking consent (existing ConsentRepository) and creates an approval_needed
  Notification alongside the pending CommuteEvent, mirroring NotificationService.propose_replan
- `backend/app/api/v1/commutes.py` — POST /commute/detect, GET /commute/pending,
  POST /commute/{id}/confirm, POST /commute/{id}/reject
- `backend/tests/test_commutes.py` — 11 tests

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered commutes router/model

### Design notes
- Reused existing infrastructure instead of inventing new mechanisms: `consent_records`
  (`location_tracking` type already existed in `ConsentRepository`'s valid types) for the
  permission gate, and the `Notification`/approval pattern from `ReplanRequest` for the
  confirmation prompt.
- Raw lat/lng points are never persisted — only the derived CommuteEvent window is stored.
- Direction inference (`hour < 14 UTC → to_work`) is a deliberate simplification consistent with
  UsableTimeService/RoutineAssumption's existing UTC-only approach — not a new gap.
- No calendar-event-location correlation: no `CalendarEvent` table with location data exists in
  this codebase yet, so "calendar patterns" from the ticket's goal is deferred to a future ticket.

### Verification
- `pytest tests/test_commutes.py -v` — 11 passed
- Full suite: `pytest` — 181 passed, 2 known-flaky Stripe-network failures in test_referrals.py
  (see known_issues.md — reproduces identically on `main`, unrelated to this change)
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline

## 2026-07-05 — TIME-040 (Jira TIME-39): Meal Tracking (Lightweight)

### Created
- `backend/app/models/meal.py` — MealEvent model, MEAL_TYPES, MEAL_STATUSES
- `backend/migrations/versions/i9j0k1l2m3n4_add_meal_events.py` — meal_events table
- `backend/app/repositories/meal_repository.py` — log(), get_today_status() (explicit log wins;
  else infers skipped/pending from the matching RoutineAssumption window from TIME-039)
- `backend/app/schemas/meal.py` — MealLogRequest, MealEventResponse, MealTodayResponse
- `backend/app/api/v1/meals.py` — POST /meals, GET /meals/today
- `backend/tests/test_meals.py` — 9 tests (API + direct repository skip/pending inference)

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered meals router/model
- `backend/app/api/v1/recommendations.py` — RecommendationResponse gained `skipped_meals: list[str]`,
  sourced from MealRepository, context only (does not change TaskScorer/ranking)
- `backend/tests/test_recommendations.py` — 3 tests for the new field

### Design notes
- Skip inference reuses the UTC-minute-of-day RoutineAssumption windows directly — same
  UTC-only simplification `UsableTimeService` already relies on, not blocked on the
  timezone-awareness follow-up tracked in known_issues.md.
- Discovered `test_referrals.py` has 2 tests that intermittently fail on real Stripe network
  calls in this sandbox (unrelated to this ticket) — documented in known_issues.md, not fixed here.

### Verification
- `pytest tests/test_meals.py tests/test_recommendations.py -v` — 20 passed
- Full suite: `pytest` — 172 passed (after a rerun past the flaky Stripe network tests above)
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline

## 2026-07-05 — TIME-039 (Jira TIME-38): Routine Assumptions Model

### Created
- `backend/app/models/routine.py` — RoutineAssumption model, ROUTINE_TYPES, DEFAULT_ROUTINES (sleep/breakfast/lunch/dinner/morning_hygiene/evening_hygiene, minutes-since-local-midnight)
- `backend/migrations/versions/h8i9j0k1l2m3_add_routine_assumptions.py` — routine_assumptions table
- `backend/app/repositories/routine_repository.py` — get_or_seed_defaults(), update_one()
- `backend/app/schemas/routine.py` — RoutineAssumptionResponse, RoutineAssumptionUpdate
- `backend/app/api/v1/routines.py` — GET /routines (seeds defaults), PATCH /routines/{routine_type}
- `backend/tests/test_routines.py` — 9 tests

### Modified
- `backend/app/api/v1/__init__.py` — registered routines_router
- `backend/app/models/__init__.py` — registered RoutineAssumption

### Design notes
- Deliberately does NOT wire routine blocks into `UsableTimeService` yet — see known_issues.md
  "RoutineAssumption data (TIME-039) is not yet subtracted from usable time". `UsableTimeService`
  has no timezone awareness today; doing that properly once for routines+meals+commute together
  (after TIME-040–042) avoids three partial integrations.
- `end_minute < start_minute` signals a block that wraps past midnight (sleep 23:00→07:00).
- Editing a routine sets `is_customized=True` so future auto-detection tickets (commute/sleep) know
  not to silently overwrite a user's explicit choice.

### Verification
- `pytest tests/test_routines.py -v` — 9 passed
- Full suite: `pytest` — 161 passed
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline (no live
  Postgres available in this environment)

## 2026-07-04 — TIME-038 (Jira TIME-37): Feedback Collection

### Created
- `backend/app/models/recommendation_feedback.py` — RecommendationFeedback model (user_id, task_id, signal, snooze_until)
- `backend/migrations/versions/g7h8i9j0k1l2_add_recommendation_feedback.py` — recommendation_feedback table
- `backend/app/repositories/recommendation_feedback_repository.py` — RecommendationFeedbackRepository.get_suppressed_task_ids()
- `backend/tests/test_feedback.py` — 7 tests for POST /recommendations/feedback
- `backend/migrations/versions/e55970716568_merge_parallel_migration_heads.py` — merges 4 divergent Alembic heads (pre-existing issue, see Known Issues)

### Modified
- `backend/app/api/v1/recommendations.py` — added `POST /recommendations/feedback` (done/snooze/not_now); `GET /recommendations` now filters out tasks suppressed by active snooze or a recent not_now
- `backend/app/models/__init__.py` — registered RecommendationFeedback so Alembic autogenerate detects it
- `backend/tests/test_recommendations.py` — 3 new tests for suppression behavior (not_now, active snooze, expired snooze)

### Design notes
- `not_now` suppresses a task from recommendations for a 4-hour cooldown (`NOT_NOW_COOLDOWN`), not permanently — avoids "nagging" per the recommendation-engine skill while still letting a still-pending task resurface later.
- `snooze` suppresses until `snooze_until` passes.
- Only the *latest* feedback per task is considered — an expired snooze or superseded not_now does not keep suppressing.
- `signal=done` also flips the task to `status=done` via `TaskRepository.update`.

### Verification
- `pytest tests/test_feedback.py tests/test_recommendations.py -v` — 16 passed
- Full suite: `pytest` — 152 passed
- `alembic upgrade head --sql` (offline mode) — compiles cleanly, single resolved head. No live Postgres available in this environment to run a real `alembic upgrade head`; needs verification against a real DB before deploy.

## 2026-07-03 — TIME-001: Repository Bootstrap

### Created
- `/README.md` — full project overview, stack, setup instructions
- `/AGENTS.md` — agent rules, subagents, skills, code generation constraints
- `/CHANGELOG.md` — initialized
- `/docs/product/product_brief.md` — product vision, rules, non-negotiables
- `/docs/architecture/architecture_overview.md` — system architecture, backend/mobile/web structure, integration patterns, data flow
- `/docs/project_memory/context_summary.md` — current state and next steps
- `/docs/project_memory/phase_status.md` — phase tracking
- `/docs/project_memory/decision_log.md` — all settled product and technical decisions

### In Progress
- Remaining project memory files
- Workflow docs
- Ticket sequence
- Skills
- PR template
- Operational CLAUDE.md
