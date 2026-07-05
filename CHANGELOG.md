# Changelog

All notable changes to TimeSense are documented here.

Format: `[DATE] TIME-### Short description`

---

## Unreleased

### Phase 11 — Insights and Learning Summary

- [2026-07-05] TIME-047: Learned assumptions settings — real "Learned Assumptions" screen on iOS and Android (Settings > Preferences), view/edit the 6 RoutineAssumption blocks via the existing GET/PATCH /api/v1/routines endpoints, no backend changes
- [2026-07-05] TIME-046: Weekly insights generation — weekly_insights table + InsightsService aggregating task/meal/sleep/commute/feedback signals over a completed week into an LLM-summarized (fallback-templated) report; GET /api/v1/insights/weekly + /history (Premium-gated); real iOS and Android Insights screens

### Phase 10 — Notifications, Widgets, Ambient Surfaces

- [2026-07-05] TIME-045: Android widgets — Glance AppWidgets for Usable Time and Next Event, each reading its own ViewModel-written Preferences state (no shared cross-widget state needed)
- [2026-07-05] TIME-044: iOS widgets — WidgetKit extension with Usable Time, Next Up, and Do Next home-screen widgets, backed by an App-Group-shared snapshot the host app writes (no independent network/auth in the extension)
- [2026-07-05] TIME-043: Notification modes and learning prompts — notification_mode (gentle/balanced/active_coach) now drives morning check-in/evening check-out/learning-prompt behavior via NotificationService + a Celery beat schedule

### Phase 9 — Routines, Meals, Commute, Sleep/Wake

- [2026-07-05] TIME-042: Sleep/wake signal integration — POST /api/v1/sleep/events (health-data-consent gated), GET /api/v1/sleep/today; late wake (>=45min past the assumed sleep-routine wake time) proposes a morning replan via the existing approval flow
- [2026-07-05] TIME-041: Commute detection — POST /api/v1/commute/detect (location-consent gated), confirm/reject flow
- [2026-07-05] TIME-040: Meal tracking — POST /api/v1/meals, GET /api/v1/meals/today (skip inference), skipped_meals in recommendations
- [2026-07-05] TIME-039: Routine assumptions — GET/PATCH /api/v1/routines with default-seeded sleep/meal/hygiene blocks per user

### Phase 8 — Recommendation Engine V1

- [2026-07-04] TIME-038: Feedback collection — POST /api/v1/recommendations/feedback (done/snooze/not_now); recommendations exclude snoozed/recently-dismissed tasks
- [2026-07-04] Fix: merge 4 divergent Alembic migration heads accumulated across TIME-030/033/036 into a single head

### Phase 0 — Repository Bootstrap

- [2026-07-03] TIME-001: Initialize repository structure, project memory, docs, skills, and workflow files
