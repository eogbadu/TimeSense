# Known Issues

## RESOLVED (2026-07-10, TIME-184): test_calendar_sync::test_appointment_within_the_hour_is_surfaced_over_tasks
- Was failing deterministically at "night" (UTC): an appointment ~45 min out returned domain `context_switch` instead of `calendar`.
- Root cause: with no user timezone, part_of_day derives from UTC; at "night" a transition_to_sleep (context_switch) candidate scored ~0.6755, edging the "coming up" calendar candidate ~0.675 by a hair.
- FIX (TIME-184): added a penalty in scoring/penalties.py — a generic context_switch nudge is suppressed when a calendar event is within the hour (mirrors the "don't start an errand before a commitment" rule). Suite now 458 passed, 0 failures.
- Latent (not fixed): part_of_day falls back to UTC when a user has no timezone; harmless in production (users have a timezone) and the penalty makes behaviour correct regardless.

## Integrations: real OAuth connect can't be verified end-to-end without OAuth app credentials (2026-07-09, TIME-177)
- The Google Calendar OAuth handshake (/integrations/google/authorize + /callback) is built and unit-tested against a mocked token exchange, but a real Google consent flow needs GOOGLE_CLIENT_ID/SECRET + a registered redirect URI (user's Google Cloud project). Same will apply to Microsoft/Outlook (Azure) and Slack. The mobile "Connect" UI is not built yet.

## Migration/model drift risk (found TIME-125)
Hand-written Alembic migrations must include server_default=now() on created_at/updated_at to match TimestampMixin. Unit tests use Base.metadata.create_all (from models), so they DON'T catch a migration missing the default — it only fails on Postgres at runtime. Four tables (user_location_states/user_places/device_tokens/push_notifications) hit this; fixed by migration y5z6a7b8c9d0. Future hand-written migrations: copy created_at/updated_at with sa.text('now()') server_default.

## Lesson: iOS visual verification must confirm the UI renders, not just that the app launches (2026-07-05)
- During TIME-052/060 I verified iOS work with "BUILD SUCCEEDED + app installs + launches to its
  sign-in screen" and treated that as success. But the app's UI was actually almost entirely
  INVISIBLE (missing color asset catalog — fixed in TIME-066): only the hardcoded-black Apple button
  rendered. A launch-only check + a glance at a screenshot with one plausible-looking element is not
  enough. For iOS UI work: confirm the *intended* elements are visible in the screenshot (brand,
  multiple buttons, text), and prefer checking a screen with rich content.

## Issue: Integration OAuth tokens are stored as plain Text, not encrypted at rest — RESOLVED 2026-07-05 (TIME-056)
- Date: 2026-07-05
- **RESOLVED (2026-07-05, TIME-056):** added `EncryptedString` (Fernet) in `app/core/crypto.py` and applied it to the access_token/refresh_token columns of Calendar/Slack/Teams/Notion integrations — tokens are now ciphertext at rest, decrypted transparently by the ORM. No migration (impl=Text). Key from `settings.token_encryption_key` (derived from secret_key if unset — set a real key in prod). `decrypt_token` tolerates any legacy plaintext.
- Area: `backend/app/models/calendar.py` (CalendarIntegration.access_token), `backend/app/models/slack.py` (SlackIntegration.access_token)
- Symptom: OAuth/access tokens for connected integrations (Google Calendar since TIME-015-era, Slack as of TIME-049) are stored in plain `Text` columns. The integration-provider-pattern skill calls for encrypted-at-rest storage ("Store encrypted in integration_tokens table").
- Root cause: The original calendar integration stored tokens as plain Text; TIME-049's Slack integration matched that existing behavior for consistency rather than introducing a one-off encryption scheme for just Slack.
- Fix: Not applied — deferred deliberately. A proper fix should be a single cross-integration pass (app-level encryption via a KMS/Fernet key, or DB-level column encryption) covering calendar + Slack + future Teams/Notion tokens together, not per-integration.
- Files changed: None.
- Verification: N/A.
- Follow-up needed: Add an encryption layer (e.g. a typed EncryptedText SQLAlchemy column backed by a key from settings/KMS) and migrate existing `calendar_integrations.access_token` / `slack_integrations.access_token` values. Do this before any real production tokens are stored. Tracks alongside the "no real OAuth apps configured yet" gap — neither is exercised until real provider apps exist.

## Issue: `npm audit` in web/ recommends a bad "fix" (Next.js 16 → 9 downgrade)
- Date: 2026-07-05
- Area: `web/package.json`
- Symptom: `npm audit` flags a moderate PostCSS XSS advisory transitively bundled inside this Next.js version's own dependencies. Its suggested `npm audit fix --force` would downgrade `next` from 16.2.10 to `9.3.3` — a completely wrong "fix" that would destroy the entire app.
- Root cause: This project uses a very new Next.js release; npm's advisory-to-fix-version mapping hasn't caught up and picks the oldest version lacking the vulnerable transitive dependency, ignoring that it's 7 major versions behind.
- Fix: Not applied — do not run `npm audit fix --force` in `web/`. Wait for a genuine Next.js patch release that bumps its bundled PostCSS instead.
- Files changed: None.
- Verification: N/A.
- Follow-up needed: Re-run `npm audit` periodically; once a real Next.js patch resolves this, the advisory will clear on its own via a normal `npm update`.

## Issue: Firebase — backend now real (TIME-061); CLIENT config files still needed (partially updated 2026-07-05)
- Date: 2026-07-05
- Area: backend `app/core/firebase.py` (RESOLVED); `web/lib/firebase.ts`, iOS `GoogleService-Info.plist`, Android `google-services.json` (still placeholder)
- **UPDATE (2026-07-05, TIME-061):** a real Firebase project EXISTS — `timesense-eb7ec`. The .env has the real BACKEND service account (`FIREBASE_PROJECT_ID`, `FIREBASE_SERVICE_ACCOUNT_JSON`), and TIME-061 fixed the parse so the Admin SDK initializes and the backend verifies real ID tokens. So the "no real Firebase project" root cause is gone; what remains is purely the per-app CLIENT config, which is NOT in .env.
- **UPDATE (2026-07-05, TIME-062):** iOS + Android client config is now DONE. iOS has firebase-ios-sdk (11.15.0) + GoogleSignIn linked and GoogleService-Info.plist added (gitignored); it builds and runs with real Firebase. Android has the real google-services.json. **Only the WEB client remains:** `web/.env.local` still needs `NEXT_PUBLIC_FIREBASE_API_KEY` + `_APP_ID` (authDomain=`timesense-eb7ec.firebaseapp.com`, projectId=`timesense-eb7ec` are known) — pending the user pasting those two public values.
- Follow-up needed: (1) web/.env.local with the web app's apiKey/appId; (2) in the console, enable sign-in providers (Apple/Google/email) under Authentication → Sign-in method; (3) on-device run for real interactive sign-in (Simulator verifies build + launch only). GoogleService-Info.plist is per-dev (gitignored) — each dev downloads their own from the console.

## Issue: test_recommendations.py's mock LLM provider doesn't actually exercise the LLM-success path
- Date: 2026-07-05
- Area: `backend/tests/test_recommendations.py`
- Symptom: `_MockProvider.complete()` returns `LLMResponse(content="This is your highest priority task right now.", model="mock")` — missing the required `provider` field on the `LLMResponse` dataclass (`app/llm/base.py` defines `provider: str` with no default). Constructing it without `provider` raises `TypeError`, which `RecommendationService._explain()`'s blanket `except Exception:` silently catches, falling through to the templated fallback text instead of the mocked LLM text. Any assertion checking for the mocked content specifically would fail — but a look at the existing test suggests it only checks structural response shape, not exact "why" text, so this has gone unnoticed.
- Root cause: `LLMResponse`'s `provider` field has no default value, so any code constructing one without it raises at construction time; discovered because `tests/test_insights.py`'s own mock provider made the identical mistake first (fixed there by adding `provider="mock"`).
- Fix: Not applied — out of scope for TIME-046 (touching an unrelated, currently-passing test file's internals risks destabilizing it without a reason tied to this ticket). `test_recommendations.py`'s mock still "passes" today only because nothing asserts on the exact why-text; it's silently testing the fallback path, not the LLM path.
- Files changed: None.
- Verification: N/A.
- Follow-up needed: Add `provider="mock"` to `test_recommendations.py`'s `_MockProvider.complete()` return value in a small, separate fix, ideally alongside an assertion that the returned "why" text actually equals the mocked content (to make the test fail loudly if this regresses again).

## Issue: WeeklyInsight's tasks_completed/tasks_total are proxies, not exact
- Date: 2026-07-05
- Area: `backend/app/services/insights_service.py`, `backend/app/repositories/task_repository.py`
- Symptom: `count_completed_in_range()` uses `Task.updated_at` as a stand-in for "when this task was completed" (any update touches `updated_at`, not just a done-transition), and `count_created_in_range()` uses `Task.created_at` as a stand-in for "captured this week." Both are reasonable but not exact.
- Root cause: `Task` has no explicit `completed_at` timestamp field — TIME-046 didn't add one, since introducing a new column plus a migration to backfill/maintain it felt like a bigger schema change than this ticket's scope (a weekly summary, not a task-model overhaul).
- Fix: Not applied — documented limitation, acceptable for a first version of weekly insights.
- Files changed: None.
- Verification: N/A.
- Follow-up needed: If this proxy proves too noisy in practice (e.g. an edit-only update inflating "completed" counts), add a real `completed_at` column to `Task`, set it exactly once on the done transition, and switch `count_completed_in_range` to use it.

## Issue: This environment has no system `java`/`JAVA_HOME` — use Android Studio's bundled JBR
- Date: 2026-07-05
- Area: `android/` build verification (TIME-045)
- Symptom: `./gradlew assembleDebug` fails immediately with `The operation couldn't be completed. Unable to locate a Java Runtime.` — `which java` and `$JAVA_HOME` are both empty.
- Root cause: No standalone JDK is installed system-wide in this sandbox. Android Studio is installed, however, and bundles its own JetBrains Runtime (JBR) at `/Applications/Android Studio.app/Contents/jbr`.
- Fix: Not needed — set `JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"` before running any `./gradlew` command in this environment (e.g. `export JAVA_HOME=... && ./gradlew assembleDebug`). This JBR is JDK 21 and works cleanly for both `assembleDebug` and `test`.
- Files changed: None (environment-only; not something to fix in the repo).
- Verification: `./gradlew assembleDebug` and `./gradlew test` both succeed with that `JAVA_HOME` set.
- Follow-up needed: None — just remember to set `JAVA_HOME` this way for any future Android work in this same environment. A different environment/container may have a system JDK and not need this.

## Issue: Android widgets (TIME-045) have no periodic auto-refresh, same as iOS (TIME-044)
- Date: 2026-07-05
- Area: `android/app/src/main/res/xml/usable_time_widget_info.xml`, `next_event_widget_info.xml`
- Symptom: Both widgets' `updatePeriodMillis="0"` — they only update when the app itself calls `UsableTimeWidget.updateUsableMinutes()`/`NextEventWidget.updateNextEvent()` after a successful fetch. If the app isn't opened, the widget's displayed data goes stale.
- Root cause: Deliberate scope decision, not a bug — matches TIME-044's iOS widgets, which have the identical limitation (see `decision_log.md`). A background-refresh pipeline (WorkManager periodic work, or push-triggered) is out of scope for both platform tickets.
- Fix: Not applied — intentional, documented in both tickets' Non-Goals.
- Files changed: None.
- Verification: N/A.
- Follow-up needed: If staleness becomes a real usability problem, add a WorkManager periodic job (Android) / BGTaskScheduler or push-triggered refresh (iOS) as a dedicated later ticket for both platforms together.

## Issue: This environment's Xcode has no iOS Simulator runtimes installed — RESOLVED 2026-07-05
- Date: 2026-07-05
- Area: `ios/` build verification (TIME-044)
- **RESOLVED (2026-07-05, during TIME-052):** the user installed an iOS Simulator runtime. `xcrun simctl list runtimes` now shows `iOS 18.0`, with iPhone 16 / 16 Pro / SE / iPad devices available. Scheme-based builds and Simulator runs now work: `xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO` → BUILD SUCCEEDED, and `simctl boot/install/launch` runs the app (verified in TIME-052 — the app launches to its sign-in screen without crashing). Going forward, prefer the scheme+destination invocation over the `-target`/`-sdk` workaround below; only fall back if a scheme build ever fails to resolve a destination again.
- Symptom: `xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense` (the command documented in CLAUDE.md) fails with `xcodebuild: error: Found no destinations for the scheme 'TimeSense' and action build.` Adding `-destination 'generic/platform=iOS Simulator'` instead reports the iOS Simulator SDK is present (`xcodebuild -showsdks` lists `iphonesimulator18.0`) but `xcrun simctl list runtimes` returns nothing and `/Library/Developer/CoreSimulator/Profiles/Runtimes/` doesn't exist — no simulator runtime disk image has ever been downloaded in this container.
- Symptom: `xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense` (the command documented in CLAUDE.md) fails with `xcodebuild: error: Found no destinations for the scheme 'TimeSense' and action build.` Adding `-destination 'generic/platform=iOS Simulator'` instead reports the iOS Simulator SDK is present (`xcodebuild -showsdks` lists `iphonesimulator18.0`) but `xcrun simctl list runtimes` returns nothing and `/Library/Developer/CoreSimulator/Profiles/Runtimes/` doesn't exist — no simulator runtime disk image has ever been downloaded in this container.
- Root cause: A fresh/minimal Xcode install where the Simulator platform's runtime bundle was never installed (`xcodebuild -runFirstLaunch` / a runtime download was skipped when this environment was provisioned). This is unrelated to any project code.
- Fix: Not applied — downloading a Simulator runtime is a large (multi-GB) network operation that wasn't taken without explicit user direction. Worked around for TIME-044 by building each target directly instead of through the scheme: `xcodebuild build -project ios/TimeSense.xcodeproj -target TimeSense -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO` (and `-target TimeSenseWidgetExtension`), which compiles and links without needing to resolve a destination. Both succeeded cleanly.
- Files changed: None.
- Verification: Both targets build with `BUILD SUCCEEDED` via the `-target`/`-sdk` invocation above; zero new warnings (one pre-existing, unrelated warning in `CaptureViewModel.swift`).
- Follow-up needed: If actually running/screenshotting the app in Simulator becomes necessary (per the `run`/`verify` skills), a Simulator runtime will need to be downloaded first — either via Xcode's own "Platforms" settings UI or `xcodebuild -downloadPlatform iOS`. Ask the user before doing this given the download size.

## Issue: iOS App Group entitlement (TIME-044) has no real Apple Developer Team behind it yet — RESOLVED 2026-07-05 (TIME-059)
- Date: 2026-07-05
- Area: `ios/TimeSense/TimeSense.entitlements`, `ios/TimeSenseWidget/TimeSenseWidget.entitlements`
- **RESOLVED (2026-07-05, TIME-059):** the user provided a real Apple Developer account in .env (Team WB5NV894N5, registered App ID com.aetheranalytics.timesense + an App Store Connect API key). TIME-059 set DEVELOPMENT_TEAM on both targets and renamed all bundle IDs + the App Group to the registered `com.aetheranalytics.timesense` / `group.com.aetheranalytics.timesense`. A signed 'generic/platform=iOS' build with the API key authenticated with Apple and reached provisioning-profile generation, failing only on "no registered device" — i.e. the config is correct against the real account; the sole remaining step is a device UDID (the user plugging in their iPhone via their Xcode). Simulator builds unaffected.
- Symptom: Both targets declared `com.apple.security.application-groups = [group.com.timesense.app]` and built fine for Simulator (CODE_SIGNING_ALLOWED=NO / automatic signing with no team), but a real device or App Store build needs that App Group registered against a real Apple Developer Team, or codesigning/provisioning fails.
- Root cause: No Apple Developer account was configured — now provided.
- Follow-up needed: For an actual on-device run, the user registers their device UDID (auto when connected in Xcode) so a development provisioning profile can be created; the headless environment has no device. HealthKit (TIME-060) adds the healthkit entitlement on top of this now-real signing.

## Issue: test_referrals.py intermittently fails on real Stripe network calls
- Date: 2026-07-05
- Area: `backend/tests/test_referrals.py` (`test_conversion_extends_subscriptions`, `test_no_double_conversion`)
- Symptom: These two tests occasionally fail with `stripe._error.APIConnectionError: ... No route to host` for `api.stripe.com`, then pass moments later on an identical rerun with no code changes.
- Root cause: These tests call through to the real Stripe SDK instead of mocking it, so they depend on outbound network access to `api.stripe.com` actually being available from wherever the suite runs. This sandbox environment's network access appears intermittent/restricted (unlike the `.devcontainer/` firewall setup documented below, which explicitly allowlists `api.stripe.com`).
- Fix: None applied — out of scope for TIME-040/041. If seen again, rerun the suite before assuming a regression; a real fix would mock the Stripe client in these two tests like the rest of `test_subscriptions.py` already does.
- Files changed: None.
- Verification: During TIME-040 it failed once then passed on an immediate rerun. During TIME-041 it failed consistently across 4 consecutive reruns — network egress to `api.stripe.com` appears to have become unavailable for the rest of this session rather than merely intermittent. Either way it's unrelated to any code change in either ticket (reproduces identically on `main` before either branch).
- Follow-up needed: Mock Stripe calls in `test_conversion_extends_subscriptions`/`test_no_double_conversion` so the suite doesn't depend on network access.

## Issue: Alembic accumulated 4 divergent migration heads (TIME-030/033/036 era)
- Date: 2026-07-04
- Area: `backend/migrations/versions/`
- Symptom: Discovered while adding the TIME-038 `recommendation_feedback` migration — `alembic heads` showed 4 heads (`a1b2c3d4e5f7` tasks/reminders, `a7b8c9d0e1f2` referrals, `b8c9d0e1f2a3` waitlist/invite, plus the new one), all branching from the same parent `f6a7b8c9d0e1`. `alembic upgrade head` would have failed with "Multiple head revisions are present" — the standard `alembic upgrade head` command in CLAUDE.md was broken and had been broken since at least the referral/waitlist tickets, undetected because tests use in-memory SQLite with `Base.metadata.create_all` and never actually run the Alembic chain.
- Root cause: Several feature branches each wrote a migration with `down_revision = "f6a7b8c9d0e1"` without checking whether a sibling branch had already claimed that as its parent, and none of the merges added a merge migration afterward.
- Fix: Ran `alembic merge heads` to generate `e55970716568_merge_parallel_migration_heads.py`, a no-op migration whose `down_revision` is the tuple of all 4 heads. `alembic heads` now shows a single head.
- Files changed: `backend/migrations/versions/e55970716568_merge_parallel_migration_heads.py` (new)
- Verification: `alembic heads` → single head; `alembic upgrade head --sql` compiles the full chain cleanly in offline mode. Could not run a real `alembic upgrade head` against Postgres — no Docker/Postgres available in this session's environment.
- Follow-up needed: Verify `alembic upgrade head` against a real Postgres instance before this branch is deployed. Going forward, anyone adding a migration should run `alembic heads` first and rebase `down_revision` onto the current head rather than an old parent.

## Issue: `gh` CLI not authenticated in this environment — RESOLVED 2026-07-04
- Date: 2026-07-04
- Area: Session/environment setup, blocks the GitHub half of the required Jira/GitHub ticket workflow
- Symptom: `gh auth status` reports not logged into any GitHub hosts, so `gh pr create` cannot run. (Note: `git push` itself worked before this fix via a separate VS Code remote-container credential helper — only the `gh` CLI specifically was unauthenticated.)
- Root cause: This devcontainer/session was never authenticated against GitHub (`gh auth login` not run).
- Fix: User ran `gh auth login` (device code flow) mid-session; `gh auth status` now shows logged in as `eogbadu` with `repo` scope. PR #29 (TIME-038) was created successfully afterward.
- Files changed: None (auth is stored in `~/.config/gh/hosts.yml`, not in the repo).
- Verification: `gh auth status` → logged in; `gh pr create` succeeded for PR #29.
- Follow-up needed: None — resolved for this environment's lifetime. A fresh container/session would need `gh auth login` run again.

## Issue: RoutineAssumption data (TIME-039) is not yet subtracted from usable time
- Date: 2026-07-05
- Area: `backend/app/services/usable_time_service.py`
- Symptom: TIME-039 added a `routine_assumptions` table and API (sleep/meal/hygiene blocks), but `UsableTimeService.calculate()` still only looks at scheduled `Task` blocks — it has no awareness of routines yet, and recommendations can still be generated for e.g. 2am if a user has pending tasks.
- Root cause: `UsableTimeService.calculate()` computes its end-of-day cap from UTC midnight and has never taken a user timezone parameter, despite TIME-034's original ticket scope saying it should. Converting routine minute-of-day values (which are local-time) into UTC blocks correctly requires that timezone awareness to exist first — bolting it on per-signal (routines now, then meals, then commute) would mean rewriting the same timezone logic three times.
- Fix: Not applied — deliberately deferred (see TIME-039 ticket Non-Goals). Was correct to store the model/API now since meal/commute/sleep tickets (TIME-040–042) need it to exist, but the actual usable-time integration should happen once all Phase 9 signals exist, in one pass, alongside adding proper timezone handling to `UsableTimeService`.
- Files changed: None yet.
- Verification: N/A.
- Follow-up needed: Add a `user_timezone: str` param to `UsableTimeService.calculate()`, convert routine/meal/commute/sleep blocks to UTC via `zoneinfo`, and subtract them from the usable window. TIME-042 (Sleep/Wake Signal Integration) is now done, so all of Phase 9's signals exist — this integration is unblocked and should be scheduled as its own ticket before or alongside Phase 10, per the recommendation-engine skill's "Empty calendar time ≠ available time" principle.

## Issue: SleepWakeEvent wake-time comparison is UTC-only, same as RoutineAssumption/CommuteService
- Date: 2026-07-05
- Area: `backend/app/services/morning_replan.py`
- Symptom: `MorningReplanService` treats a `wake_time`'s UTC hour/minute as if it were the user's local minute-of-day when comparing against the "sleep" RoutineAssumption's `end_minute`. A user outside UTC will get late-wake detection offset by their UTC difference.
- Root cause: No per-user timezone field or conversion exists yet anywhere in the codebase (see the RoutineAssumption issue above) — TIME-042 deliberately followed the same established simplification rather than solving timezone handling a fourth time in isolation.
- Fix: Not applied — deferred to the same unified timezone-awareness ticket as the RoutineAssumption issue above.
- Files changed: None yet.
- Verification: N/A.
- Follow-up needed: Resolved by the same `UsableTimeService` timezone pass referenced above; no separate fix needed once that lands.

## Issue: Notification orchestration (TIME-043) Celery beat schedule and Learning Mode window are both placeholders
- Date: 2026-07-05
- Area: `backend/app/workers/celery_app.py`, `backend/app/services/notification_service.py`
- Symptom: (1) The morning/learning/evening beat times (8am/10am/9pm) are UTC, not per-user-local — same known simplification as everywhere else timezone-sensitive in this codebase. (2) The Learning Mode window gating `maybe_send_learning_prompt()` is a fixed 14 days (reusing the trial length) rather than the data-driven "ends based on enough data" behavior already logged as a deferred decision.
- Root cause: No per-user timezone handling exists yet (see the RoutineAssumption/SleepWakeEvent issues above); a data-driven Learning Mode end date depends on scorer/recommendation signal-quality thresholds that don't exist yet either.
- Fix: Not applied — (1) will be resolved by the same `UsableTimeService` timezone pass referenced above extending to Celery beat scheduling; (2) is intentionally out of scope for TIME-043 per its Non-Goals, to avoid a second, conflicting partial implementation of the deferred data-driven learning-period decision.
- Files changed: None yet.
- Verification: N/A.
- Follow-up needed: Once per-user timezone support exists, beat scheduling should either move to per-user local-time task dispatch or the tasks should filter by "is it currently 8am/9pm in this user's timezone" rather than firing globally at a fixed UTC hour. The Learning Mode window should be replaced once the data-driven end-of-learning-period logic is built.

## Issue: Devcontainer firewall script breaks Docker Desktop for Mac embedded DNS
- Date: 2026-07-04
- Area: `.devcontainer/` (yolo-mode sandbox for `claude --dangerously-skip-permissions`)
- Symptom: `postStartCommand` (the egress-firewall init script) failed with `curl: (6) Could not resolve host` immediately when fetching GitHub's IP ranges, on a freshly created container.
- Root cause: Two distinct bugs stacked on top of each other. (1) The upstream `anthropics/claude-code` reference `init-firewall.sh` flushes the `nat` table (`iptables -t nat -F`) to selectively preserve Docker's embedded-DNS NAT rules; on Docker Desktop for Mac those rules don't textually contain `127.0.0.11` the way they do on Linux Docker Engine, so the grep-and-replay restore silently loses them and DNS breaks permanently for that container. (2) The `ghcr.io/anthropics/devcontainer-features/claude-code` devcontainer feature installs its own bundled copy of `init-firewall.sh` at `/usr/local/bin/init-firewall.sh` during the features build stage, which runs *after* our own Dockerfile's `COPY` — so a same-named custom script gets silently clobbered by the unmodified upstream one, no matter how the Dockerfile/image caching is handled.
- Fix: Our script only touches the `filter` table (no nat/mangle flush at all — a pure egress allowlist doesn't need them). It's installed as `/usr/local/bin/timesense-init-firewall.sh` (distinct name) to avoid the feature's install-time collision. Also added `-exist` to `ipset add` calls since two allowlisted domains can resolve to the same IP.
- Files changed: `.devcontainer/init-firewall.sh`, `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`
- Verification: `npx @devcontainers/cli up --workspace-folder .` then confirmed inside the container: DNS resolves, `https://example.com` is blocked, `https://api.github.com/zen` and `https://api.stripe.com` succeed, `claude --version` works, Postgres/Redis reachable.
- Follow-up needed: None currently. If the `claude-code` feature is ever bumped or the Dockerfile base image changes, re-verify the firewall still runs cleanly (rebuild with `docker compose -p timesense_devcontainer -f .devcontainer/docker-compose.yml build --no-cache devcontainer`).

## Format

```
## Issue: [short title]
- Date: 
- Area: 
- Symptom: 
- Root cause: 
- Fix: 
- Files changed: 
- Verification: 
- Follow-up needed: 
```
