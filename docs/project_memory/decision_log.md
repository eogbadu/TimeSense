# Decision Log

## Product Decisions

- Decision: Product name is TimeSense
  Reason: Defined in spec
  Date: 2026-07-03

- Decision: Tagline is "Don't make managing your day another job."
  Reason: Core product rule defined in spec
  Date: 2026-07-03

- Decision: Native mobile apps — Swift/SwiftUI for iOS, Kotlin/Jetpack Compose for Android
  Reason: Deep OS-level behavior, premium mobile polish, widgets, health/calendar/reminder integrations, notifications, alarm awareness require native tooling. React Native cannot meet the bar.
  Date: 2026-07-03

- Decision: Web app is companion dashboard only (not primary product)
  Reason: Mobile is the daily-use interface. Web supports account setup, subscription management, integrations, settings, insights, admin.
  Date: 2026-07-03

- Decision: No Projects at launch
  Reason: Projects would turn TimeSense into a project management system, violating the core product rule.
  Date: 2026-07-03

- Decision: Goals included as a simple list (no categories, no project system)
  Reason: Goals influence recommendations and insights without adding management overhead.
  Date: 2026-07-03

- Decision: No file/document upload at launch
  Reason: Launch is focused on mobile-first real-day intelligence. File Q&A and document parsing are explicitly deferred.
  Date: 2026-07-03

- Decision: Calendar writes always require explicit user approval
  Reason: Trust. TimeSense may recommend changes but must not alter the user's calendar without consent.
  Date: 2026-07-03

- Decision: Replans require user approval
  Reason: Same trust principle. TimeSense suggests; user decides.
  Date: 2026-07-03

- Decision: No drag-and-drop schedule editor
  Reason: Managing the schedule should not become a job. TimeSense suggests adjustments; users approve.
  Date: 2026-07-03

- Decision: 14-day Premium trial requires payment information
  Reason: Subscription model requirement. Avoids trial abuse and ensures trial users experience the full product.
  Date: 2026-07-03

- Decision: Pricing — $14.99/month · $99/year · $79/year Founder
  Reason: Defined in spec.
  Date: 2026-07-03

- Decision: Free Basic Mode after trial expiry (not a full free tier)
  Reason: Premium features require backend intelligence that is expensive to run. Basic mode maintains user presence without full cost.
  Date: 2026-07-03

- Decision: Pause premium background syncs in Free Basic Mode; keep connection tokens where secure
  Reason: Avoids wasted API calls and backend costs while making it easy to resume premium instantly after subscribing.
  Date: 2026-07-03

- Decision: Waitlist, invite codes, referral system, and admin dashboard at launch
  Reason: Controlled rollout, cost management, bug management, early-adopter scarcity.
  Date: 2026-07-03

- Decision: Raw audio storage and model training use require separate explicit opt-in
  Reason: Privacy positioning. Users stay in control.
  Date: 2026-07-03

- Decision: Individual user first; no family/shared mode at launch
  Reason: Focus. Family/shared mode is a separate product problem.
  Date: 2026-07-03

- Decision: Meal tracking is lightweight only (no calories, macros, nutrition)
  Reason: Meal tracking is about time/context (when, skipped, eating while working), not diet.
  Date: 2026-07-03

- Decision: Hygiene is grouped into simple routine blocks (not detailed checklist tracking)
  Reason: Morning/evening hygiene affects usable time; individual action tracking is not needed.
  Date: 2026-07-03

- Decision: Learning period ends based on enough data, not a fixed number of days
  Reason: Users onboard at different paces. Data quality is a better signal than elapsed time.
  Date: 2026-07-03

## Technical Decisions

- Decision: FastAPI + PostgreSQL + Redis/Celery backend
  Reason: FastAPI is fast, type-safe, and well-suited to async LLM/integration calls. PostgreSQL is the primary data store. Redis/Celery handles background sync and notification jobs.
  Date: 2026-07-03

- Decision: Firebase Auth for authentication
  Reason: Cross-platform (iOS/Android/web) with minimal server-side session management. Works well with StoreKit and Google Play.
  Date: 2026-07-03

- Decision: LLM layer must be provider-agnostic (OpenAI default)
  Reason: Avoids vendor lock-in. Anthropic, Gemini, or another provider can be added without rewriting core logic.
  Date: 2026-07-03

- Decision: Stripe for web payments, StoreKit for iOS, Google Play Billing for Android, unified backend entitlement
  Reason: App Store and Play Store require platform-native billing. Stripe handles web. Backend normalizes all three into one entitlement state.
  Date: 2026-07-03

- Decision: Docker for backend/web infrastructure only (not iOS, not Android)
  Reason: Native mobile tooling (Xcode, Android Studio) cannot run in Docker. Docker is for PostgreSQL, Redis, FastAPI, and Celery.
  Date: 2026-07-03

- Decision: Provider abstractions for all integrations (calendar, LLM, notifications, task sources)
  Reason: Core product logic must not be coupled to any single provider. Makes swapping or adding providers low-risk.
  Date: 2026-07-03

- Decision: Bottom tabs: Now, Today, Capture, Insights, Settings (no Tasks tab, no Projects tab, no Routines tab)
  Reason: Spec requirement. Keeps navigation centered on the assistant experience, not task management.
  Date: 2026-07-03

- Decision: "not_now" feedback suppresses a task from recommendations for a 4-hour cooldown, not permanently or just-for-this-response
  Reason: The recommendation-engine skill's "do not nag" rule means a dismissed task shouldn't be re-suggested immediately, but a still-pending task also shouldn't disappear from recommendations for the rest of the day just because the user dismissed it once. 4 hours was chosen as a reasonable middle ground pending real usage data.
  Date: 2026-07-04

- Decision: Routine assumption blocks (TIME-039) are stored as minutes-since-local-midnight integers, not a Time/datetime column, and are not yet subtracted from UsableTimeService
  Reason: A recurring daily block doesn't need a date component, and integers avoid DB-driver Time-type quirks across SQLite (tests) and Postgres. The usable-time integration is deferred until UsableTimeService gains real timezone awareness (currently UTC-midnight-only) — doing it once for routines+meals+commute together after TIME-040–042 avoids three partial, soon-to-be-redone integrations.
  Date: 2026-07-05

- Decision: A late wake (TIME-042) is detected by comparing SleepWakeEvent.wake_time against the user's existing "sleep" RoutineAssumption end_minute (TIME-039), not a separate assumed-wake-time field
  Reason: RoutineAssumption already models the user's assumed sleep window per the Phase 9 data model; adding a second, disconnected "expected wake time" concept would let the two drift out of sync. A user editing their sleep routine (PATCH /api/v1/routines/sleep) automatically updates what counts as a late wake.
  Date: 2026-07-05

- Decision: A sleep-triggered morning replan reuses NotificationService.propose_replan/ReplanRequest verbatim, with no sleep-specific replan type or approval endpoint
  Reason: The product rule that replans always require explicit approval is already fully implemented; inventing a parallel mechanism for one more trigger source would duplicate the approve/reject/expiry logic for no benefit. The existing /api/v1/notifications/replans/{id}/approve|reject routes handle it identically to any other replan.
  Date: 2026-07-05

- Decision: Notification mode behavior (TIME-043) maps gentle -> evening check-out only, balanced -> morning + evening check-ins, active_coach -> both check-ins plus learning prompts
  Reason: The product brief already frames "Active Coach" as the persona associated with the early Learning Mode window ("First few weeks: Active Coach / Learning Mode"), so gating learning prompts on active_coach specifically reuses existing product language instead of inventing a fourth, disconnected notification concept.
  Date: 2026-07-05

- Decision: TIME-043's learning prompt uses a fixed 14-day window (reusing the existing trial length) rather than building the data-driven "learning period ends based on enough data" logic
  Reason: That data-driven behavior was already logged as a deferred decision (2026-07-03) and depends on signal/data-quality thresholds that don't exist yet in the scorer/recommendation engine. Building a second, ad hoc version of it here would conflict with that future implementation; reusing the trial length is a defensible placeholder that's easy to find and replace later.
  Date: 2026-07-05

- Decision: TIME-044's iOS widgets read a shared App-Group snapshot the host app writes; the widget extension has no network or auth code of its own
  Reason: `APIClient.swift` only ever holds the Firebase ID token in memory (never persisted to Keychain), refreshed via Firebase's auth-state listener while the app process is alive. A widget extension is a separate process with no access to that in-memory token, so giving it independent network calls would require inventing a second, Keychain-shared token-refresh path. Writing a small Codable snapshot to a shared UserDefaults suite after the app's own authenticated fetches — and calling `WidgetCenter.shared.reloadAllTimelines()` — is the standard WidgetKit pattern and avoids that duplication entirely.
  Date: 2026-07-05

- Decision: The new `TimeSenseWidgetExtension` target was added by scripting the `xcodeproj` Ruby gem (`gem install xcodeproj --user-install`) rather than hand-editing `project.pbxproj` or relying on the Xcode GUI
  Reason: A new native target touches build phases, an embed/copy-files phase, a target dependency, and per-configuration build settings across two targets — order-sensitive, easy-to-typo pbxproj surgery that's much safer done through a library that understands the file format than via text edits, and this environment has no way to drive the Xcode GUI's "New Target" wizard. The one-off wiring script was deleted after running it once; the resulting `project.pbxproj` is the artifact that matters going forward.
  Date: 2026-07-05

- Decision: TIME-045's Android widgets use Jetpack Glance (androidx.glance:glance-appwidget) rather than legacy RemoteViews/AppWidgetProvider with XML layouts
  Reason: Glance is Jetpack's Compose-for-widgets library, keeping widget UI code in Kotlin/Compose per the project's "Kotlin and Jetpack Compose exclusively" rule (CLAUDE.md/AGENTS.md), rather than introducing a second, XML-layout-based UI paradigm just for widgets.
  Date: 2026-07-05

- Decision: TIME-045's two widgets each read their own independent Glance Preferences state (no shared cross-widget snapshot, unlike TIME-044's iOS WidgetSnapshot)
  Reason: Android AppWidgets run in the same process as the host app (no separate extension process like iOS's WidgetKit target), so there's no equivalent of the App-Group-sharing problem TIME-044 solved. Each widget's data comes from exactly one ViewModel (NowViewModel owns usable minutes, TodayViewModel owns the next event), so giving each its own state is simpler than inventing a merged blob two ViewModels would need to coordinate around.
  Date: 2026-07-05

- Decision: WeeklyInsight rows are generated once per (user, week_start) and cached forever — a completed week is never silently recomputed
  Reason: Past weeks' underlying data (tasks, meals, sleep, commute, feedback) doesn't change after the fact, so recomputing would only add cost/latency for an identical result, and would risk producing a different LLM summary for the same historical week if regenerated later. Idempotent generation also makes the weekly Celery job and the on-demand API-triggered generation safely overlap without duplicate rows (enforced by a DB unique constraint on user_id+week_start).
  Date: 2026-07-05

- Decision: TIME-046 only summarizes fully-completed Monday-Sunday weeks, never "this week so far"
  Reason: A partial week's numbers (e.g. "1 of 1 tasks done" on a Tuesday) are noisy and could read as judgmental or misleading before the week is over — the product's "no guilt-driven copy" rule (product_brief.md) argues against surfacing incomplete-week statistics as if they were meaningful trends.
  Date: 2026-07-05

- Decision: No new `Task.completed_at` column — TIME-046 approximates completion timing via `updated_at`
  Reason: Adding a real completed-at timestamp is a task-model schema change bigger than this ticket's "weekly summary" scope; `updated_at` is close enough for a v1 insight and the limitation is explicitly documented (known_issues.md) rather than silently accepted.
  Date: 2026-07-05

- Decision: TIME-047's Android time editor reuses one Material3 `TimePicker` with Starts/Ends toggle buttons rather than a two-field time-range picker
  Reason: Material3 has no built-in time-range picker component, and pulling in a third-party library for a single settings edit flow was more dependency weight than the feature warranted. iOS's two side-by-side `DatePicker(.hourAndMinute)` fields don't have this constraint, so the two platforms' edit UIs are shaped slightly differently — an intentional, scope-appropriate platform difference, not an inconsistency to fix.
  Date: 2026-07-05

- Decision: TIME-048 built the backend admin endpoints the ticket sequence's scope line assumed already existed, rather than shipping a dashboard with dead-end pages
  Reason: Confirmed directly with the user before proceeding (only user-listing and invite-code management had real admin endpoints; subscriptions/feedback/integrations/metrics/waitlist had none). Building the real thing keeps the codebase's established pattern of "every ticket delivers a working feature," not a UI shell with nothing behind it.
  Date: 2026-07-05

- Decision: Web app admin role-gating checks GET /api/v1/users/me client-side for UX, but the server-side AdminUser FastAPI dependency remains the actual security boundary
  Reason: Client-side checks can always be bypassed by a motivated user (dev tools, direct API calls); they only exist to give a non-admin a clean "access denied" screen instead of a confusing empty/erroring dashboard. This mirrors the existing backend comment in admin.py: "the route existence is not hidden, but the data is access-controlled at the dependency level."
  Date: 2026-07-05

- Decision: Firebase Auth construction in the web app is lazy (`getFirebaseAuth()`), not eager at module load
  Reason: `getAuth()` validates the API key eagerly and throws `auth/invalid-api-key` immediately when it's empty — even during `next build`'s static prerendering, which has nothing to do with a real user visiting the page. Since no real Firebase project exists yet (same gap as iOS/Android), eager construction would have permanently broken the production build. Lazy construction, guarded by `isFirebaseConfigured`, keeps the build green and defers the failure to actual runtime sign-in attempts, where it belongs.
  Date: 2026-07-05

- Decision: TIME-049's Slack action items are detected → queued as *pending* → user-confirmed before any Task is created; scanning never auto-creates Tasks
  Reason: The product's core trust principle (calendar writes and replans always require approval) extends naturally to "don't turn every Slack message into a task behind the user's back." Reusing the exact request→approve shape of the calendar PendingCalendarAction flow keeps the mental model consistent and the approval gate auditable (SlackActionItem.status + created_task_id).
  Date: 2026-07-05

- Decision: TIME-049 introduced a generic MessageSourceProvider abstraction (not a Slack-specific service) even though only Slack implements it today
  Reason: TIME-050 (Teams) is the very next ticket and is the same shape — read messages, detect action items, approve into tasks. Building the read-only-chat-source ABC now (mirroring the existing CalendarProvider ABC) means Teams is a new provider class + registry entry, not a re-architecture. Matches the integration-provider-pattern skill's "core logic calls the interface, never a provider directly."
  Date: 2026-07-05

- Decision: TIME-050 shared only the LLM detection (extracted ActionItemDetectionService) between Slack and Teams; the models/repos/service/schemas/API stay parallel per-source, NOT unified into one source-tagged message-source schema
  Reason: Rule of three — Slack was the first message source, Teams is the second, so one duplication is acceptable; a premature unification would mean a churny migration of the just-merged Slack tables for speculative future reuse. The genuinely shared piece (a single copy of the action-item-detection prompt/logic) was worth extracting immediately since two divergent copies of an LLM prompt is a real maintenance hazard. The repo's own precedent (commute/meal/sleep are similarly parallel per-feature tables) supports parallel-until-proven. Unify on the third message-source integration if the shape holds.
  Date: 2026-07-05

- Decision: TIME-051 gave Notion its own TaskSourceProvider abstraction rather than bending it into the MessageSourceProvider/ActionItemDetectionService used by Slack/Teams (chosen by the user when asked)
  Reason: Notion is fundamentally a different kind of source: a database row is already a discrete, structured task, whereas Slack/Teams are noisy chat streams where an LLM must decide "is this even an action item?". Modeling Notion as a task source (structured title/due extraction, no LLM, import/dismiss framing) is honest to what it is; forcing it through the message-source pipeline would mean either running a pointless LLM detection pass over already-structured tasks or awkwardly stubbing detection. The two abstractions (MessageSourceProvider for chat, TaskSourceProvider for structured task systems) also line up with the integration-provider-pattern skill's own split between "communication integrations" and "task/reminder integrations" (Todoist/Things/Apple Reminders will slot under TaskSourceProvider next).
  Date: 2026-07-05

- Decision: TIME-059 renamed the iOS bundle identifiers + App Group from the placeholder com.timesense.app to the user's registered App ID com.aetheranalytics.timesense (Team WB5NV894N5), aligning the project with the real Apple Developer account; the Android applicationId (com.timesense.app) was left unchanged
  Reason: The user confirmed their real Apple account/Team is in .env and asked to use it; a device build can only provision against the *registered* App ID, so the project's bundle IDs had to match com.aetheranalytics.timesense (cascading to the widget extension bundle ID and the shared App Group, which must be identical across both entitlements files + WidgetSnapshot.appGroupID or the widget can't read the app's snapshot). Android's applicationId is a separate Google Play registration and was deliberately not touched by this iOS-only signing ticket. Verified real-account provisioning as far as headlessly possible: the App Store Connect API key authenticated and signing reached profile generation, stopping only at "no registered device" — the expected boundary, since a development profile needs a device UDID the headless environment doesn't have.
  Date: 2026-07-05

- Decision: iOS Firebase SDK pinned to 11.x (resolved 11.15.0), not the latest 12.x; GoogleSignIn-iOS added as a separate package; GoogleService-Info.plist kept gitignored (not committed)
  Reason: Firebase 12.15.x's Package.swift declares Swift tools-version 6.1, which this environment's Xcode 16.0 / Swift 6.0 can't parse ("incompatible tools version") — so 12.x can't resolve here; 11.x (tools 5.9/6.0) does. GoogleSignIn is a distinct package from firebase-ios-sdk and the real AuthService imports it for signInWithGoogle, so it must be linked separately (surfaced as "no such module 'GoogleSignIn'" once Firebase compiled the previously-stubbed code). The plist follows the repo's existing .gitignore convention (client config is per-developer, downloaded from the console) — the committed reproducible bits are project.pbxproj (package refs/links) + Package.resolved.
  Date: 2026-07-05

## Deferred Decisions

- Decision: Gmail / Apple Mail integration
  Why deferred: Depends on complexity. Email may become an inbox manager, violating core rules.
  Trigger for revisiting: After launch, if user demand is high and a lightweight, non-inbox approach is clear.

- Decision: Monthly vs. annual vs. founder plan availability per platform
  Why deferred: Apple App Store and Google Play may not support identical introductory offer mechanics.
  Trigger for revisiting: During Phase 3 implementation, when StoreKit and Google Play products are configured.
