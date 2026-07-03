# Context Summary

**Last updated:** 2026-07-03

## Current Build State

Phase 0 (Bootstrap) and Phase 1 (Backend Foundation) are fully merged to main.
Phase 2 (Core Data Model and Auth) is complete — 4 PRs open awaiting squash merge (#6–#9).
All 10 Jira tickets (TIME-7 through TIME-16) are marked Done.
35 backend tests passing, lint clean.

Backend API endpoints implemented:
- `GET /api/v1/health`
- `GET /api/v1/auth/me`
- `GET /api/v1/users/me`, `PATCH /api/v1/users/me/profile`, `PATCH /api/v1/users/me/preferences`
- `GET /api/v1/onboarding/personality`, `PUT /api/v1/onboarding/personality`
- `GET /api/v1/onboarding/state`, `POST /api/v1/onboarding/state/advance`, `PATCH /api/v1/onboarding/state/path`, `POST /api/v1/onboarding/state/complete`
- `GET /api/v1/consent/`, `POST /api/v1/consent/`, `DELETE /api/v1/consent/audio`
- `GET /api/v1/admin/health`, `GET /api/v1/admin/users`

Database tables (via Alembic migrations):
- users, user_profiles, user_preferences
- assistant_personalities, onboarding_states
- consent_records

## Last Completed Work
- TIME-007: User + Profile + Preferences models, repository, service, API
- TIME-008: AssistantPersonality + OnboardingState models, repositories, API
- TIME-009: ConsentRecord model (append-only audit trail), repository, API
- TIME-010: Admin-only routes with AdminUser dependency enforcement
- Jira transition script added — moves tickets via REST API

## Current Active Task
Merging Phase 2 PRs into main (#6 TIME-007, #7 TIME-008, #8 TIME-009, #9 TIME-010)
then starting Phase 3: Subscription Entitlements

## Next Recommended Task
1. Merge PRs #6-#9 (squash merge each, rebase next branch onto main between merges)
2. Start TIME-011: Stripe Customer + Trial Foundation (Phase 3 kickoff)

## Important Decisions to Preserve
- Product name: TimeSense
- Tagline: "Don't make managing your day another job."
- Native iOS (Swift/SwiftUI) + native Android (Kotlin/Compose)
- Web companion only (not primary product)
- FastAPI + PostgreSQL + Firebase Auth + Redis/Celery + LLM abstraction
- Stripe (web) + StoreKit (iOS) + Google Play Billing (Android) → unified backend entitlement
- Bottom tabs: Now, Today, Capture, Insights, Settings
- No Projects at launch
- No file upload at launch
- Calendar writes require approval
- Replans require approval
- 14-day trial requires payment info
- $14.99/month · $99/year · $79/year founder plan
- Free Basic Mode after trial expiry

## Known Problems
- Stacked branches (TIME-007 through TIME-010): each is based on the previous.
  After squash-merging PR #6 into main, rebase branches #7-#9 onto main before merging.
  Same rebase pattern as Phase 1 resolution.

## Warnings for Next Session
- Read this file + phase_status.md before doing anything.
- Do not start Phase 3 until Phase 2 PRs are merged.
- Always rebase stacked branches onto main after each squash merge.
- The `.env` file is gitignored and contains real secrets — never commit it.
