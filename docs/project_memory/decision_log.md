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

## Deferred Decisions

- Decision: Gmail / Apple Mail integration
  Why deferred: Depends on complexity. Email may become an inbox manager, violating core rules.
  Trigger for revisiting: After launch, if user demand is high and a lightweight, non-inbox approach is clear.

- Decision: Monthly vs. annual vs. founder plan availability per platform
  Why deferred: Apple App Store and Google Play may not support identical introductory offer mechanics.
  Trigger for revisiting: During Phase 3 implementation, when StoreKit and Google Play products are configured.
