# Changelog

All notable changes to TimeSense are documented here.

Format: `[DATE] TIME-### Short description`

---

## Unreleased

### Phase 9 — Routines, Meals, Commute, Sleep/Wake

- [2026-07-05] TIME-041: Commute detection — POST /api/v1/commute/detect (location-consent gated), confirm/reject flow
- [2026-07-05] TIME-040: Meal tracking — POST /api/v1/meals, GET /api/v1/meals/today (skip inference), skipped_meals in recommendations
- [2026-07-05] TIME-039: Routine assumptions — GET/PATCH /api/v1/routines with default-seeded sleep/meal/hygiene blocks per user

### Phase 8 — Recommendation Engine V1

- [2026-07-04] TIME-038: Feedback collection — POST /api/v1/recommendations/feedback (done/snooze/not_now); recommendations exclude snoozed/recently-dismissed tasks
- [2026-07-04] Fix: merge 4 divergent Alembic migration heads accumulated across TIME-030/033/036 into a single head

### Phase 0 — Repository Bootstrap

- [2026-07-03] TIME-001: Initialize repository structure, project memory, docs, skills, and workflow files
