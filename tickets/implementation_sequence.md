# TimeSense Implementation Sequence

This is the master ordered list of Jira tickets for TimeSense. Work through these in order. Do not skip phases without explicit approval.

---

## Phase 0 — Repository, Memory, Workflow, and Skills Bootstrap

### TIME-001: Repository, Memory, and Workflow Bootstrap
Goal: Create the repository operating system before any product code.
Scope: README, AGENTS.md, CLAUDE.md (operational), CHANGELOG, docs/, project memory files, workflow docs, ticket sequence, PR template, Claude skills, agent subagent docs.
Non-goals: No product application code.
Acceptance: Repo understandable from docs alone. Claude can resume from project memory without chat history.
Verification: Confirm all required files exist. Confirm context_summary.md is complete.
Memory updates: All project_memory/ files, CHANGELOG.md.
Status: IN PROGRESS

---

## Phase 1 — Backend Foundation

### TIME-002: FastAPI App Structure and Health Endpoint
Goal: Bootstrap the FastAPI backend with project structure, config, and health check.
Scope: FastAPI app shell, config/settings, health endpoint, CORS middleware, error handling foundation.
Non-goals: No database yet. No auth yet. No business logic.
Files: backend/app/main.py, backend/app/core/config.py, backend/requirements.txt
Acceptance: Backend starts. GET /health returns 200. Structure follows service/repository pattern.
Verification: uvicorn app.main:app --reload; curl localhost:8000/health
Memory: implementation_log, phase_status, change_summary, context_summary

### TIME-003: PostgreSQL Connection and Alembic Migrations
Goal: Connect FastAPI to PostgreSQL and set up migration tooling.
Scope: SQLAlchemy async engine, Alembic config, base model, initial migration.
Non-goals: No application tables yet.
Files: backend/app/core/database.py, backend/alembic/, backend/alembic.ini
Acceptance: Database connects. alembic upgrade head runs. alembic revision works.
Verification: alembic upgrade head; alembic current

### TIME-004: Redis and Celery Background Worker Setup
Goal: Add Redis connection and Celery worker for background jobs.
Scope: Redis connection, Celery app, health-check task, worker startup command.
Non-goals: No application tasks yet.
Files: backend/app/core/redis.py, backend/app/workers/celery_app.py
Acceptance: Worker starts. Health-check task runs. Redis connects.
Verification: celery -A app.workers.celery_app worker --loglevel=info

### TIME-005: Firebase Auth Integration and Protected Routes
Goal: Verify Firebase Auth JWTs server-side and protect routes.
Scope: Firebase Admin SDK setup, JWT verification dependency, current_user dependency, admin role check.
Non-goals: No user model in DB yet.
Files: backend/app/core/firebase.py, backend/app/core/security.py, backend/app/api/v1/auth.py
Acceptance: Valid Firebase JWT returns user info. Invalid token returns 401. Admin role check works.
Verification: pytest backend/tests/test_auth.py

### TIME-006: Docker Compose for Backend Infrastructure
Goal: Provide a reproducible local dev environment for backend/web infrastructure.
Scope: docker-compose.yml for PostgreSQL, Redis, FastAPI, Celery worker. .env.example files.
Non-goals: No iOS or Android in Docker. No production config yet.
Files: docker-compose.yml, backend/.env.example
Acceptance: docker compose up starts all services. Health check passes.
Verification: docker compose up -d; curl localhost:8000/health

---

## Phase 2 — Core Data Model and Auth

### TIME-007: User and Profile Data Model
Goal: Create core user, profile, and preferences schema.
Scope: users table, user_profiles table, user_preferences table, Alembic migrations.
Non-goals: No subscription tables yet.
Files: backend/app/models/user.py, backend/app/models/profile.py, migrations/
Acceptance: Tables created. User can be created and retrieved.
Verification: alembic upgrade head; pytest backend/tests/test_users.py

### TIME-008: Assistant Personality and Onboarding State
Goal: Persist assistant personality choice and onboarding progress.
Scope: assistant_personality_settings table, onboarding_state field on user, API endpoints to read/write.
Non-goals: No full onboarding flow yet.
Files: backend/app/models/user.py, backend/app/api/v1/users.py, backend/app/services/user_service.py
Acceptance: Personality persists. Onboarding state persists. API endpoints work.
Verification: pytest backend/tests/test_user_preferences.py

### TIME-009: Consent Records
Goal: Store user consent decisions for privacy/data use.
Scope: consent_records table, consent API endpoint, audio/training consent fields.
Non-goals: No UI for consent yet.
Files: backend/app/models/consent.py, backend/app/api/v1/privacy.py
Acceptance: Consent records can be created and read. Required consent fields exist.
Verification: pytest backend/tests/test_consent.py

### TIME-010: Admin Role Enforcement
Goal: Protect admin-only routes and add admin role model.
Scope: Role field on users, admin-only FastAPI dependency, /admin route foundation, admin audit log.
Non-goals: No admin dashboard UI yet.
Files: backend/app/core/security.py, backend/app/api/v1/admin.py, backend/app/models/audit.py
Acceptance: Admin routes reject non-admin users. Admin actions logged.
Verification: pytest backend/tests/test_admin_auth.py

---

## Phase 3 — Cross-Platform Subscription Entitlements

### TIME-011: Subscription Data Model
Goal: Create unified subscription entitlement schema.
Scope: subscriptions table, payment_sources table, subscription_events table, subscription_entitlements view/table.
Non-goals: No Stripe/Apple/Google integration yet.
Files: backend/app/models/subscription.py, migrations/
Acceptance: Tables created. Entitlement model supports trialing/active/grace_period/canceled/expired/refunded states.
Verification: alembic upgrade head; pytest backend/tests/test_subscription_model.py

### TIME-012: Stripe Web Payments Foundation
Goal: Implement Stripe checkout, customer portal, and webhooks for web subscriptions.
Scope: Stripe customer creation, checkout session, customer portal, webhook handler, entitlement update on webhook events.
Non-goals: No Apple/Google billing yet.
Files: backend/app/api/v1/subscriptions.py, backend/app/services/stripe_service.py, backend/app/api/v1/webhooks/stripe.py
Acceptance: Stripe checkout works. Webhook updates entitlement. Idempotent webhook handling.
Verification: Stripe test mode events; pytest backend/tests/test_stripe.py

### TIME-013: Apple StoreKit Server Notifications
Goal: Receive and process Apple App Store Server Notifications to update entitlement.
Scope: Apple notification endpoint, transaction validation, entitlement update, idempotency.
Non-goals: No StoreKit client code yet.
Files: backend/app/api/v1/webhooks/apple.py, backend/app/services/apple_billing_service.py
Acceptance: Apple notification endpoint receives and processes events. Entitlement updates correctly.
Verification: pytest backend/tests/test_apple_billing.py

### TIME-014: Google Play Real-Time Developer Notifications
Goal: Receive and process Google Play Billing notifications to update entitlement.
Scope: Google notification endpoint, purchase token validation, entitlement update, idempotency.
Non-goals: No Google Play client code yet.
Files: backend/app/api/v1/webhooks/google.py, backend/app/services/google_billing_service.py
Acceptance: Google notification endpoint processes events. Entitlement updates correctly.
Verification: pytest backend/tests/test_google_billing.py

### TIME-015: Trial Logic and Free Basic Mode
Goal: Implement 14-day trial, trial-to-paid conversion, and Free Basic Mode downgrade.
Scope: Trial start, trial end, premium feature gating, Free Basic Mode state, premium sync pause.
Non-goals: No mobile paywall UI yet.
Files: backend/app/services/entitlement_service.py, backend/app/api/v1/subscriptions.py
Acceptance: Trial starts correctly. Expired trial downgrades to Free Basic Mode. Premium gates work.
Verification: pytest backend/tests/test_trial_entitlement.py

### TIME-016: Referral Program
Goal: Implement referral tracking and reward logic.
Scope: referrals table, referral code generation, referral reward on paid conversion (1 month each).
Non-goals: No referral UI yet.
Files: backend/app/models/referral.py, backend/app/services/referral_service.py
Acceptance: Referral code generates. Reward activates on paid conversion. No double-reward.
Verification: pytest backend/tests/test_referral.py

### TIME-017: Waitlist and Invite Codes
Goal: Implement waitlist and invite-code access control.
Scope: waitlist_entries table, invite_codes table, invite validation on signup, admin invite code management.
Non-goals: No waitlist UI yet.
Files: backend/app/models/invite.py, backend/app/services/invite_service.py, backend/app/api/v1/invites.py
Acceptance: Invite codes work. Signup blocked without valid code. Admin can create/disable codes.
Verification: pytest backend/tests/test_invites.py

---

## Phase 4 — Mobile App Shells

### TIME-018: iOS App Shell — Navigation and Core Screens
Goal: Create the native SwiftUI app with bottom navigation and placeholder screens.
Scope: Xcode project, SwiftUI app shell, TabView with Now/Today/Capture/Insights/Settings, design tokens, empty states, API client foundation.
Non-goals: No deep integrations. No production data.
Files: ios/TimeSense/ (full SwiftUI project)
Acceptance: App builds. Bottom navigation works. Screens exist. Premium UX direction established.
Verification: xcodebuild build; simulator screenshots

### TIME-019: Android App Shell — Navigation and Core Screens
Goal: Create the native Kotlin/Compose app with bottom navigation and placeholder screens.
Scope: Android Studio project, Compose app shell, BottomNavigation with Now/Today/Capture/Insights/Settings, design tokens, empty states, API client foundation.
Non-goals: No deep integrations. No production data.
Files: android/app/src/main/ (full Compose project)
Acceptance: App builds. Bottom navigation works. Screens exist. Premium UX direction established.
Verification: ./gradlew build; emulator screenshots

---

## Phase 5 — Onboarding and Permission Education

### TIME-020: iOS Onboarding Flow
Goal: Implement the full onboarding experience on iOS.
Scope: Welcome screen, path selection, personality selection, Learning Mode explanation, integration setup screens, permission education, consent, trial/paywall entry.
Files: ios/TimeSense/Features/Onboarding/
Acceptance: User can complete onboarding. Skip integrations and add later. Consent and personality persist. Trial/paywall reachable.

### TIME-021: Android Onboarding Flow
Goal: Implement the full onboarding experience on Android.
Scope: Same scope as TIME-020 but in Kotlin/Compose.
Files: android/app/src/main/kotlin/com/timesense/ui/onboarding/
Acceptance: Same criteria as TIME-020.

### TIME-022: Backend Onboarding State APIs
Goal: Backend endpoints for saving and resuming onboarding state.
Scope: Onboarding state model, API endpoints, preference persistence, consent persistence.
Files: backend/app/api/v1/users.py, backend/app/services/onboarding_service.py
Acceptance: Onboarding state persists across app restart. Consent records stored.

---

## Phase 6 — Calendar and Reminder Integrations Foundation

### TIME-023: Calendar Provider Abstraction
Goal: Build the calendar provider interface and integration model.
Scope: CalendarProvider abstract class, calendar_accounts model, calendar_events model, provider registry, write-approval gate.
Files: backend/app/integrations/calendar/base.py, backend/app/models/calendar.py

### TIME-024: Apple Calendar (EventKit) Integration
Goal: Read calendar events from Apple Calendar on iOS.
Scope: EventKit permission request, event read, classification, sync to backend.
Files: ios/TimeSense/Services/CalendarService.swift, backend/app/integrations/calendar/apple.py

### TIME-025: Google Calendar Integration
Goal: Read calendar events from Google Calendar via OAuth.
Scope: OAuth flow, token storage, event read, sync to backend.
Files: backend/app/integrations/calendar/google.py, backend/app/api/v1/integrations/google_calendar.py

### TIME-026: Outlook Calendar Integration
Goal: Read calendar events from Outlook via Microsoft Graph OAuth.
Scope: OAuth flow, token storage, event read, sync to backend.
Files: backend/app/integrations/calendar/outlook.py

### TIME-027: Apple Reminders Integration
Goal: Read tasks from Apple Reminders.
Scope: EventKit reminders read, task sync to backend.
Files: ios/TimeSense/Services/RemindersService.swift

### TIME-028: Todoist Integration
Goal: Read tasks from Todoist via API.
Scope: OAuth, task read, sync to backend, write-back approval.
Files: backend/app/integrations/tasks/todoist.py

### TIME-029: Things Integration (if API available)
Goal: Read tasks from Things where app-to-app integration is feasible.
Files: ios/TimeSense/Services/ThingsService.swift

---

## Phase 7 — Now, Today, Capture, and Internal Tasks

### TIME-030: Capture Screen — Text and Voice
Goal: Implement capture on iOS and Android with text input and voice transcript.
Scope: Text capture, voice transcript (speech-to-text), classification, auto-create vs ask-each-time preference.
Files: ios/.../Capture/, android/.../capture/, backend/app/api/v1/capture.py, backend/app/models/captured_item.py

### TIME-031: Today Screen — Realistic Timeline
Goal: Show a full-day realistic timeline with calendar events, routines, and usable time blocks.
Scope: Timeline rendering, calendar event display, routine blocks, past/current/future visual states.
Files: ios/.../Today/, android/.../today/, backend/app/api/v1/timeline.py

### TIME-032: Now Screen — Current Context and Recommendation
Goal: Show the current context, usable time, and best next action on the Now screen.
Scope: Hero card, usable time, basic recommendation from backend, quick actions (Done/Snooze/Not Now/Replan/Ask/Why).
Files: ios/.../Now/, android/.../now/, backend/app/api/v1/recommendations.py (basic)

### TIME-033: Task Model and Internal Reminders
Goal: Implement the task/reminder model and auto-create preference logic.
Scope: tasks table, captured_items table, task-from-capture flow, auto-create vs ask-each-time behavior.
Files: backend/app/models/task.py, backend/app/services/task_service.py

---

## Phase 8 — Recommendation Engine V1

### TIME-034: Usable Time Calculator
Goal: Calculate realistic usable time windows from calendar, routines, meals, prep time.
Scope: UsableTimeCalculator service, focus window detection, prep/transition estimates.
Files: backend/app/services/usable_time.py, backend/app/services/focus_windows.py

### TIME-035: Task Scoring Service
Goal: Score task candidates against current context.
Scope: TaskScorer service, scoring from priority/deadline/energy/focus window/usable time/goals.
Files: backend/app/services/task_scorer.py

### TIME-036: Recommendation API V1
Goal: Return one best recommendation and two alternatives to the mobile app.
Scope: /recommendations endpoint, scoring integration, LLM explanation via gateway, "Why this?" field.
Files: backend/app/api/v1/recommendations.py, backend/app/services/recommendation_service.py

### TIME-037: LLM Gateway
Goal: Build the provider-agnostic LLM abstraction layer.
Scope: LLMGateway abstract class, OpenAIGateway implementation, prompt templates for recommendation explanations.
Files: backend/app/llm/gateway.py, backend/app/llm/providers/openai.py

### TIME-038: Feedback Collection
Goal: Store and process user feedback on recommendations.
Scope: recommendation_feedback table, feedback API endpoint, feedback signal integration into scorer.
Files: backend/app/models/recommendation.py, backend/app/api/v1/recommendations.py

---

## Phase 9 — Routines, Meals, Commute, Sleep/Wake

### TIME-039: Routine Assumptions Model
Goal: Build the routine assumption model and management.
Scope: routine_assumptions table, routine API, settings edit flow for learned assumptions.
Files: backend/app/models/routine.py, backend/app/api/v1/routines.py

### TIME-040: Meal Tracking (Lightweight)
Goal: Track meal timing and skipped meals for context.
Scope: meal_events table, meal log API, meal-skip detection, meal status in recommendations.
Files: backend/app/models/meal.py, backend/app/api/v1/meals.py

### TIME-041: Commute Detection
Goal: Use location and calendar patterns to detect commutes.
Scope: commute_events table, location permission model, commute detection heuristic, confirmation prompt.
Files: backend/app/models/commute.py, backend/app/services/commute_service.py

### TIME-042: Sleep/Wake Signal Integration
Goal: Incorporate Apple Health sleep/wake data into morning replans.
Scope: HealthKit sleep data read (iOS), sleep_wake_events table, morning replan suggestion on late wake.
Files: ios/.../HealthService.swift, backend/app/models/sleep_wake.py, backend/app/services/morning_replan.py

---

## Phase 10 — Notifications, Widgets, Ambient Surfaces

### TIME-043: Notification Modes and Learning Prompts
Goal: Implement notification modes (Gentle/Balanced/Active Coach) and learning prompts.
Scope: notification_events table, notification mode preference, morning check-in, evening check-out, learning prompts.
Files: backend/app/services/notification_service.py, backend/app/workers/notification_tasks.py

### TIME-044: iOS Widgets
Goal: Create iOS home screen and lock screen widgets.
Scope: WidgetKit extension, usable-time widget, next-event widget, best-next-action widget.
Files: ios/TimeSenseWidget/

### TIME-045: Android Widgets
Goal: Create Android home screen widgets.
Scope: AppWidget implementation, usable-time widget, next-event widget.
Files: android/.../widgets/

---

## Phase 11 — Insights and Learning Summary

### TIME-046: Weekly Insights Generation
Goal: Generate weekly learning summaries.
Scope: Weekly insight generation service, insight storage, Insights screen on iOS and Android.
Files: backend/app/services/insights_service.py, ios/.../Insights/, android/.../insights/

### TIME-047: Learned Assumptions Settings
Goal: Allow users to view and edit what TimeSense has learned.
Scope: Learned assumptions display, edit flow in Settings.
Files: ios/.../Settings/LearnedAssumptionsView.swift, android/.../settings/

---

## Phase 12 — Admin Dashboard

### TIME-048: Admin Dashboard Foundation (Web)
Goal: Build the admin web dashboard with key metrics and management tools.
Scope: /admin route (role-protected), user search, invite code management, subscription/trial view, feedback review, integration status, basic metrics.
Files: web/app/admin/

---

## Phase 13 — Integrations Expansion

### TIME-049: Slack Integration
Goal: Lightweight action-item detection from Slack.
Scope: Slack OAuth, message read, action-item detection, user approval before task creation.
Files: backend/app/integrations/slack.py

### TIME-050: Microsoft Teams Integration
Goal: Lightweight action-item detection from Teams.
Scope: Teams OAuth, message read, action-item detection, user approval.
Files: backend/app/integrations/teams.py

### TIME-051: Notion Integration
Goal: Lightweight task/context extraction from Notion.
Scope: Notion OAuth, page/task read, optional task import.
Files: backend/app/integrations/notion.py

### TIME-052: Siri Shortcuts / App Intents
Goal: Expose TimeSense actions to Siri and Shortcuts.
Scope: App Intents for: what to do next, log lunch, start focus, mark done, replan day.
Files: ios/TimeSense/Intents/

### TIME-053: Google Assistant Integration
Goal: Expose TimeSense actions to Google Assistant.
Scope: Actions on Google / Dialogflow integration for key commands.
Files: backend/app/integrations/google_assistant.py

---

## Phase 14 — Beta Hardening and Launch Readiness

### TIME-054: Error Monitoring and Analytics
Goal: Add error monitoring (Sentry or equivalent) and key analytics events.
Files: backend/app/core/monitoring.py, ios/.../Analytics.swift, android/.../analytics/

### TIME-055: Privacy Review and Data Export
Goal: Implement data deletion and export flows.
Files: backend/app/api/v1/privacy.py

### TIME-056: Security Review and Hardening
Goal: Audit auth, token storage, admin access, rate limiting, webhook security.

### TIME-057: App Store and Play Store Prep
Goal: Prepare metadata, screenshots, privacy policy, App Store review notes.

### TIME-058: Beta Smoke Test and Release Checklist
Goal: Run full beta smoke test. Verify all acceptance criteria. Update all project memory.

---

## Notes

- Tickets may be added, split, or reordered with explicit approval.
- Never bundle unrelated tickets.
- Always update project memory after completing a ticket.
- Each ticket must reference this document as the source of sequence truth.
