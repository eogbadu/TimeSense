# Implementation Log

## 2026-07-05 — TIME-044 (Jira TIME-43): iOS Widgets

### Created
- New `TimeSenseWidgetExtension` target (WidgetKit app-extension, iOS 17.0, embedded in the
  TimeSense host app) — added programmatically via the `xcodeproj` Ruby gem (installed this
  session with `gem install xcodeproj --user-install`) rather than hand-editing project.pbxproj,
  since a new native target touches build phases, embed/copy-files phases, and a target
  dependency that are error-prone to write by hand
- `ios/TimeSense/Core/Widgets/WidgetSnapshot.swift` — Codable snapshot (usableMinutes, bestTask,
  nextEvent, updatedAt), persisted as JSON in a shared App Group UserDefaults suite
  (`group.com.timesense.app`); compiled into both the app and extension targets
- `ios/TimeSenseWidget/TimeSenseWidgetBundle.swift`, `SnapshotProvider.swift`,
  `UsableTimeWidget.swift`, `NextEventWidget.swift`, `BestNextActionWidget.swift` — the extension's
  own sources; all three widgets share one `TimelineProvider` that only reads the snapshot
- `ios/TimeSenseWidget/Info.plist` — physical plist (GENERATE_INFOPLIST_FILE=NO), matching Apple's
  own widget-extension template keys (CFBundleIdentifier/Executable/Name via build-setting
  substitution, NSExtension/NSExtensionPointIdentifier = com.apple.widgetkit-extension)
- `ios/TimeSense/TimeSense.entitlements`, `ios/TimeSenseWidget/TimeSenseWidget.entitlements` — App
  Group entitlement, wired via CODE_SIGN_ENTITLEMENTS on both targets

### Modified
- `ios/TimeSense/Features/Now/NowViewModel.swift` — after a successful `/now` fetch, updates
  usableMinutes/bestTask on the shared snapshot (preserving nextEvent) and calls
  `WidgetCenter.shared.reloadAllTimelines()`
- `ios/TimeSense/Features/Today/TodayViewModel.swift` — after a successful `/timeline/today`
  fetch, derives the next non-done, not-yet-ended event and updates nextEvent on the shared
  snapshot (preserving usableMinutes/bestTask), then reloads timelines
- `ios/TimeSense.xcodeproj/project.pbxproj` — new target, entitlements wiring, embed phase

### Design notes
- The widget extension has zero network/auth code — it only ever reads the App-Group-shared
  snapshot the host app writes after its own authenticated fetches. This avoids duplicating
  Firebase's in-memory-only ID token (APIClient.swift never persists it to Keychain) into a
  second process, which would have required a new Keychain-sharing mechanism.
- Widgets use DesignTokens.Typography/Spacing (pure value constants, safe to share) but not
  DesignTokens.Color, since those are named-asset-catalog colors and no Assets.xcassets exists
  in this project yet for even the host app — widgets use system semantic colors instead.
- Timeline refresh policy re-requests at the earlier of 30 minutes or the next event's start time,
  using the last-known snapshot in between — no push-triggered instant refresh in this ticket.
- Environment note: this sandbox's Xcode install has no Simulator runtimes downloaded
  (`xcrun simctl list runtimes` is empty), so scheme-based `xcodebuild build -scheme TimeSense`
  fails with "Found no destinations" regardless of this ticket's changes. Verified instead with
  `xcodebuild build -target TimeSense -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO` (and the same
  for `-target TimeSenseWidgetExtension`), which compiles/links without needing a destination.
  Both targets build cleanly with zero new warnings (one pre-existing, unrelated warning in
  CaptureViewModel.swift). A real device/App Store build still needs a real Apple Developer Team
  (open_questions.md) for the App Group entitlement to take effect.

## 2026-07-05 — TIME-043 (Jira TIME-42): Notification Modes and Learning Prompts

### Created
- `backend/app/models/notification_event.py` — NotificationEvent model (event_type
  morning_checkin/evening_checkout/learning_prompt, notification_id FK) — audit trail + dedup
- `backend/migrations/versions/l2m3n4o5p6q7_add_notification_events.py` — notification_events table
- `backend/app/workers/notification_tasks.py` — three thin Celery tasks (send_morning_checkins,
  send_evening_checkouts, send_learning_prompts) wrapping the NotificationService methods via
  asyncio.run() + AsyncSessionLocal; not covered by tests (no Redis/Docker in this environment,
  same precedent as the pre-existing app.workers.health_task)
- `backend/tests/test_notification_orchestration.py` — 9 tests, service-layer against db_session
  (matching test_notifications.py's existing pattern for non-HTTP-triggered flows)

### Modified
- `backend/app/repositories/notification_repository.py` — added NotificationEventRepository
  (record/has_sent_today)
- `backend/app/repositories/user_repository.py` — added list_active_ids() for the worker loop
- `backend/app/services/notification_service.py` — added maybe_send_morning_checkin(),
  maybe_send_evening_checkout(), maybe_send_learning_prompt(), maybe_send_routine_learning_prompt()
- `backend/app/workers/celery_app.py` — registered notification_tasks module + a UTC beat_schedule
  (8am/10am/9pm) for the three tasks
- `backend/app/models/__init__.py` — registered NotificationEvent

### Design notes
- `notification_mode` (gentle|balanced|active_coach) already existed on UserPreferences from an
  earlier ticket but had no behavior attached to it anywhere — this ticket is purely about giving
  it real effect, not adding new preference storage/API.
- Mode mapping: gentle -> evening check-out only (lightest touch); balanced -> both check-ins, no
  learning prompts; active_coach -> both check-ins + learning prompts. This maps directly onto the
  product brief's "Active Coach / Learning Mode" framing rather than inventing an unrelated concept.
- The learning prompt is concrete, not a stub: it checks the user's "sleep" RoutineAssumption
  (TIME-039) and, if still `is_customized = False` and the account is within a 14-day placeholder
  Learning Mode window (reusing the existing 14-day trial length rather than a new arbitrary
  number), asks the user to confirm/adjust the assumed sleep block.
- The 14-day window is explicitly a placeholder — decision_log.md already has an unimplemented
  decision that the learning period should end "based on enough data, not fixed days"; this ticket
  doesn't attempt that, to avoid inventing a second, conflicting partial implementation.
- Dedup (once per event_type per user per UTC day) follows the same created-at-date-check pattern
  already used by SleepWakeEvent/CommuteEvent, rather than a new mechanism.
- Celery beat schedule times (8am/10am/9pm) are UTC, not per-user-local — same known UTC-only
  simplification as RoutineAssumption/CommuteService/MorningReplanService (known_issues.md).

## 2026-07-05 — TIME-042 (Jira TIME-41): Sleep/Wake Signal Integration

### Created
- `backend/app/models/sleep_wake.py` — SleepWakeEvent model (wake_time, sleep_start, source
  healthkit/manual, replan_request_id FK)
- `backend/migrations/versions/k1l2m3n4o5p6_add_sleep_wake_events.py` — sleep_wake_events table
- `backend/app/repositories/sleep_wake_repository.py` — create/get_latest_today/has_replan_on_date/
  set_replan_request
- `backend/app/schemas/sleep_wake.py` — SleepWakeEventIn, SleepWakeEventResponse
- `backend/app/services/morning_replan.py` — MorningReplanService.record_wake_event() gates on
  health_data consent, compares wake_time minute-of-day against the user's "sleep" RoutineAssumption
  end_minute (TIME-039), and calls the existing NotificationService.propose_replan() when the wake
  is >= 45 minutes late, linking the resulting ReplanRequest back onto the event to dedupe same-day
- `backend/app/api/v1/sleep.py` — POST /sleep/events, GET /sleep/today
- `backend/tests/test_sleep_wake.py` — 8 tests

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered sleep router/model

### Design notes
- No new replan mechanism: reuses `NotificationService.propose_replan`/`ReplanRequest` (TIME-015)
  exactly as-is, including the existing `/api/v1/notifications/replans/{id}/approve|reject` routes —
  a sleep-triggered replan looks identical to any other replan to the approval flow.
- Consent-gated on the existing `health_data` consent type (already defined in
  `ConsentRepository.VALID_CONSENT_TYPES`, unused until now) — same 403-without-consent pattern as
  TIME-041's `location_tracking` gate.
- Wake-time-vs-assumption comparison uses the same UTC-minute-of-day simplification already used by
  RoutineAssumption/UsableTimeService/CommuteService (see known_issues.md) rather than inventing a
  fourth partial timezone approach.
- iOS HealthKit read integration is explicitly out of scope for this ticket (backend contract only),
  same backend/mobile split TIME-041 used for its location-permission piece — flagged as its own
  decision point per context_summary.md's note on this being the first backend/mobile-split ticket.
- Found the Jira ticket key (TIME-41) already existed with a stale "In Review" status before any
  code for this ticket existed in this session — likely an abandoned artifact from an earlier
  attempt. Overwrote its description via `create_jira_tickets.py` and moved it back to
  "In Progress" before starting; no code from that prior attempt was present in the repo.

## 2026-07-05 — TIME-041 (Jira TIME-40): Commute Detection

### Created
- `backend/app/models/commute.py` — CommuteEvent model (direction, detected_start/end,
  estimated_minutes, status pending/confirmed/rejected, notification_id FK)
- `backend/migrations/versions/j0k1l2m3n4o5_add_commute_events.py` — commute_events table
- `backend/app/repositories/commute_repository.py` — create/get/list_pending/set_status
- `backend/app/schemas/commute.py` — LocationPingIn, CommuteDetectRequest, CommuteEventResponse
- `backend/app/services/commute_service.py` — haversine-based detect_from_pings() heuristic
  (>500m displacement, 5–120 min elapsed, direction from first ping's UTC hour); propose_commute()
  gates on location_tracking consent (existing ConsentRepository) and creates an approval_needed
  Notification alongside the pending CommuteEvent, mirroring NotificationService.propose_replan
- `backend/app/api/v1/commutes.py` — POST /commute/detect, GET /commute/pending,
  POST /commute/{id}/confirm, POST /commute/{id}/reject
- `backend/tests/test_commutes.py` — 11 tests

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered commutes router/model

### Design notes
- Reused existing infrastructure instead of inventing new mechanisms: `consent_records`
  (`location_tracking` type already existed in `ConsentRepository`'s valid types) for the
  permission gate, and the `Notification`/approval pattern from `ReplanRequest` for the
  confirmation prompt.
- Raw lat/lng points are never persisted — only the derived CommuteEvent window is stored.
- Direction inference (`hour < 14 UTC → to_work`) is a deliberate simplification consistent with
  UsableTimeService/RoutineAssumption's existing UTC-only approach — not a new gap.
- No calendar-event-location correlation: no `CalendarEvent` table with location data exists in
  this codebase yet, so "calendar patterns" from the ticket's goal is deferred to a future ticket.

### Verification
- `pytest tests/test_commutes.py -v` — 11 passed
- Full suite: `pytest` — 181 passed, 2 known-flaky Stripe-network failures in test_referrals.py
  (see known_issues.md — reproduces identically on `main`, unrelated to this change)
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline

## 2026-07-05 — TIME-040 (Jira TIME-39): Meal Tracking (Lightweight)

### Created
- `backend/app/models/meal.py` — MealEvent model, MEAL_TYPES, MEAL_STATUSES
- `backend/migrations/versions/i9j0k1l2m3n4_add_meal_events.py` — meal_events table
- `backend/app/repositories/meal_repository.py` — log(), get_today_status() (explicit log wins;
  else infers skipped/pending from the matching RoutineAssumption window from TIME-039)
- `backend/app/schemas/meal.py` — MealLogRequest, MealEventResponse, MealTodayResponse
- `backend/app/api/v1/meals.py` — POST /meals, GET /meals/today
- `backend/tests/test_meals.py` — 9 tests (API + direct repository skip/pending inference)

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered meals router/model
- `backend/app/api/v1/recommendations.py` — RecommendationResponse gained `skipped_meals: list[str]`,
  sourced from MealRepository, context only (does not change TaskScorer/ranking)
- `backend/tests/test_recommendations.py` — 3 tests for the new field

### Design notes
- Skip inference reuses the UTC-minute-of-day RoutineAssumption windows directly — same
  UTC-only simplification `UsableTimeService` already relies on, not blocked on the
  timezone-awareness follow-up tracked in known_issues.md.
- Discovered `test_referrals.py` has 2 tests that intermittently fail on real Stripe network
  calls in this sandbox (unrelated to this ticket) — documented in known_issues.md, not fixed here.

### Verification
- `pytest tests/test_meals.py tests/test_recommendations.py -v` — 20 passed
- Full suite: `pytest` — 172 passed (after a rerun past the flaky Stripe network tests above)
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline

## 2026-07-05 — TIME-039 (Jira TIME-38): Routine Assumptions Model

### Created
- `backend/app/models/routine.py` — RoutineAssumption model, ROUTINE_TYPES, DEFAULT_ROUTINES (sleep/breakfast/lunch/dinner/morning_hygiene/evening_hygiene, minutes-since-local-midnight)
- `backend/migrations/versions/h8i9j0k1l2m3_add_routine_assumptions.py` — routine_assumptions table
- `backend/app/repositories/routine_repository.py` — get_or_seed_defaults(), update_one()
- `backend/app/schemas/routine.py` — RoutineAssumptionResponse, RoutineAssumptionUpdate
- `backend/app/api/v1/routines.py` — GET /routines (seeds defaults), PATCH /routines/{routine_type}
- `backend/tests/test_routines.py` — 9 tests

### Modified
- `backend/app/api/v1/__init__.py` — registered routines_router
- `backend/app/models/__init__.py` — registered RoutineAssumption

### Design notes
- Deliberately does NOT wire routine blocks into `UsableTimeService` yet — see known_issues.md
  "RoutineAssumption data (TIME-039) is not yet subtracted from usable time". `UsableTimeService`
  has no timezone awareness today; doing that properly once for routines+meals+commute together
  (after TIME-040–042) avoids three partial integrations.
- `end_minute < start_minute` signals a block that wraps past midnight (sleep 23:00→07:00).
- Editing a routine sets `is_customized=True` so future auto-detection tickets (commute/sleep) know
  not to silently overwrite a user's explicit choice.

### Verification
- `pytest tests/test_routines.py -v` — 9 passed
- Full suite: `pytest` — 161 passed
- `alembic heads` — single head; `alembic upgrade head --sql` — compiles cleanly offline (no live
  Postgres available in this environment)

## 2026-07-04 — TIME-038 (Jira TIME-37): Feedback Collection

### Created
- `backend/app/models/recommendation_feedback.py` — RecommendationFeedback model (user_id, task_id, signal, snooze_until)
- `backend/migrations/versions/g7h8i9j0k1l2_add_recommendation_feedback.py` — recommendation_feedback table
- `backend/app/repositories/recommendation_feedback_repository.py` — RecommendationFeedbackRepository.get_suppressed_task_ids()
- `backend/tests/test_feedback.py` — 7 tests for POST /recommendations/feedback
- `backend/migrations/versions/e55970716568_merge_parallel_migration_heads.py` — merges 4 divergent Alembic heads (pre-existing issue, see Known Issues)

### Modified
- `backend/app/api/v1/recommendations.py` — added `POST /recommendations/feedback` (done/snooze/not_now); `GET /recommendations` now filters out tasks suppressed by active snooze or a recent not_now
- `backend/app/models/__init__.py` — registered RecommendationFeedback so Alembic autogenerate detects it
- `backend/tests/test_recommendations.py` — 3 new tests for suppression behavior (not_now, active snooze, expired snooze)

### Design notes
- `not_now` suppresses a task from recommendations for a 4-hour cooldown (`NOT_NOW_COOLDOWN`), not permanently — avoids "nagging" per the recommendation-engine skill while still letting a still-pending task resurface later.
- `snooze` suppresses until `snooze_until` passes.
- Only the *latest* feedback per task is considered — an expired snooze or superseded not_now does not keep suppressing.
- `signal=done` also flips the task to `status=done` via `TaskRepository.update`.

### Verification
- `pytest tests/test_feedback.py tests/test_recommendations.py -v` — 16 passed
- Full suite: `pytest` — 152 passed
- `alembic upgrade head --sql` (offline mode) — compiles cleanly, single resolved head. No live Postgres available in this environment to run a real `alembic upgrade head`; needs verification against a real DB before deploy.

## 2026-07-03 — TIME-001: Repository Bootstrap

### Created
- `/README.md` — full project overview, stack, setup instructions
- `/AGENTS.md` — agent rules, subagents, skills, code generation constraints
- `/CHANGELOG.md` — initialized
- `/docs/product/product_brief.md` — product vision, rules, non-negotiables
- `/docs/architecture/architecture_overview.md` — system architecture, backend/mobile/web structure, integration patterns, data flow
- `/docs/project_memory/context_summary.md` — current state and next steps
- `/docs/project_memory/phase_status.md` — phase tracking
- `/docs/project_memory/decision_log.md` — all settled product and technical decisions

### In Progress
- Remaining project memory files
- Workflow docs
- Ticket sequence
- Skills
- PR template
- Operational CLAUDE.md
