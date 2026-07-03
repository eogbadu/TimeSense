# Phase Status

## Current Phase
Phase 3: Cross-Platform Subscription Entitlements (TIME-011 next)

## Completed Phases
- Phase 0: 2026-07-03 — Bootstrap files, docs, skills, memory, workflow docs. TIME-001 done.
- Phase 1: 2026-07-03 — Backend foundation. FastAPI, PostgreSQL, Redis/Celery, Firebase Auth, migrations. TIME-002–TIME-006 done.
- Phase 2: 2026-07-03 — Core data model and auth. User/Profile/Preferences, onboarding state, assistant personality, consent records, admin role enforcement. TIME-007–TIME-010 done.

## Phase 2 Acceptance Criteria
- [x] Authenticated user can be created/resolved (get_or_create_user)
- [x] User preferences can be saved and read
- [x] Consent records can be created and read (append-only audit trail)
- [x] Assistant personality can be saved
- [x] Admin-only route protection works (403 for non-admins, 401 for unauthenticated)
- [x] Tests cover core auth and data model behavior (35 tests passing)

## Phase 3 Acceptance Criteria (upcoming)
- [ ] User can start 14-day Premium trial
- [ ] Stripe customer created for web subscriptions
- [ ] Subscription status updates from Stripe webhooks
- [ ] Apple/Google subscription notification handler stubs exist
- [ ] Expired/canceled users move to Free Basic Mode
- [ ] Premium gates work (feature flag check)
- [ ] Referral reward logic implemented or stubbed with tests
- [ ] Admin can view subscription/trial status

## Active Jira Tickets
- Merging: TIME-007 (PR #6), TIME-008 (PR #7), TIME-009 (PR #8), TIME-010 (PR #9)
- Next: TIME-011 (Stripe Trial Foundation)

## Blockers
- None

## Next Phase
Phase 4: Mobile App Shells (iOS SwiftUI + Android Compose) — after Phase 3
