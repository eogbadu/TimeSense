# Context Summary

**Last updated:** 2026-07-04

## Current Build State

Phases 0–2 merged to main. Phases 3 (subscriptions), 4 (mobile shells), and early Phase 5 tasks complete.

Backend API endpoints implemented:
- `GET /api/v1/health`, `GET /api/v1/auth/me`
- `GET/PATCH /api/v1/users/me`, profiles, preferences
- Onboarding state machine, personality, consent records
- Admin routes
- `POST/GET/PATCH/DELETE /api/v1/tasks` (soft-delete)
- `POST /api/v1/capture` (LLM parse → Task)
- Notifications, replan requests

Database tables: users, profiles, preferences, personalities, onboarding_states, consent_records, subscription_records, notification_preferences, replan_requests, tasks, internal_reminders.

Backend tests: 21 (tasks: 15, capture: 6) all passing.

Mobile app shells:
- iOS SwiftUI: bottom tab navigator (Now/Today/Capture/Insights/Settings), AuthService with `#if canImport(FirebaseAuth)` stubs, CaptureViewModel + CaptureView wired to backend. `xcodebuild → BUILD SUCCEEDED`.
- Android Kotlin/Compose: bottom nav, AuthViewModel, CaptureViewModel + CaptureScreen wired to backend. `./gradlew assembleDebug → BUILD SUCCESSFUL`.

## Jira Key Mapping
- TIME-019 (impl seq) → Jira TIME-25 (Android shell) — Done
- TIME-020 → TIME-26 (iOS Firebase Auth) — Done
- TIME-021 → TIME-27 (Android Firebase Auth) — Done
- TIME-022 → TIME-28 (Backend Onboarding State APIs) — Done
- TIME-033 → TIME-29 (Task Model + Internal Reminders) — Done
- TIME-037 → TIME-30 (LLM Gateway) — Done
- TIME-030 → TIME-31 (Capture Screen connect) — Done (PR #23)
- TIME-031 → TIME-32 (Today Screen timeline) — Done (PR #24)
- TIME-032 → TIME-33 (Now Screen context+recommendation) — **Done (PR #25, merged 2026-07-04)**

## Last Completed Work
TIME-032 (Jira TIME-33): Now Screen — current context + best-task recommendation.
- Backend: GET /api/v1/now → greeting + 60-min usable-time stub + highest-priority pending task
- iOS: NowViewModel + NowView with GreetingCard, BestTaskCard, Done/Snooze/Not Now; APIClient.patch() added
- Android: NowViewModel (StateFlow) + NowScreen with same layout

TIME-031 (Jira TIME-32): Today Screen — live timeline.
- Backend: GET /api/v1/timeline/today?date=YYYY-MM-DD → tasks sorted by scheduled_start
- iOS: TodayViewModel + TodayView + TimelineCard (past/current/future visual states)
- Android: TodayViewModel + TodayScreen (LazyColumn) + TimelineCard

## Current Active Task
None.

## Next Recommended Task
TIME-034: Usable Time Calculator (Phase 8 — Recommendation Engine V1)
- Replace the hardcoded 60-minute stub in GET /api/v1/now with real usable-window calculation
- `backend/app/services/usable_time.py` + focus window detection

## Important Decisions to Preserve
- Firebase added via Xcode UI (File > Add Package Dependencies), NOT in pbxproj — `#if canImport` guards ensure CLI builds work
- `google-services.json` and `GoogleService-Info.plist` are placeholders — real files needed from Firebase Console before auth works at runtime
- Native iOS (Swift/SwiftUI) + native Android (Kotlin/Compose)
- FastAPI + PostgreSQL + Firebase Auth + Redis/Celery + LLM abstraction
- Bottom tabs: Now, Today, Capture, Insights, Settings
- Calendar writes require approval; Replans require approval
- 14-day trial requires payment info; Free Basic Mode after trial expiry

## Known Problems
- `python-dotenv` cannot parse multi-line `.env` values → non-blocking (warnings only)
- Firebase SPM cannot be resolved via CLI — needs Xcode UI

## Warnings for Next Session
- Read this file + phase_status.md before doing anything.
- The `.env` file is gitignored and contains real secrets — never commit it.
- Jira key mapping above is required — implementation seq numbers ≠ Jira ticket numbers.
