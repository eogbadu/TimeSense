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

## Deferred Decisions

- Decision: Gmail / Apple Mail integration
  Why deferred: Depends on complexity. Email may become an inbox manager, violating core rules.
  Trigger for revisiting: After launch, if user demand is high and a lightweight, non-inbox approach is clear.

- Decision: Monthly vs. annual vs. founder plan availability per platform
  Why deferred: Apple App Store and Google Play may not support identical introductory offer mechanics.
  Trigger for revisiting: During Phase 3 implementation, when StoreKit and Google Play products are configured.
