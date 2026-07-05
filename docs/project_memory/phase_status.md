# Phase Status

## Current Phase
Phase 9: Routines, Meals, Commute, Sleep/Wake (TIME-039, TIME-040, TIME-041 done; TIME-042 next)

## Staleness Warning (2026-07-04)
This file's "Completed Phases" and per-phase acceptance-criteria checkboxes were not kept
current between TIME-011 and TIME-037 — `context_summary.md` asserts Phases 3–5 (and parts
of 6/7) are done (backed by passing test_subscriptions.py, test_referrals.py, test_tasks.py,
test_timeline.py, test_now.py, test_recommendations.py), but the checkboxes below were never
ticked off session-to-session. Phase 8 below has been verified and reconciled as part of
TIME-038. Phases 3–7 checkboxes still need a reconciliation pass against actual code/tests
before being trusted — do not assume unchecked = not built.

## Completed Phases
- Phase 0: 2026-07-03 — Bootstrap files, docs, skills, memory, workflow docs. TIME-001 done.
- Phase 1: 2026-07-03 — Backend foundation. FastAPI, PostgreSQL, Redis/Celery, Firebase Auth, migrations. TIME-002–TIME-006 done.
- Phase 2: 2026-07-03 — Core data model and auth. User/Profile/Preferences, onboarding state, assistant personality, consent records, admin role enforcement. TIME-007–TIME-010 done.
- Phase 8: 2026-07-04 — Recommendation Engine V1. Usable time calculator, task scorer, GET /api/v1/recommendations (best + alternatives + LLM why), LLM Gateway, feedback collection (done/snooze/not_now) with suppression integrated into the recommendation flow. TIME-034–TIME-038 done (PRs #26–#28, TIME-038 in this session).

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

## Phase 8 Acceptance Criteria
- [x] GET /api/v1/recommendations returns best task with why string
- [x] Returns up to 2 alternatives
- [x] why falls back gracefully when LLM unavailable
- [x] GET /api/v1/now best_task uses TaskScorer ranking
- [x] POST /api/v1/recommendations/feedback records done/snooze/not_now
- [x] signal=done marks the task done
- [x] Snoozed/not_now tasks excluded from recommendations until snooze_until passes / cooldown expires
- [x] All tests pass (152 total in full suite)

## Phase 9 Progress
- [x] TIME-039 (Jira TIME-38): Routine Assumptions Model — routine_assumptions table, GET/PATCH
      /api/v1/routines, default seeding. NOT yet integrated into UsableTimeService (see known_issues.md).
- [x] TIME-040 (Jira TIME-39): Meal Tracking (Lightweight) — meal_events table, POST /api/v1/meals,
      GET /api/v1/meals/today (skip inference via TIME-039 routine windows), skipped_meals surfaced
      in GET /api/v1/recommendations as context only.
- [x] TIME-041 (Jira TIME-40): Commute Detection — commute_events table, POST /api/v1/commute/detect
      (gated on location_tracking consent) + confirm/reject flow, reusing existing consent/notification
      infrastructure. No calendar-event-location correlation yet (no such table exists).
- [ ] TIME-042: Sleep/Wake Signal Integration

## Active Jira Tickets
- TIME-40 (impl TIME-041, Commute Detection) — Done
- Next: TIME-042 (Sleep/Wake Signal Integration)

## Blockers
- None

## Next Phase
Phase 10: Notifications, Widgets, Ambient Surfaces — after Phase 9 completes
