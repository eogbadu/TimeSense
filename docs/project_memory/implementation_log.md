# Implementation Log

## 2026-07-08 — TIME-146 (Jira TIME-146): Fix voice capture (continuous dictation + live waveform)

User: no waveform animation while speaking; pausing then continuing wiped the text. Root cause: SFSpeechRecognizer sends isFinal after a pause; the old code called cleanup() on isFinal -> recording stopped (waveform view disappeared -> 'no animation') and the next tap started a fresh session with transcript='' (wipe). Rewrote VoiceCaptureService for CONTINUOUS dictation: startAudio() installs the tap + runs the engine for the whole session (separate from recognition); startRecognition() creates a request/task; on isFinal (or a segment-end error) we commit the segment to `committed` and restartRecognition() seamlessly (engine/tap keep running); published transcript = join(committed, currentPartial) so pausing never clears. stop() sets isRecording=false + teardown(). RMS scaling 12->18. WaveformView.barHeight now = idle shimmer (0.16*jitter) + level*(0.45+0.55*jitter) so it always animates while recording and reacts strongly to volume. iOS BUILD SUCCEEDED.
## 2026-07-08 — TIME-145 (Jira TIME-145): Audio-reactive waveform while listening

VoiceCaptureService: @Published level: CGFloat (0..1) computed from each audio-tap buffer via rmsLevel (RMS of float channel * 12, clamped); dispatched to @MainActor; reset to 0 on stop()/cleanup(). CaptureView: WaveformView (private) — 7 Capsule bars whose heights = maxHeight * min(1, idle 0.12 + level * jitter[i]); a 0.11s Timer re-rolls per-bar jitter (0.35..1.0) for liveliness; easeInOut animations on level + jitter. heroIcon shows WaveformView(level: voice.level, .white) while recording (with a stronger shadow), the static waveform icon otherwise, cross-faded. iOS BUILD SUCCEEDED.
## 2026-07-08 — TIME-144 (Jira TIME-144): Voice capture (on-device speech-to-text)

VoiceCaptureService (@MainActor): SFSpeechRecognizer(locale current) + AVAudioEngine; requestPermissions (SFSpeechRecognizer.requestAuthorization + AVAudioApplication.requestRecordPermission iOS17 / AVAudioSession fallback); beginRecording sets AVAudioSession .record/.measurement, installs an input tap feeding SFSpeechAudioBufferRecognitionRequest (shouldReportPartialResults; requiresOnDeviceRecognition when supportsOnDeviceRecognition -> keeps audio on device); recognitionTask -> @Published transcript (partial + final); stop()/cleanup tear down. No raw audio persisted/uploaded. CaptureView: @StateObject voice; mic button toggles record (mic.fill <-> stop.circle.fill, red + .pulse); .onChange(voice.transcript) fills captureText while recording; error alert bound to voice.errorMessage. Replaced the coming-soon stub. Info.plist: NSMicrophoneUsageDescription + NSSpeechRecognitionUsageDescription. Registered VoiceCaptureService.swift. Transcript flows into the normal POST /capture parse (no backend change). iOS BUILD SUCCEEDED. Honors the raw-audio-opt-in product rule (on-device, text-only).
## 2026-07-08 — TIME-143 (Jira TIME-143): Surface upcoming appointments; no errands right before one

User report: at 1:53pm the top pick was 'Go to the gym early in the morning' (scheduled 8am) while a 2:40pm Ekele Acupuncture appointment (45 min out) sat on the calendar. Diagnosis: (a) calendar candidates only fired mins<=15, so a 45-min appointment generated NO candidate (engine knew next_event/free_block but never surfaced it as an action); (b) with GOOGLE_MAPS_API_KEY set, the gym resolved a nearby gym, DRIVING_TIME_CALCULATED + TRIP_FITS_FREE_BLOCK -> location_fit 0.9 -> score 62, winning. Fix: calendar_candidates widened — join(<=2), prep-or-leave(<=20 / located<=30), and a 'Coming up'/'Head out soon' candidate up to 60min(located)/75min with urgency=max(0.6,1-mins/90); importance 0.85, context 0.9, time 1.0. penalties: location errand + next_event<=60min -> +40 (don't start a trip right before a commitment). Verified on the user's data: top pick now 'Coming up: Ekele Acupuncture' (67.5); gym dropped out of top 6; best_task becomes a real task. New test (appointment ~45min surfaces as calendar domain). Suite 414. KNOWN GAP: the engine's TaskItem has no scheduled_start, so the gym's 8am slot is invisible — a future ticket should give the engine scheduled-time awareness.
## 2026-07-08 — TIME-141 (Jira TIME-141): Why-page Calendar signal shows real free time

User: the Calendar signal in /now/why almost always said '240 minutes free before the end of your day' — looked hard-coded. Root cause: build_explanation used UsableTimeService.calculate (MAX_WINDOW_MINUTES=240 cap; measured to LOCAL midnight; considered scheduled TASKS only, ignoring calendar events). Fix: new _free_and_next(db,user,today_tasks,now,tz) computes free time until the next commitment (scheduled task OR timed calendar event) or the end of the WORKING day (SchedulingService window_end), with busy = scheduled tasks + timed calendar events, via SchedulingService.free_minutes_before (working-hours + tz aware). next_event now includes calendar events. Replaced UsableTimeService import/usage; phrasing 'before your workday ends'. compute_confidence now uses the real free time. Verified: a meeting in 45 min -> 'You have a 45-minute free block before Design review at 2:29 PM'. New API test (Why Calendar signal names the meeting, not 240). Suite 413. (Location + time-of-day signals were already genuinely derived.)
## 2026-07-08 — TIME-140 (Jira TIME-140): Capture parses specific times into scheduled_start

Root cause of captured tasks losing their time: both the LLM prompt and rule-based parser only produced due_at, so 'today at 5pm' never became a scheduled slot (and the LLM was inconsistent). Fix: capture_date_parser.parse_datetime now returns (scheduled_start, due_at, title) — a specific clock time -> scheduled_start on the given/today date; a date without a time -> due_at at end of day. capture_service: added scheduled_start to the LLM JSON schema/rules (time -> scheduled_start, date -> due_at, prefer scheduled_start); the deterministic parser ALWAYS runs and fills any field the LLM leaves null (LLM wins when present); scheduled_end = start + (estimated||30). Verified end-to-end: 'Go to Walmart today at 5pm' -> scheduled 21:00Z (5pm EDT) + 30-min block; 'Buy new pants today' -> due today 23:59; 'Buy milk' -> neither. Updated parser tests to the 3-tuple. Suite 412. Completes the deep-linking + timezone + capture batch.
## 2026-07-08 — TIME-139 (Jira TIME-139): App sends the device timezone

Root fix for the profile-timezone='UTC' issue (deeper cause of the TIME-125 Today bug + wrong greetings). MainTabView.task -> syncDeviceTimezone(): PATCH /api/v1/users/me/profile {timezone: TimeZone.current.identifier} on launch (endpoint + UserProfileUpdate already support timezone). Now greetings (_greeting), 'today' boundaries, working-hours windows, and scheduling all use the real local tz. Timeline ±1-day tolerance (TIME-125) kept as a safety net. iOS BUILD SUCCEEDED.
## 2026-07-08 — TIME-138 (Jira TIME-138): Notification-tap deep-linking

Backend: PushSender.send gains data: dict; ApnsPushSender merges it into the APNs payload alongside aps (so custom keys ride along). push_for_user sends data={type:recommendation, task_id?}; offer_time_block sends data={type:offer_time_block, task_id, task_title}. iOS: DeepLinkRouter.shared (@Published route: DeepRoute?{now, scheduleTask(taskId,title)}); AppDelegate.userNotificationCenter(didReceive:) reads userInfo type/task_id/task_title on tap -> sets route (offer_time_block -> scheduleTask, else now). MainTabView observes router -> switches tab (Today for scheduleTask, Now for now; clears .now). TodayView .onChange(router.route): on .scheduleTask -> clear route, ensureWriteAccess, suggestedSlot, present pre-filled EKEventEditViewController. Updated test stub sender to accept data. iOS BUILD SUCCEEDED; suite 411.
## 2026-07-08 — TIME-137 (Jira TIME-137): Proactive 'block time for high-priority task' offer

ProactivePushService.offer_time_block_for_user(user, sender, now, respect_cooldown=True): tokens required; shared 45-min cooldown; pick the top UNSCHEDULED pending task that's overdue or priority<=2 (sorted overdue-first then priority); find_slot_multiday over busy = other scheduled tasks + timed calendar events (OFFER_HORIZON_DAYS=3), not_before=now; push title 'Block time for “<task>”?' body 'You have a free <dur>-min slot <today|tomorrow|Weekday> at <h:mm AM>. Want to schedule it?' collapse_id=offer_time_block; record PushNotification. Celery scan_and_push: push_for_user first; elif offer_time_block_for_user -> so a time-block offer fills in when there's no eligible recommendation (both honor cooldown). POST /api/v1/devices/test-offer (respect_cooldown=False) to verify on device. 3 tests (offer for high-priority unscheduled; none when low-priority; cooldown). Suite 411.
## 2026-07-08 — TIME-136 (Jira TIME-136): Roll suggested slots to the next few days

SchedulingService: extracted _earliest_in_window(cursor,window_end,dur,busy); added find_slot_multiday(now,duration,busy,tz,not_before,max_days) looping day offsets 0..max_days-1, computing each day's working window via _window(now+offset), cursor=max(window_start,now) for today else window_start, honoring not_before, returning the first fit. /tasks/{id}/suggested-slot now uses find_slot_multiday over SLOT_SEARCH_DAYS=3, busy = all pending scheduled tasks (across days) + timed calendar events in [now,horizon]; response gains day label (today/tomorrow/later this week). iOS unchanged (decodes start/end; native editor shows the date). New test: rolls forward when today's window is past. Suite 407.
## 2026-07-08 — TIME-135 (Jira TIME-135): Engine-suggested time blocks

Backend GET /api/v1/tasks/{id}/suggested-slot: SchedulingService(work_start,work_end).find_slot(now, duration=estimated_minutes||30, busy, tz, not_before=now) where busy = today's OTHER scheduled tasks + timed synced calendar events (SimpleNamespace shim with scheduled_start/end so _busy treats events as busy). Returns SuggestedSlotOut{fits,start,end,duration_minutes,message}; None -> fits=false. iOS: TodayViewModel.suggestedSlot(taskId,estimatedMinutes) GETs it (fallback now+duration); TodayView refactored to a ScheduleDraft(id,title,start,end); the Today context-menu 'Find a time & add to calendar' -> ensureWriteAccess -> suggestedSlot -> pre-fills EKEventEditViewController via .sheet(item:); on save re-syncs. 2 backend tests (slot avoids a blocking meeting; 404). Suite 407; iOS BUILD SUCCEEDED. Ties the calendar feature together: the engine proposes a conflict-free block, the user approves.
## 2026-07-08 — TIME-134 (Jira TIME-134): Calendar write-back (add task to calendar w/ approval)

Write half of read+write. CalendarSyncService: ensureWriteAccess() (requests full access if needed), makeDraftEvent(title,start,end) -> unsaved EKEvent on defaultCalendarForNewEvents, eventStore accessor. EventEditorView (UIViewControllerRepresentable wrapping EKEventEditViewController + EKEventEditViewDelegate; EventKitUI) = Apple's native review/confirm editor — the approval step per the product rule. TodayView: @State schedulingTask; SmartPlanCard gains onSchedule + a '.contextMenu Add to Calendar' (calendar.badge.plus); tapping ensures write access then presents the editor via .sheet(item:), pre-filled from the task (scheduledStart or now, +estimatedMinutes/30 duration); on save -> syncIfAuthorized so the new event reflects back. Registered EventEditorView.swift. iOS BUILD SUCCEEDED. Completes the Apple Calendar read+write MVP (TIME-131..134).
## 2026-07-08 — TIME-133 (Jira TIME-133): Show calendar events on Today

CalendarSyncService now @Published var events: [CalEvent] (id/title/start/end/location/allDay), populated in sync() from the EKEvents (alongside the backend payload). TodayView: @ObservedObject calendar; todaysEvents = events filtered to today + not all-day, sorted by start; new read-only 'On your calendar' CalendarEventsCard (calendar glyph + title + 'start – end · location'), shown above Smart Plan when non-empty; Today .task/onChange now also calls calendar.syncIfAuthorized() so events refresh on tab appear. iOS BUILD SUCCEEDED. Write-back (add events w/ approval) = TIME-134.
## 2026-07-08 — TIME-132 (Jira TIME-132): iOS Apple Calendar (EventKit) connect + sync

CalendarSyncService (EventKit, @MainActor, shared): requestFullAccessToEvents (iOS17+) / requestAccess(.event) fallback; reads events now-12h..now+36h via predicateForEvents; maps EKEvent -> {external_id=eventIdentifier, title, starts_at/ends_at ISO8601, location, all_day}; PUT /api/v1/calendar/synced; syncIfAuthorized (launch/foreground); disconnect clears the backend copy; @Published status/lastSyncedCount. CalendarSettingsView rewired to real states (Connect Apple Calendar / connecting spinner / connected + N events + Sync now + Disconnect / denied -> Open iOS Settings) + '.task syncIfAuthorized'. Info.plist NSCalendarsFullAccessUsageDescription + NSCalendarsUsageDescription. AppDelegate re-syncs on launch. Registered CalendarSyncService.swift in the target; added UIKit import to SettingsScreens. iOS BUILD SUCCEEDED. Needs on-device test for the permission prompt. NEXT: TIME-133 show events on Today + write-back.
## 2026-07-08 — TIME-131 (Jira TIME-131): Apple Calendar backend (EventKit sync + engine wiring)

Pivoted to Apple Calendar first (native EventKit — no OAuth/Google Cloud; also sees Google cals synced into iOS Calendar). Backend half: synced_calendar_events table (user_id/source/external_id/title/starts_at/ends_at/location/all_day; unique per user+source+external_id; migration z6a7b8c9d0e1 WITH created_at/updated_at server_default per TIME-125 lesson) + SyncedCalendarEventRepository (replace_for_source, list_window). PUT /api/v1/calendar/synced (app pushes EventKit events, replace-all per source) + GET /calendar/synced/today; NOT premium-gated (device permission). context_builder now fetches synced events (now-1h..now+24h, TIMED only — all-day excluded), maps to engine CalendarEvent, feeds normalize_context -> calendar_context (current/next event, minutes-until, free block, meeting density); free block = minutes-until-next-event when an event is upcoming, else usable_minutes. So the engine fires prepare_for_meeting/join_meeting/leave_for_event. 4 tests (sync store/list; replace; imminent meeting -> prepare; all-day ignored). Suite 405. NEXT: TIME-132 iOS EventKit read/permission/sync; TIME-133 show events on Today + write-back.
## 2026-07-08 — TIME-130 (Jira TIME-130): Gate push debug logs behind #if DEBUG

Added debugLog(_ message: @autoclosure () -> String) that only prints under #if DEBUG (the autoclosure isn't evaluated in release). Replaced all AppDelegate print() calls (launch marker, register, permission result, ✅ token, ❌ fail, foreground presentation) with debugLog — so no console noise or device-token logging ships to production. The token is still PUT to the backend regardless. iOS BUILD SUCCEEDED.
## 2026-07-08 — TIME-129 (Jira TIME-129): Foreground notification presentation + PUSH VERIFIED

PUSH NOW WORKS END-TO-END ON DEVICE. After TIME-128 (Firebase proxy disabled) the token registered (device_tokens=1, PUT /devices 200); a server-side send_test via the real ApnsPushSender returned delivered=1 and APNs returned HTTP/2 200 + apns-id — confirmed on the user's phone. The FIRST push seemed to not arrive because iOS suppresses banners for foreground apps. Fix: AppDelegate conforms to UNUserNotificationCenterDelegate + set as center.delegate; willPresent returns [.banner,.sound,.badge] so pushes AND local geofence notifications show even with the app open. iOS BUILD SUCCEEDED. Full push chain: engine -> LLM text -> JWT/HTTP2 -> sandbox APNs -> device. For automatic proactive push, run celery worker+beat.
## 2026-07-08 — TIME-128 (Jira TIME-128): Disable Firebase delegate swizzling for APNs

Root cause of 'no push token' nailed via console: fresh build ran (🚀 TIME-127), registerForRemoteNotifications() called (📡), notification permission granted=true — but NEITHER didRegisterForRemoteNotificationsWithDeviceToken (✅) NOR didFailToRegister (❌) fired. Classic FirebaseAuth UIApplicationDelegate method swizzling intercepting the APNs registration callback and not chaining to our @UIApplicationDelegateAdaptor delegate. Fix: Info.plist FirebaseAppDelegateProxyEnabled=NO (we use neither FCM nor phone-auth, so safe). Verified the key merges into the built Info.plist. Now the delegate should fire ✅/❌ on device. iOS BUILD SUCCEEDED.
## 2026-07-08 — TIME-127 (Jira TIME-127): Launch/registration markers

Push still not registering on device; console showed no ✅/❌ despite HEAD at TIME-126 → likely stale binary or detached console. Added AppDelegate.didFinishLaunching prints: '🚀 build TIME-127' marker, '📡 Calling registerForRemoteNotifications()', and the notification-permission result. Pure diagnostics — if the 🚀 line doesn't appear, the installed app is stale (clean build + run from Xcode). iOS BUILD SUCCEEDED.
## 2026-07-08 — TIME-126 (Jira TIME-126): Unconditional APNs registration

Diagnosis (from DB + logs): device_tokens=0, push_notifications=0, ZERO PUT /devices requests ever — the app never registered. APNs creds valid (JWT signs), bundle id matches (com.aetheranalytics.timesense), sandbox=true. Two causes: (1) the created_at migration bug 500'd PUT /devices until TIME-125; (2) AppDelegate gated registerForRemoteNotifications() behind the notification-permission grant, so no-permission -> no token. Fix: register unconditionally on launch (token is independent of alert permission); request alert permission separately; log the token on success + a clear failure message. Remaining external requirement: Push Notifications capability must be on the provisioning profile (Xcode Signing & Capabilities / Apple App ID) or didFailToRegister fires; and Celery worker+beat must run for the auto-scan (test-push works without it). iOS BUILD SUCCEEDED.
## 2026-07-08 — TIME-125 (Jira TIME-125): On-device regression fixes

Diagnosed from the phone via run_dev logs + DB inspection. BUG 1 (root cause of 'no push' + 'location not used'): POST /location/place, PUT /devices, PUT /places all 500'd on Postgres with NotNullViolation on created_at — my hand-written migrations (v2w3x4y5z6a7, w3x4y5z6a7b8, x4y5z6a7b8c9) omitted the server_default=now() that TimestampMixin declares. SQLite create_all tests build from the models (which HAVE the default) so they passed; only Postgres (which uses the migrations) failed. Fix: migration y5z6a7b8c9d0 ALTER COLUMN ... SET DEFAULT now() on user_location_states/user_places/device_tokens/push_notifications (created_at+updated_at). Verified an upsert now succeeds. BUG 2 ('your day is open' at night): /timeline/today included untimed pending tasks only if for_date == datetime.now(UTC).date(); the client sends its LOCAL date, which lags UTC in the evening (user tz behind UTC), so the branch was skipped and only today-scheduled tasks (0) returned. Fix: include untimed when abs(for_date - utc_today) <= 1 day (client only ever requests its own current date). Verified the real user's Jul-7 request now returns their 4 untimed pending tasks. Added known-issues note on migration/model drift + a regression test (untimed tasks across the UTC boundary). Deeper: profile timezone is 'UTC' (app never sends the real tz) — follow-up. Suite 401. Backend restarted.
## 2026-07-07 — TIME-124 (Jira TIME-124): Capture keyboard dismissal bug

User report: typing on Capture left the keyboard up with no way to close it, hiding the Capture button + tab bar (app felt stuck). Cause: the TextField uses axis: .vertical (multi-line) so Return inserts a newline, and there was no Done/tap/swipe dismissal. Fix: added a keyboard ToolbarItemGroup 'Done' button (isInputFocused=false) + ScrollView.scrollDismissesKeyboard(.interactively) for swipe-to-dismiss. Kept the multi-line field. iOS BUILD SUCCEEDED.
## 2026-07-07 — TIME-123 (Jira TIME-123): Celery beat service + test-push endpoint

docker-compose: added a 'beat' service (celery -A app.workers.celery_app beat) alongside the worker so the beat_schedule actually fires (check-ins, weekly insights, 30-min scan-and-push). ProactivePushService.send_test(user, sender, gateway, title, body): pushes to the user's device tokens NOW, bypassing eligible_for_push + cooldown; uses a {title,body} override if given else the engine's pick; records the PushNotification; returns {apns_available, delivered, title, body, action_type} or {reason: no_device}. POST /api/v1/devices/test-push (current user, own devices only) exposes it. 5 new tests (send_test bypasses eligibility+cooldown; title/body override; no_device; endpoint apns_available=false w/o creds via patched sender; endpoint no_device). Suite 400. Note: this machine's .env already resolves to ApnsPushSender (creds present) — so the endpoint can deliver once a real device token + valid provisioning are in place.
## 2026-07-07 — TIME-122 (Jira TIME-122): iOS remote-push registration

Wired the app for APNs remote push. TimeSense.entitlements: aps-environment=development (Xcode/Apple flips to production for App Store). Info.plist UIBackgroundModes += remote-notification. AppDelegate: on launch requests notification auth then registerForRemoteNotifications; didRegisterForRemoteNotificationsWithDeviceToken -> hex token -> PUT /api/v1/devices {token, platform:ios} (APIClient.put, 401-retry handles the launch race); didFailToRegister logs (non-fatal). Completes the proactive-push loop end-to-end (pending: APNS_* creds on the server + a push-enabled provisioning profile on device). iOS BUILD SUCCEEDED.
## 2026-07-07 — TIME-121 (Jira TIME-121): APNs remote push (backend)

Backend for proactive push. config: apns_key_id/team_id/private_key/bundle_id/use_sandbox (empty key -> disabled). Models: device_tokens (token unique) + push_notifications (action_type/title/body/sent_at/delivered_count; cooldown+audit); migration x4y5z6a7b8c9. Repos + PUT/DELETE /api/v1/devices (200 DeviceAck; sidestepped FastAPI 204-body assertion). Push sender: PushSender Protocol + NullPushSender + ApnsPushSender (ES256 JWT via PyJWT, HTTP/2 via httpx+h2, apns-collapse-id=action_type; never raises; available iff creds+h2) + factory (Google-style gating). Added h2==4.1.0 to requirements. ProactivePushService.push_for_user: gather_candidate_tasks (extracted to app/services/recommendation/candidate_gather.py; now.py delegates) -> build_user_context -> run_engine(gateway) -> require domain!=fallback AND eligible_for_push (score>=75 & conf>=0.75) -> 45-min cooldown (_in_cooldown: same action_type suppressed; different+high-urgency overrides) -> send LLM title/body to each device token -> record PushNotification. Celery push_tasks.scan_and_push over DeviceTokenRepository.distinct_user_ids (UserRepository.get_by_id eager-loads profile/prefs); beat every 30 min; no-op unless APNs configured. CALIBRATION FIX: CandidateAction.location_fit default 0.0 -> 0.5 (neutral for location-independent actions) so a strong overdue/high-priority task can clear the 75 push threshold (pure tasks previously capped ~71). Uniform shift preserves relative ordering. 8 new tests (device register/reregister/unregister/auth; push gating: no token, not-eligible, cooldown-same-type, after-cooldown, null-sender-records-0-delivered). Suite 395. iOS registration = TIME-122.
## 2026-07-07 — TIME-120 (Jira TIME-120): LLM text for arrival push notifications

LocationService.notifyBestTask now calls /now/recommendation (which returns LLM notification title/body with deterministic fallback) after posting the current place, and fires the local notification with the engine's LLM-phrased text when there's a real recommendation (domain != fallback); otherwise a light 'You're at <place>' acknowledgement so we don't nag when nothing's pressing. Replaces the previous plain 'Best next: <task>' string. APNs remote push still not wired (backend follow-up). iOS BUILD SUCCEEDED.
## 2026-07-07 — TIME-119 (Jira TIME-119): iOS surfaces cross-domain engine recommendation

Adopted /now/recommendation on the Now screen. NowViewModel: EngineRecommendation model (action_type/domain/title/message/explanation/confidence/reason_codes/eligible_for_push/related_task_id/travel/destination_place) + lazy fetch after the fast /now payload (@Published suggestion). NowView: SuggestionCard (domain icon, 'TimeSense suggests', title, LLM message, NN% match, travel line 'Place · N min away · fits your window' when present) rendered when suggestion.isCrossDomainAction (related_task_id == nil); supersedes the plain wind-down MomentCard. Task-backed picks unchanged (best-action card). Used title2/caption tokens (no title3/caption2 in the token set). iOS BUILD SUCCEEDED.
## 2026-07-07 — TIME-118 (Jira TIME-118): /now/recommendation full-engine endpoint

Added GET /api/v1/now/recommendation: gather candidate tasks (extracted _gather_candidate_tasks, shared with /now) -> build_user_context -> run_engine(maps provider + LLM gateway) -> NowRecommendationResponse. Unlike /now (task-centric, fast, no LLM), this surfaces the engine's cross-domain decision (prep-for-meeting, wind-down, etc.) with LLM text (deterministic fallback). Response: action_type/domain/title/message/explanation/confidence/score/urgency/estimated_minutes/reason_codes/eligible_for_push + related_task_id (when task-backed) + destination_place/travel (when present) + alternatives (each w/ related_task_id). Added Recommendation.related_entity_ids (set in select_recommendation) so the endpoint can expose the task id. Audits task-backed picks (RecommendationEvent requires task_id). Refined the night penalty: WORKISH exempt when urgent (overdue OR urgency>=0.8, i.e. due very soon) — a due-soon task at night is no longer suppressed; errands still suppressed unless overdue. 3 new tests (task pick includes related_task_id; no-tasks -> non-task action w/ null id; 401). Suite 387. Not adopted by iOS yet.
## 2026-07-07 — TIME-117 (Jira TIME-117): LLM explanation layer (final engine phase)

Built the spec's phase 12. llm/fallback_recommendation_text.fallback_text(rec) — deterministic LLMRecommendationText (title/body/explanation), enriched with a KNOWN travel time when present. llm/generate_recommendation_text.generate_recommendation_text(rec, ctx, gateway) — strict system prompt (rewrite-only; never change the action; never invent distances/times/open-closed/conflicts/preferences; return strict JSON title<=6w/body<=24w/explanation<=40w); builds context facts (part of day, free block, place, destination, KNOWN travel time, tone); parses JSON (handles markdown fences); any exception/empty/unparseable -> fallback. engine.run_engine gained optional gateway -> populates rec.title/message/explanation from the LLM (action_type/domain unchanged — LLM returns text only). Documented GOOGLE_MAPS_API_KEY in backend/.env.example + docs/launch/release_checklist.md. 7 new tests (fallback shape; JSON parse incl. markdown; failure/garbage->fallback; run_engine(gateway) sets text but NOT action; no-gateway deterministic). Suite 384. /now stays LLM-free (fast); /now/why keeps its structured explainer. This COMPLETES the recommendation-engine-build-spec.md (phases 1-12).

## 2026-07-07 — TIME-116 (Jira TIME-116): iOS syncs saved places to /places

Added APIClient.put; LocationService.syncPlaces() PUTs the saved places (name, place_type inferred from name keywords, lat/lng, is_preferred) to /api/v1/places, called after savePlace/removePlace and on start(). This populates the backend user_places so the engine (TIME-115) can resolve errands + compute travel time. Only a GOOGLE_MAPS_API_KEY on the server remains for real driving-time. iOS BUILD SUCCEEDED. Completes the location-aware engine path end-to-end (pending API key).
## 2026-07-07 — TIME-115 (Jira TIME-115): Real maps provider + coordinate plumbing

Made the engine's location features real (gated). Added: config google_maps_api_key; user_places table (name/place_type/lat/lng/is_preferred per user; unique(user,name); migration w3x4y5z6a7b8) + UserPlaceRepository (list, replace_all) + GET/PUT /api/v1/places (app syncs its saved places WITH coords — deliberate named places, not a trail). GoogleMapsProvider (httpx async geocode/nearbysearch/textsearch/distancematrix; never raises → None/[]; available iff key). maps/factory.get_maps_provider() returns GoogleMapsProvider(key) when settings.google_maps_api_key set else NullMapsProvider. context_builder: preferred_places from user_places; travel ORIGIN = coords of the saved place the user is currently at (location.place_name match) — no live-GPS storage. 9 new tests (places sync/replace; context origin+preferred; end-to-end errand-leads-when-maps-confirms-fit via stub provider; provider gating + distance-matrix parse). Suite 377. Still dormant until a real key is set AND the app syncs places (iOS sync = TIME-116).

## 2026-07-07 — TIME-114 (Jira TIME-114): Engine integrated into /now

Wired the deterministic engine into /now. New context_builder.build_user_context(db,user,tasks,now,usable) maps ORM Task->TaskItem (priority 1-2/3/4-5 -> high/med/low; status; estimate; due; light location-intent detection via place keywords + trigger phrases), builds time snapshot (work hours), location snapshot, sleep-derived HealthContext, prefs; free block = UsableTimeService. maps/factory.get_maps_provider() -> NullMapsProvider (TIME-115 swaps). now.py _ranked_candidates now calls _engine_rank_tasks: build ctx -> generate_candidate_actions -> rank_candidates -> map ranked task/location candidates back to ORM Tasks (order preserved; safety-append unsurfaced). Removed TaskScorer + _location_rerank from /now. Fixes found during integration: (1) task_candidates only generated for bucketed tasks -> added TaskContext.all_tasks so EVERY active task gets a candidate; (2) added an engine penalty: at home + location candidate without confirmed TRIP_FITS -> +60 (restores TIME-110 guarantee within the engine). Updated 2 legacy location tests to the engine's principled behavior (errand only leads with confirmed feasibility). /now/why unchanged (LLM explanation is the last phase). 3 new tests; full suite 368.

## 2026-07-07 — TIME-113 (Jira TIME-113): Recommendation engine — candidates, scoring, ranking/selection

Phases 7-10 of the deterministic engine. candidates/: per-domain generators (task per-active-task + batch; location via maps+travel-feasibility, degrades to low-confidence w/ LOCATION_DATA_MISSING/MAPS_API_UNAVAILABLE; calendar prep/join/leave/focus/review; health recover/break/walk/wind_down; routine; planning; context_switch; always-on fallback) + generate_candidate_actions(ctx, maps, now). scoring/: score_candidate (weighted sum *100 - penalty, clamp 0-100) + penalties.py hard rules (meeting<=15 suppresses deep_work/errands; short block no deep work; poor sleep/low energy dampens demanding work unless hard deadline; night suppresses errands+work unless overdue; TRIP_DOES_NOT_FIT +70; PLACE_CLOSED +40; missing maps/location +20; feedback reject/dismiss penalties). selection/: rank_candidates (score,conf,urgency desc); notification_policy.eligible_for_push (>=75 & >=0.75); select_recommendation (best+alts+reason codes+confidence+deterministic fallback text). feedback/apply_feedback (pure FeedbackSummary). engine.run_engine orchestrator (generate→feedback→score→rank→select; NO LLM). 17 new tests mapping spec scenarios (meeting soon/now, free-block sizes, overdue, poor sleep, sedentary walk, Walmart-from-home-no-maps doesn't lead, preferred-place trip fits/doesn't-fit, night suppresses errands, push thresholds, missing-data no-crash). Suite 365. NOT wired into /now yet (TIME-114).

## 2026-07-07 — TIME-112 (Jira TIME-112): Recommendation engine foundation (phases 1-6)

Began rebuilding the recommendation engine per recommendation-engine-build-spec.md as a deterministic, scored decision system (LLM only explains later, never selects). New package app/services/recommendation/ (Python port of the TS spec; no Any). Phases: (1) types.py — ActionType/ReasonCode/domains + Coordinates/TimeSnapshot/Place/TaskItem/CalendarEvent/HealthContext/UserContext/CandidateAction/Recommendation dataclasses. (2) time_service.get_time_snapshot (tz-aware, injectable now). (3) location_service.get_user_location_snapshot (from UserLocationState; safe when missing). (4) maps/ — MapsProvider Protocol + NullMapsProvider + MapsSkillService wrapper (preferred-first resolution; returns None → low-confidence, never invents). (5) travel_feasibility_service.calculate_travel_feasibility (total=travel+onsite+after+buffer; None without maps). (6) normalize_context — derives calendar/task context (buckets, free block, deadlines) from raw inputs, pure/testable. 15 new tests; suite 348. INSPECTION: TaskScorer→refactor to one input; now.py _ranked/_location_rerank→replace; usable_time/scheduling/task_duration/feedback/location repos→reuse; LLM removed from selection. No maps API/coords configured → NullMapsProvider (real provider + coordinate plumbing later). NOT yet wired into /now (integration in a later phase).

## 2026-07-07 — TIME-111 (Jira TIME-111): Swipe-to-reveal Done + Delete on Today

User: wanted swipe-to-delete showing Delete + Mark done buttons. Added SwipeableRow (custom DragGesture — Smart Plan is a card, not a List, so .swipeActions isn't available) revealing green Done (hidden if already done) + red Delete; highPriorityGesture with horizontal-intent guard so vertical scroll still works; snaps open/closed; tapping a button runs markDone/deleteTask and closes. Replaced the long-press context menu. iOS BUILD SUCCEEDED.

## 2026-07-07 — TIME-110 (Jira TIME-110): Location always factored; errands never lead while home

User bug: at home at 5pm, app recommended 'Go to Walmart' (an errand you can't do from home). Two causes fixed: (1) iOS never told the backend it was home — no enter event fires when already inside a region on save/launch. Now LocationService posts the current place on EVERY didDetermineState (incl. seed/sync from registerGeofence + reregisterGeofences requestState), split from notify; seeds never touch lastRegionState so they can't dedup a real relaunch event. (2) Backend _location_rerank: at home, errands now sink below every non-errand (delta n+1) so they can never be the top pick while home; out, errands still surface (-2). New test: due-now high-priority 'Go to Walmart' does not lead while home. Location tests 3; iOS BUILD SUCCEEDED.

## 2026-07-07 — TIME-109 (Jira TIME-109): Delete tasks from Today

User: needed to delete completed / no-longer-viable tasks. Added TodayViewModel.deleteTask -> DELETE /api/v1/tasks/{id} (existing soft-delete) -> reload; Smart Plan rows get a long-press context menu ('Mark done' if pending + 'Delete task'). Delete only on Today for now. iOS BUILD SUCCEEDED.

## 2026-07-07 — TIME-108 (Jira TIME-108): Location shapes the recommendation

Wired location into the recommendation. Backend: user_location_states table (place_name nullable, is_home; one per user; migration v2w3x4y5z6a7) storing only the derived place NAME (no raw coords); UserLocationRepository (get_current w/ 6h staleness, upsert); POST /api/v1/location/place upserts. /now + /now/why rerank via _location_rerank: out/away -> errand/shopping/appointment/travel tasks surface (+/-2 position nudge, scorer order as tiebreak); home -> they drop. Explainer Location signal/context now reflect the real place ('at Home' / 'out and about') instead of 'not connected'. iOS LocationService posts the place on each geofence transition (place on enter, null on exit) before fetching the best task. 2 new tests (signal reflects place; errand outranks focus when out, not home). Suite 332; iOS BUILD SUCCEEDED. Backend tests: 332.

## 2026-07-07 — TIME-107 (Jira TIME-107): Save any number of named places

User: could only save Home/Work. Replaced the two fixed buttons in PlacesSettingsView with an 'Add this location' card: a name TextField + 'Save here' button + quick-pick chips (Home/Work/Gym/School/Errands) that prefill the name. Name-aware row icons; save gated on name+location; capped at iOS's 20-region limit (UI note + LocationService.savePlace guard, trims/validates the name). The service already accepted arbitrary names. iOS BUILD SUCCEEDED.

## 2026-07-07 — TIME-106 (Jira TIME-106): Geofence radius 150->100m

User point: a smaller radius crosses the exit boundary sooner, so departures fire earlier. Reduced SavedPlace radius 150->100m — the practical reliability floor (iOS accuracy ~50-150m; below 100m brings jitter/false triggers, mitigated by TIME-105's state-verification dedup). iOS exit hysteresis (~150-200m beyond boundary) is inherent so radius only helps at the margin. iOS BUILD SUCCEEDED.

## 2026-07-07 — TIME-105 (Jira TIME-105): Reliable geofence notifications

User report: leaving home fired no notification, and arriving fired 'you left home' (a stale/late exit event delivered on return). Fixed by not trusting raw enter/exit events: on didEnter/didExit we now call requestState(for:) and act on didDetermineState (authoritative inside/outside), tracking lastRegionState per region and notifying only on a real change (dedups contradictory late events). Seed state on save (no spurious alert) but not on relaunch (so a background-relaunch event still fires once). Radius 130->150m. iOS exit latency (minutes) is inherent but events are now correct. iOS BUILD SUCCEEDED.

## 2026-07-07 — TIME-104 (Jira TIME-104): Deep-link to iOS Settings for Always location

User report: tapping 'Allow Always' did nothing — iOS silently no-ops requestAlwaysAuthorization (shows the upgrade prompt at most once, usually deferred). Verified the built Info.plist HAS the Always usage key + background mode (not a config bug). Added LocationService.openAppSettings() (UIApplication.openSettingsURLString) and made PlacesSettingsView's permission card state-based: notDetermined->Enable; WhenInUse->explainer + 'Open iOS Settings'; denied->Open Settings; always->all set. iOS BUILD SUCCEEDED.

## 2026-07-07 — TIME-103 (Jira TIME-103): Location-aware background arrival notifications

Added the location subsystem. LocationService (CoreLocation): permission step-up (WhenInUse->Always), region monitoring of saved places, on enter/exit -> GET /now -> local notification; one-time fix for saving places. AppDelegate (@UIApplicationDelegateAdaptor) configures Firebase + inits LocationService on launch so geofence events are handled after background relaunch (moved Firebase.configure out of App.init). Info.plist: location usage strings + UIBackgroundModes location. PlacesSettingsView (Settings -> Integrations -> Location & Places): enable location, save Home/Work from current location, list/remove, shows real auth status. Notification permission requested. Privacy Location row now reflects the real permission. Only user-chosen place centers persisted (UserDefaults) — no raw track. NEEDS ON-DEVICE TESTING (permissions/background/geofence can't be verified headless). Recommendation not yet location-informed server-side (arrival surfaces the current best task) — follow-up. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-102 (Jira TIME-102): Visual polish (light-mode contrast)

Final item of the screen-redesign pass. Darkened the TextSecondary token in light mode (#8A8A8E -> #5E5E66) for legible helper text; slightly brighter in dark mode. Global via the asset catalog. Verified on the sign-in screen (secondary text noticeably more legible). Chips/card-hierarchy/section-header items from note #12 were already delivered across TIME-090-101. iOS BUILD SUCCEEDED. Completes the redesign batch (screens 3-12).

## 2026-07-06 — TIME-101 (Jira TIME-101): Settings home grouping

Regrouped SettingsView into AI Planning (Learned Patterns, Working Hours, Notification Timing) / Integrations (Calendar, Health) / Privacy (Privacy & Consent, Delete My Data) / Account (Profile, Subscription, Appearance, About, Version). Sign Out stays at the bottom. Skipped non-existent rows (Recommendation Preferences, Notion, Location, separate Export) to avoid dead stubs. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-100 (Jira TIME-100): Subscription redesign

Rebuilt SubscriptionSettingsView to the mockup: Current Plan card (Basic (Free)/Premium + leaf/crown icon); 'Basic includes' checklist; indigo 'Premium unlocks' card (AI best-next-action, integrations, weekly insights, proactive notifications, unlimited integrations); 'Upgrade to Premium' button + 'Plans managed in the App Store'. is_premium hides the upgrade CTA. StoreKit purchase still a follow-up. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-099 (Jira TIME-99): Privacy & Consent redesign

Rebuilt PrivacyConsentView to the mockup: banner ('you're in control'); 'Connected signals' card (Calendar/Health/Location/Audio rows with icon+subtitle+status, shown honestly as Off/Disabled until integrations exist); 'Data controls' card (Delete my data wired to DELETE /privacy/account + signOut; Export my data = coming-soon stub); encrypted/never-sold footer. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-098 (Jira TIME-98): Calendar screen redesign

Rebuilt CalendarSettingsView to the mockup: large calendar hero; 'Connect your calendar' + copy; 'Connect Calendar' button; 'Supported providers' card (Google/Apple rows); 'Learn more about calendar privacy' link. Connect actions = coming-soon alert with the privacy note (in-app OAuth is a follow-up). Removed the 'connect on web' text. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-097 (Jira TIME-97): Working Hours redesign

Rebuilt WorkingHoursSettingsView to the mockup: explainer banner (why hours matter); card with Start/End menu-picker rows + a Repeat day-of-week selector (Mon-Fri default, visual only) + Save; end<=start validation retained. Per-day hours not persisted yet (future premium). iOS BUILD SUCCEEDED.
## 2026-07-06 — TIME-096 (Jira TIME-96): Learned Patterns rename + redesign

Renamed 'Learned Assumptions' -> 'Learned Patterns' (screen title + Settings row). Redesigned to the mockup: explainer banner; icon rows (Sleep/Breakfast/Lunch/Morning/Evening) with name + time range + confidence line + chevron (tap to edit); 'Add manual pattern' button (coming-soon stub). Confidence derived honestly client-side (customized -> High/Set by you, else Medium/Default pattern; no fabricated day counts). Edit sheet unchanged. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-095 (Jira TIME-95): Insights locked-state redesign

Rebuilt InsightsPremiumGate to preview the AI value (mockup): indigo 'Your AI Insights' lock banner with better copy; preview cards (Best focus window/Pattern detected/Schedule balance/Routine consistency) with small illustrative line/bar/ring charts under a subtle locked veil; 'Upgrade to Premium' + 'See all features'; crown nav icon. Preview values are illustrative samples. Premium body unchanged. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-094 (Jira TIME-94): Capture redesign (AI-native)

Rebuilt CaptureView to the mockup: hero indigo circle + waveform icon; title "What's on your mind?"; new AI copy; input box with a mic button (voice = coming-soon alert stub); selectable quick chips (Task/Reminder/Schedule/Errand/Idea); full-width Capture button; "TimeSense can detect" row (Time/Priority/Task type/Schedule fit); sparkles nav icon. Capture behavior unchanged. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-093 (Jira TIME-93): 'Why this recommendation' screen redesign

Redesigned the recommendation-explanation screen to the mockup (the key recruiter-facing view).
Backend: build_explanation returns structured `signals` (name/detail/available) for Calendar, Time
of day, Location, Priority, Energy — available=False when a signal isn't connected (Location/Energy);
WhyResponse gains `signals`. iOS: RecommendationExplanation decodes signals; the sheet is rebuilt as
a ScrollView — RecommendedActionHeaderCard (icon + title + "for N minutes" | Confidence ring),
SignalsCard (icon + name + detail + green check), AlternativesCard (icon + title + reason + chevron),
plain-English Summary, "Evaluated just now". New ConfidenceRing (circular %). Removed the old
List-based sheet + BulletLabelStyle. Backend 330 passing; iOS BUILD SUCCEEDED. This starts the
multi-screen redesign pass (user's notes for screens 3-12); remaining screens queued.

## 2026-07-06 — TIME-092 (Jira TIME-92): Redesign the Today page to the approved mockup

Rebuilt Today to the mockup. TodayViewModel also fetches /now for the recommendation card + adds
fetchExplanation and markDone(taskId). NowTask now decodes due_at (for "before 6:00 PM");
TaskCategoryStyle gained locationAware (Errand/Appointment) for the "Location-aware" tag; shared
WhyThis / RecommendationExplanationSheet / taskCategoryStyle made internal for reuse. TodayView:
DateSummaryRow ("July 6, 2026" + "N of M complete" + calendar icon); "AI Recommended Now" card
(category icon, title + "before <due>", meta line, "Why this recommendation?" → sheet); "Smart Plan"
card grouping tasks by Morning/Afternoon/Evening/Anytime with tap-to-complete rows. Dropped the
visible auto-schedule Undo on rows for the clean look (unschedule still in the VM). iOS BUILD
SUCCEEDED. Not visually verified (Today is behind auth). Tab bar unchanged.

## 2026-07-06 — TIME-091 (Jira TIME-91): Context chips fit on one row (no scroll)

Per user: the Now context chips (Calendar/Routine/Location/Time/Tasks) should all be visible at
once. ContextChipsRow: removed the horizontal ScrollView; the five chips now share the row equally
(frame maxWidth .infinity) with lineLimit(1) + minimumScaleFactor(0.75) so labels never truncate on
narrow screens. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-090 (Jira TIME-90): Redesign the Now page to the approved mockup

Rebuilt Now to match the user's mockup. Backend: exposed `confidence` (0–1) on /now via a shared
compute_confidence() (extracted from the explainer) so the card and the explanation sheet agree.
iOS NowView: inline "Now" title + sparkles; AnalysisBanner ("TimeSense analyzed your day ·
Re-evaluated N min ago" from lastLoaded); ContextChipsRow (Calendar/Routine/Location/Time/Tasks);
BestNextActionCard (header + "AI Recommended" badge, category icon, title + "for N minutes", centered
meta line, inline Confidence bar, "Why this recommendation?" → sheet, kept Done/Snooze/Not-now);
OtherOptionsSection list (category icon, title, "N min · descriptor", chevron → the task's
explanation sheet). Added client-side taskCategoryStyle(title) → icon/colour/descriptor. Removed the
old GreetingHeader + PriorityBadge. The mockup's center "+" FAB tab bar is a separate follow-up.
Backend 330 passing; iOS BUILD SUCCEEDED. Not visually verified (Now is behind auth).

## 2026-07-06 — TIME-089 (Jira TIME-89): Rich structured "Why This Recommendation?" + pipeline

Turned the one-line why into a full structured explanation. recommendation_explainer.build_explanation
normalizes live context (calendar free-time + next event, time-of-day/focus, health/energy from
today's sleep signal if present, location from a recent commute if present, task data), computes
deterministic decision_factors (Priority/Time fit/Energy match/Location fit/Urgency) + a heuristic
confidence (0.5–0.95), deterministic alternative reasons, and an LLM summary (deterministic
fallback). Signals only appear when we actually have them — never fabricated. GET /now/why now
returns the structured WhyResponse (recommended_action, confidence, context_used, decision_factors,
alternatives_considered, summary; keeps backward-compatible `reason`) and writes a
recommendation_events audit row (JSONB on Postgres / JSON on SQLite via with_variant — the initial
JSONB-only column broke SQLite test DB creation; fixed). iOS: RecommendationExplanation model; the
button lazily fetches then presents a sheet with sections. 1 new test; suite 330 passing; iOS BUILD
SUCCEEDED; migration u1v2w3x4y5z6 applied.

## 2026-07-06 — TIME-088 (Jira TIME-88): Rename Now 'Why this?' → 'Why This Recommendation?'

Copy tweak on the Now best-task card: the expandable recommendation-explanation link now reads
"Why This Recommendation?" (was "Why this?"). No behavior change — still collapsed by default,
lazily fetches the reason on tap. iOS BUILD SUCCEEDED.

## 2026-07-06 — TIME-058 (Jira TIME-86): Beta Smoke Test & Release Checklist (v1 close-out)

Closed out the v1 build. Added scripts/smoke_test.py (liveness + auth-gate checks: health 200,
protected routes 401 — all PASS against the live backend), docs/launch/beta_smoke_test.md (~10-min
manual device checklist), and docs/launch/release_checklist.md (go/no-go across engineering/infra/
auth/store/legal + post-v1 follow-ups). Verified this session: backend suite 329 passing, iOS build
SUCCEEDED, web `npm run build` compiled, live smoke all PASS. Android build NOT verified — no JDK on
the dev machine ("Unable to locate a Java Runtime"); noted in the checklist. (Also fixed: the Jira
create-script dedup cap 100→500, and deleted a duplicate TIME-058 ticket created by an accidental
double-run + Jira indexing lag.) v1 is feature-complete; remaining items are release-gating (deploy,
store submission) or post-v1 features, tracked as follow-ups.

## 2026-07-06 — TIME-087 (Jira TIME-85): On-device dev — reach the Mac backend over the LAN

Demoing on a physical iPhone failed with "cannot connect to the server" — on a device localhost is
the phone, not the Mac. APIClient.resolveBaseURL() now: API_BASE_URL env wins; simulator → localhost;
physical-device DEBUG → the Mac's Bonjour .local name (ekeles-MacBook-Pro.local:8000, stable across
IP changes); release → prod URL placeholder. Added ios/TimeSense/Info.plist (merged via
GENERATE_INFOPLIST_FILE=YES + INFOPLIST_FILE) with NSAllowsLocalNetworking=true +
NSLocalNetworkUsageDescription so cleartext HTTP to the LAN/.local is allowed and iOS prompts for
local-network access. Verified the built plist has BOTH the ATS key and the generated keys
(UILaunchScreen, bundle id); iOS BUILD SUCCEEDED. Backend already reachable on the LAN via run_dev.py
(all interfaces). Requires phone+Mac same Wi-Fi and tapping Allow on the local-network prompt.

## 2026-07-05 — TIME-086 (Jira TIME-84): Configurable working hours

Replaced the hardcoded 8am–9pm scheduling window with a per-user preference. Added
user_preferences.work_start_hour/work_end_hour (migration t0u1v2w3x4y5; defaults 8/21) on the model,
UserPreferencesResponse, and UserPreferencesUpdate (validated 0–22 / 1–23, end > start via
model_validator; end capped at 23 to avoid the replace(hour=24) window-math edge). Repo
update_preferences accepts them. Capture auto-schedule and /now feasibility now build
SchedulingService from the user's hours (fallback 8/21). iOS: Settings ▸ Working Hours screen (start/
end hour pickers with 12-hour labels, Save → PATCH; disabled when end ≤ start). 1 new test
(roundtrip + 422 on end≤start); suite 329 passing; iOS BUILD SUCCEEDED; migration applied.

## 2026-07-05 — TIME-085 (Jira TIME-83): Best-time auto-scheduling with Undo

Completes the scheduling brain. Added tasks.auto_scheduled (migration s9t0u1v2w3x4) on the model +
TaskResponse. Capture now auto-places an untimed, due-today/undated task into the next open slot via
SchedulingService.find_slot (estimate + working hours + existing blocks), marking auto_scheduled=True
(skips when no slot fits today). POST /tasks/{id}/unschedule clears the slot + flag. iOS: TimelineTask
decodes auto_scheduled; Today's TimelineCard shows "Scheduled by TimeSense · Undo" for auto-placed
tasks, Undo → TodayViewModel.unschedule → reload. Only places today; 8–21 default window; internal
scheduling (not a calendar write). 2 new tests; suite 328 passing; iOS BUILD SUCCEEDED; migration
applied to dev DB.

## 2026-07-05 — TIME-084 (Jira TIME-82): Feasibility warnings (+ scheduling core)

Added SchedulingService (shared core): find_slot(now, duration, scheduled_tasks, tz, not_before) →
earliest fitting start today inside the working window (default 8am–9pm local) and around busy
blocks; free_minutes_before(deadline, ...) → free minutes before a deadline. /now: for the best
task, if it has a future due_at today and free_minutes_before(due) < estimated_minutes → returns a
feasibility warning {fits:false, message, suggested_slot} naming the next realistic slot (or "no
slot left today"). _ranked_candidates now also returns today_tasks. iOS: NowContext decodes
feasibility; a gentle FeasibilityCard (warning tint) shows under the best task when it won't fit.
4 new scheduling tests; suite 326 passing; iOS BUILD SUCCEEDED.

## 2026-07-05 — TIME-083 (Jira TIME-81): Learn actual durations ("How long did that take?")

The learning trigger for the duration brain. Repo LEARNING_SAMPLE_TARGET=5 + learning_active();
estimator.should_ask(). Endpoints: GET /tasks/{id}/duration-prompt → {ask, category} (ask only while
sample_count < 5), POST /tasks/{id}/duration-feedback {actual_minutes} → record_actual (EMA) and
returns the updated learned {category, estimated_minutes}. iOS: after markDone (now takes the title,
from hero + alternatives), calls duration-prompt; if ask, shows a confirmationDialog (~15/~30/~1h/
Skip) whose chip POSTs feedback. So the prompt appears only during the learning period and fades as
estimates get confident — never becomes a chore. 5 new duration tests (incl. learn-then-stop-asking);
suite 322 passing; iOS BUILD SUCCEEDED.

## 2026-07-05 — TIME-082 (Jira TIME-80): Task duration brain (seed table + learned estimates)

Foundation of the scheduling "brain": every task gets a realistic time estimate. app/services/
task_duration.py holds a seed DEFAULT_DURATIONS table + keyword infer_category() (appointment/
meeting/call/email/shopping/errand/chore/exercise/cooking/writing/reading/admin/travel/general) so
estimates work without the LLM. New task_duration_estimates table (user_id, category,
estimated_minutes, sample_count; unique per user+category; migration r8s9t0u1v2w3) is the personal
lookup table the AI refines: TaskDurationRepository.record_actual folds real durations in via EMA
(alpha 0.3); TaskDurationEstimator.estimate returns the learned value when present else the seed.
Capture now fills estimated_minutes from the estimator when the LLM didn't. Does NOT yet schedule/
check feasibility or capture actual durations from the UI (follow-ups TIME-083/084/085 teed up).
4 new tests; suite 321 passing. Migration applied to the live dev DB.

## 2026-07-05 — TIME-081 (Jira TIME-79): Usable-time cap uses local midnight

UsableTimeService capped "time left today" at UTC midnight, so the "usable minutes" on Now was wrong
for non-UTC users (over/under-reported, esp. in the evening) — same class of bug as the greeting
(TIME-080). calculate() now takes user_timezone and caps at the user's next LOCAL midnight (converted
to UTC; bad tz → UTC fallback). Callers pass the tz: /now (_ranked_candidates via
user.profile.timezone) and RecommendationService.recommend. Google Assistant webhook keeps the UTC
default. New test (UTC+11 late-local → ~60 min vs UTC → 240). Backend-only; 317 passing.

## 2026-07-05 — TIME-080 (Jira TIME-78): Local-time-aware Now (greeting + wind-down moment)

Per user guidance ("local time you always have; energy you don't"), grounded Now in local time.
Fixed a real bug: _greeting used UTC hour → wrong for the user's timezone; now derived from the
profile timezone (adds a "You're up late" band < 5am). Added NowResponse.moment (deterministic,
no LLM): when local hour >= 21 or < 5 AND no urgent task (overdue / due <= 3h / priority 1), returns
a gentle wind-down nudge; else null. iOS decodes moment and shows a calm MomentCard (moon icon)
above the best task; the top task is still offered. Recommendations still come only from the user's
tasks — the moment is framing, not a new "rest" task. Backend 316 passing (2 new tests); iOS BUILD
SUCCEEDED.

## 2026-07-05 — TIME-079 (Jira TIME-77): 'Why this?' must justify the pick

User report: the reason contradicted the recommendation — for "Go to Home Depot today" the why said
"consider resting now… plan your trip when more energized", arguing against the recommended task.
Cause: the energy hint fed to the LLM said "evening — better to wrap up than start heavy work",
nudging it to discourage the task. Fixed: _EXPLAIN_SYSTEM now states the task is ALREADY chosen and
fixed and the model must only justify it, explicitly forbidding suggestions to rest/wait/do later/
pick another task; reframed _part_of_day energy hints to descriptive framing (evening: "energy is
winding down, so finishing a manageable task feels satisfying"). Verified live: why now justifies
the pick ("manageable errand… fits your 72-minute window… sense of accomplishment"). Confirmed to
the user that recommendations come ONLY from their task list (rest is not a task). Backend-only; 314
passing.

## 2026-07-05 — TIME-078 (Jira TIME-76): Lazy-load 'Why this?' on tap

TIME-077 generated the LLM reason on every /now load (~1-2s + a cost each load, though "Why this?"
is collapsed by default). Made /now fast again: extracted _ranked_candidates(); /now returns best +
alternatives + usable_minutes with NO LLM call (reason stays null). New GET /now/why?task_id=
recomputes the ranking, finds the task + its alternatives, and returns explain_choice (404 if not
currently recommended). iOS: WhyThis self-loads on first expand — calls fetchWhy(taskId) → GET
/now/why, shows a "Thinking…" spinner, caches the result; collapse/re-expand doesn't refetch.
Backend 314 passing (2 new /now/why tests); iOS BUILD SUCCEEDED.

## 2026-07-05 — TIME-077 (Jira TIME-75): Now alternatives + richer LLM 'Why this?'

The 'Why this?' just said "best move right now". Now shows the best hero PLUS two alternatives, and
the reason is a real explanation of why the best beats them. RecommendationService.explain_choice
(now public) builds an enriched LLM prompt: the alternatives, a time-of-day + energy heuristic
(morning=fresh, afternoon dip, evening=winding down — from the user's timezone), free time before
the next commitment, and deadlines; with a richer deterministic fallback for when the LLM is down.
/now returns alternatives (ranked[1:3]) and uses explain_choice for the reason (added the LLM gateway
dep + user timezone from profile); /recommendations also passes timezone. iOS: NowContext decodes
alternatives; Now renders an "Or consider" list of compact AlternativeRow cards (tap circle to
complete). Verified live: LLM produced "Going to Home Depot now is a productive way to use your
energy while wrapping up the day..." — the user's OpenAI credits are active again. Note: the reason
is generated eagerly per Now load (~1-2s LLM latency); lazy-on-tap is a possible follow-up. Backend
313 passing; iOS BUILD SUCCEEDED.

## 2026-07-05 — TIME-076 (Jira TIME-74): Make Settings rows functional (+ Sign Out, Delete)

Most Settings rows were dead placeholders (chevron, no action) and there was no Sign Out. Added
SettingsScreens.swift with real screens wired to existing endpoints: Profile (email + display_name
PATCH /users/me/profile), Subscription (read-only status from /subscriptions/me), Notifications
(notification_mode picker → PATCH /users/me/preferences), Appearance (System/Light/Dark via
@AppStorage applied at app root + PATCH preferences.theme), Privacy & Consent (summary), Calendar
(honest web-managed status), About. SettingsView now uses NavigationLinks for all; Delete My Data →
confirm alert → DELETE /privacy/account?confirm=true → signOut; a Sign Out section → signOut.
TimeSenseApp applies the stored theme via .preferredColorScheme. Registered the new file in the
Xcode target (xcodeproj gem). iOS BUILD SUCCEEDED. No backend changes (existing endpoints). Not
visually verified (Settings is behind auth; can't headless sign-in) — standard SwiftUI Forms.

## 2026-07-05 — TIME-075 (Jira TIME-73): 'Why this?' reasoning on Now

Added a deterministic recommendation reason to /now (reason: str|None) built from the chosen task —
overdue / due today / due <weekday>, high priority, and "fits your N free minutes", with a calm
fallback. NowContext decodes it; BestTaskCard shows a "Why this?" button (sparkles + chevron) that
expands to the reason, hidden by default per the premium-UX spec. No LLM (Now stays fast). Backend
test asserts a reason is returned. Backend 313 passing; iOS BUILD SUCCEEDED.

## 2026-07-05 — TIME-074 (Jira TIME-72): Fix Now quick actions (wire Snooze/Not-now + no wrap)

On Now, "Not now" and "Snooze" had empty actions (did nothing) and "Snooze" wrapped to two lines.
Fixed: NowViewModel.snooze/notNow POST to /recommendations/feedback (snooze_until ~3h for snooze);
/now now excludes get_suppressed_task_ids (active snooze / not_now cooldown) so those actions
actually surface a different best task; QuickActionRow rebuilt as a full-width primary Done + two
compact secondary pills (lineLimit(1)+fixedSize → never wrap). Backend test: not_now suppresses the
task from /now. Backend 312 passing; iOS BUILD SUCCEEDED.

## 2026-07-05 — TIME-073 (Jira TIME-71): Premium visual redesign (calm/minimal)

User feedback: "the app looks cheap; it was supposed to look expensive." Direction chosen: calm &
minimal, Apple-like. Elevated the design system (inherited by every screen): white Surface (#FFFFFF)
cards on a soft-gray Background (#F4F4F6) so cards float; deeper indigo accent (#4F46E5); refined
neutrals; SF Pro (default face, not rounded) with a tighter heading scale + Tracking tokens; softer
diffuse shadow tokens; CardModifier now a continuous-corner surface with a hairline + soft shadow.
Redesigned the Now hero: large tracked greeting header (unboxed), a spacious "Do this next" hero
card, warmer empty state. iOS BUILD SUCCEEDED; verified the sign-in screen renders premium via a
Simulator screenshot (authed screens inherit the same tokens). "Why this?" reasoning is the next
ticket. No logic/data changes.

## 2026-07-05 — TIME-072 (Jira TIME-70): Rule-based date fallback for capture

Root cause of "the best task on Now doesn't update when I add tasks": the LLM parse was failing
(OpenAI 429 / quota exhausted — the user's key is valid but out of credits), and the fallback just
stored the raw text with NO due date. With every task at due_at=None + priority 3, the scorer ties
them all so the best never changes. Added app/services/capture_date_parser.py (parse_datetime):
extracts today/tonight/tomorrow, weekday names (next occurrence), "Month Dayth", and "at 5pm"/
"9:30am" → a UTC due_at (default 5pm local for date-only) + a cleaned, capitalized title with the
scheduling phrase stripped. CaptureService now uses it on LLM failure. New captures get dates → the
scorer prioritizes due-today over undated/tomorrow. (Existing undated tasks are not backfilled; the
LLM remains primary when available.) 8 parser tests + updated 2 capture assertions (titles now
cleaned); suite 316/316 excl. 2 flaky.

## 2026-07-05 — TIME-071 (Jira TIME-69): Today shows untimed pending tasks

Reported while using the app: "why is it only showing 1 task?" — Now intentionally shows only the
single best next action, and Today showed only scheduled blocks, so captured (untimed) tasks had no
visible home even with 14 saved. GET /api/v1/timeline/today now, when viewing today, appends the
user's untimed pending tasks (scheduled_start is None) to the scheduled-today set (untimed sort
last) — so Today is the user's full to-do list. Non-today dates unchanged. (The related "best task
is tomorrow's" complaint was because old tasks lacked extracted due dates — captured while the
OpenAI key was invalid; new captures with the now-valid key extract due_at so day-prioritization
works via the existing scorer. No scorer change.) New test; suite 308/308 excl. 2 flaky.

## 2026-07-05 — TIME-070 (Jira TIME-68): iOS recover from 401 (refresh + sign-out-to-sign-in)

Reported: on launch the app showed "Session expired. Please sign in again." as a dead-end (no
sign-in screen); switching tabs then worked. Root cause: `AppState.isAuthenticated` flips true the
moment Firebase restores the user, so the tabs render and fire API calls BEFORE AuthService's async
`getIDToken` sets the token on APIClient — the first request 401s; later tab loads work because the
token has arrived by then. And a 401 was surfaced as an in-view error, never routing to sign-in.

Fix:
- APIClient: added a `tokenProvider` closure; on a 401 it refreshes the token once and retries the
  request (fixes the launch race + hourly Firebase token expiry). If still 401, posts
  `.apiUnauthorized` and throws.
- AuthService: sets the tokenProvider (`getIDToken(forcingRefresh: true)`) and observes
  `.apiUnauthorized` → `signOut()` → currentUser=nil → ContentView shows SignInView, so a genuinely
  invalid session lands the user on the sign-in screen instead of a dead-end.

iOS BUILD SUCCEEDED. (No backend change.)

## 2026-07-05 — TIME-069 (Jira TIME-67): Dual-stack dev server launcher

Found while the user ran the app on the Simulator: it failed with `nw_endpoint_flow_failed
[::1.8000]`. Root cause — the documented `uvicorn app.main:app` binds IPv4 (127.0.0.1) only, but
macOS resolves `localhost` to IPv6 `::1` first, so the Simulator (calling localhost:8000) couldn't
connect. Added `backend/run_dev.py` which binds an AF_INET6 socket with IPV6_V6ONLY=0 (dual-stack)
and serves app.main:app on it, so both ::1 and 127.0.0.1 respond. Documented in CLAUDE.md's Commands
(use `python run_dev.py` for Simulator dev; plain `uvicorn --reload` stays IPv4-only for reload
loops). Verified both loopbacks return 200. Not committed to production serving (containers bind
0.0.0.0 behind a proxy) — local-dev convenience only.

## 2026-07-05 — TIME-068 (Jira TIME-66): Refresh Now/Today on tab return (+ pull-to-refresh)

Follow-up to TIME-067: even though the backend now surfaces captured tasks, the Now/Today screens
didn't update after a capture. They load once via SwiftUI `.task { }`, but TabView keeps tab views
mounted so `.task` doesn't re-run on tab switch. Fix: NowView + TodayView now
`.onChange(of: appState.selectedTab)` reload when their tab becomes active (appState.selectedTab
drives the TabView selection), plus `.refreshable` pull-to-refresh on both. Initial `.task` kept for
first appearance. iOS BUILD SUCCEEDED. (No backend change.)

## 2026-07-05 — TIME-067 (Jira TIME-65): Fix day-view task visibility (Today 404 + Now ignores captured tasks)

Two bugs found while using the running app:

### Today tab "Couldn't load today — 404" (iOS)
APIClient built the request URL with `URL.appending(path:)`, which percent-encodes the WHOLE string
as a single path component — so any `?query` (Today sends `/timeline/today?date=YYYY-MM-DD`) turned
into `%3Fdate=...`, producing a non-existent path → 404. This broke EVERY query-param endpoint
(insights history, admin search, etc.), not just Today. Fix: build the URL as
`baseURL.absoluteString + path` so the query survives. (The date was already ISO `yyyy-MM-dd`, so no
format issue.)

### Captured task never appears on Now (backend)
GET /now's candidate set was only scheduled-today + overdue tasks. A freshly captured task has no
scheduled_start and no due_at, so it was neither → never surfaced. Fix: also include unscheduled
pending tasks as "do it whenever" candidates.

### Verification
- Backend: new test_now test (unscheduled captured task → best_task); full suite 307/307 (302 via
  --ignore + 5 referral subset), excl. 2 flaky.
- iOS: BUILD SUCCEEDED. (Full signed-in E2E needs the user's login; the URL fix is a one-line
  construction change verified by build + reasoning.)

## 2026-07-05 — TIME-066 (Jira TIME-64): Fix iOS missing color assets (invisible UI)

### Bug (found while the user tried to sign in on the Simulator)
Almost the entire iOS UI was invisible — the user reported only a "Continue with Apple" button on the
sign-in screen. Root cause: `DesignTokens.Color` references named asset-catalog colors
(`Color("TextPrimary")`, `"Surface"`, `"Background"`, `"AccentColor"`, `"TextSecondary"`,
`"Destructive"`, `"Success"`), but **the project had no asset catalog at all**. Every token color
resolved to an invisible fallback, so all text/surfaces/brand rendered white-on-white; only
hardcoded-black elements (the Apple button) showed.

### Fix
- Created `ios/TimeSense/Assets.xcassets` with a colorset for each token (light + dark variants;
  neutral text/surface palette + indigo accent #4A6CF7), plus an empty `AppIcon.appiconset` (actool
  requires the app-icon set named by ASSETCATALOG_COMPILER_APPICON_NAME).
- Registered the catalog in the TimeSense target's resources (xcodeproj gem).

### Verification
- Simulator build → BUILD SUCCEEDED (first attempt failed on the missing AppIcon set until the empty
  one was added). Installed + launched + screenshotted the sign-in screen: brand header, Continue
  with Apple, Continue with Google, "or" divider, and Continue with Email all now render.

### Lesson (recorded in known_issues.md)
Prior iOS "verification" this session (BUILD SUCCEEDED + app launches to its sign-in screen) did NOT
catch this — the one visible element looked plausible in a screenshot, so "app runs to sign-in" was
mistaken for a healthy UI. **Visual verification must confirm the intended UI actually renders, not
just that the app launches.**

## 2026-07-05 — TIME-057 (Jira TIME-63): App Store and Play Store Prep

Documentation deliverable (no code). Created `docs/launch/`:
- `privacy_policy.md` — complete, publishable privacy policy grounded in the real implementation:
  Firebase auth; all 6 consent types (audio_storage/audio_training/location_tracking/health_data/
  calendar_details/analytics); integrations (Calendar/Slack/Teams/Notion, tokens encrypted at rest
  per TIME-056); LLM/OpenAI processing of captured text; Stripe/StoreKit/Play billing; raw-audio
  opt-in; data export + deletion rights (TIME-055); retention; children; contact. Bracketed
  company/legal details for the user; flagged for legal review.
- `app_store_listing.md` — iOS name/subtitle/promo/description/keywords/what's-new (within Apple
  limits) + App Review notes (demo account, permissions, subscription) + App Privacy nutrition-label
  answers per data type.
- `play_store_listing.md` — Android title/short+full description/category + Play Data Safety form
  answers + content-rating notes.
- `store_assets_checklist.md` — exact icon/screenshot sizes + counts per device class, feature
  graphic, and submission prerequisites the USER must produce.
- `README.md` — index + submission runbook.

Non-goals (the user's steps): actual screenshots/icons/feature-graphics, console data entry + binary
upload, legal review. Verified by review for completeness + consistency with the codebase's data
practices; no tests (docs-only).

## 2026-07-05 — TIME-056 (Jira TIME-62): Security Review and Hardening

### Audit (already secure — documented, unchanged)
- Auth: verify_id_token(check_revoked=True); require_admin on the token claim; /users/me mirrors it.
- Stripe webhook already verifies signatures (construct_event → 400 on bad sig, 503 unconfigured).
- Admin routes all require AdminUser (403 otherwise); privacy delete needs confirm; export redacts tokens.

### New hardening
- **Token encryption at rest** — `app/core/crypto.py`: Fernet `encrypt_token`/`decrypt_token` + an
  `EncryptedString` TypeDecorator (impl=Text → NO migration). Key from settings.token_encryption_key
  or derived from secret_key when unset. `decrypt_token` tolerates legacy plaintext (returns as-is on
  InvalidToken). Applied to access_token/refresh_token on Calendar/Slack/Teams/Notion integrations —
  ciphertext at rest, plaintext through the ORM. Closes the logged 'tokens stored as plain Text' issue.
- **Security headers** — `SecurityHeadersMiddleware`: X-Content-Type-Options nosniff, X-Frame-Options
  DENY, Referrer-Policy no-referrer, X-XSS-Protection 0, CSP default-src 'none', + HSTS in production.
- **Rate limiting** — `app/core/rate_limit.py`: in-process fixed-window RateLimiter keyed by
  (name, auth-token-or-IP); plain async-function dependencies (`capture_rate_limit`,
  `account_delete_rate_limit`) applied to POST /capture (30/min) and DELETE /privacy/account (5/hr);
  429 + Retry-After when exceeded. Single-instance/in-memory (Redis is a follow-up).
- config: token_encryption_key + rate-limit knobs.

### Gotchas
- FastAPI does NOT inject `Request` into a class-instance `__call__` dependency (it treats `request`
  as a required field → 422); exposed the limiters as plain async functions instead.
- Shared in-process limiters accumulate state across tests (same auth token) → added an autouse
  conftest fixture (`_reset_all()`) to reset between tests.

### Verification
- 7 new tests (test_security.py): crypto round-trip + legacy-plaintext tolerance; token ciphertext
  at rest (raw column) vs plaintext via ORM; security headers present; rate limiter blocks at limit +
  is per-caller. Suite 306/306 (excl. 2 flaky). Live backend confirmed emitting the headers. No
  migration (EncryptedString renders as TEXT).

## 2026-07-05 — TIME-055 (Jira TIME-61): Privacy Review and Data Export

Self-service GDPR/CCPA-style data portability + erasure (Phase 14).

### Export
- `PrivacyService.export_data(user_id)` — a `_USER_DATA` registry of (label, model, user-column)
  drives a generic serializer that gathers the user's rows across every user-owned table (incl. the
  differently-named FK columns: InviteCode.created_by_id, ReferralCode.owner_id,
  ReferralConversion.referred_user_id) into a JSON bundle. OAuth `access_token`/`refresh_token` are
  redacted; UUIDs/datetimes are JSON-safe.
- `GET /api/v1/privacy/export` (authed) → the bundle.

### Deletion
- `PrivacyService.delete_account(user_id)` — deletes the User row so DB-level ON DELETE CASCADE
  erases all user_id-owned rows (self-maintaining — future tables auto-covered), explicitly purges
  analytics_events (their FK is SET NULL, which would only anonymize), and deletes the Firebase Auth
  user best-effort (graceful when Firebase is unconfigured, e.g. tests).
- `DELETE /api/v1/privacy/account?confirm=true` (authed) → 204; requires confirm=true (irreversible).

### Test infra
- Enabled SQLite FK enforcement in `tests/conftest.py` (`PRAGMA foreign_keys=ON` via a connect
  listener) so ON DELETE CASCADE is exercised like Postgres. Verified the whole suite still passes
  with it on (287 pre-existing + 7 new).

### Verification
- 7 new tests (test_privacy.py): export includes data + redacts tokens; delete erases + cascades;
  requires confirm (400 otherwise); only affects own data; both require auth. Suite 299/299 (excl. 2
  flaky).
- Real-Postgres round-trip: created a user+task, exported (task present, token redacted), deleted →
  user row gone + tasks cascaded to 0.

### Deferred (Non-Goal)
- Per-consent-type revocation cleanup (e.g. revoking health_data auto-purging sleep data) — a
  separate follow-up noted since the consent ticket. This ticket is full-account export + deletion.

## 2026-07-05 — TIME-054 (Jira TIME-60): Error Monitoring and Analytics (backend) — starts Phase 14

Phase 13 (Integrations Expansion, TIME-049–053) is complete; this is the first Phase 14 (Beta
Hardening & Launch Readiness) ticket.

### Monitoring
- `app/core/monitoring.py` — Sentry-optional: `init_monitoring()` initializes Sentry only when
  `settings.sentry_dsn` is set AND sentry-sdk imports; else a clean no-op (graceful pattern).
  `capture_exception(exc, context)` delegates or no-ops; never raises. `send_default_pii=False`,
  `traces_sample_rate=0`.
- Wired into `main.py` lifespan (`init_monitoring()`) and `app/core/errors.py` (the 500 handler +
  a new catch-all Exception handler both call `capture_exception` with path/method context).
- `config.sentry_dsn` (default ""); `sentry-sdk[fastapi]==2.19.2` added to requirements (imported
  lazily inside the functions, so tests run without it installed).

### Analytics (privacy-respecting)
- `AnalyticsEvent` model (user_id nullable FK, event_name, properties JSON text) + migration
  `q7r8s9t0u1v2`; `AnalyticsRepository` (create, counts_by_event).
- `AnalyticsService.track(event_name, user_id=None, properties=None)` — records a user-attributed
  event ONLY if that user granted the existing **`analytics` consent** (ConsentRepository); system
  events (user_id None) record without a check; never raises (best-effort, rides along the request).
- Emits `task_captured` from `POST /api/v1/capture` (properties={source}).
- `GET /api/v1/admin/analytics` (admin-gated) → per-event counts + total.

### Verification
- 9 new tests (test_monitoring_analytics.py): monitoring no-op/safe-capture; analytics
  records-with-consent / skips-without / system-event; capture emits (and skips without consent);
  admin counts + 403. Full suite 292/292 (287 via --ignore + 5 referral subset), excl. 2 flaky.
- Single alembic head; migration applies cleanly to the live Postgres.

### Deferred (Non-Goal)
- Client-side analytics (iOS Analytics.swift / Android analytics/) — follow-up ticket; this
  establishes the backend pipeline + event schema + consent gating first.

## 2026-07-05 — TIME-065 (Jira TIME-59): Sync DB user role from the Firebase token claim

### Why
Authorization had two independent role sources: backend admin endpoints gate on the Firebase custom
claim (require_admin → token role), but GET /users/me returns the DB user.role and the web dashboard
gates on that. Granting admin took two steps (set the claim AND update the DB row) — surfaced when
setting up the first admin.

### Change
- `UserService.get_or_create_user` gains an optional `role` param: on an existing user, if the
  passed role differs from the stored one, update it (persisted by the request's session commit —
  get_db commits on success); on create, pass it through to `repo.create` (which already accepted
  `role`). The claim is the source of truth — a cache refresh, including downgrades if the claim is
  removed.
- `GET /users/me` passes `current_user.role` (the token claim) into get_or_create_user, so the DB
  role mirrors the claim on the call the web makes.
- require_admin unchanged (still reads the token claim; the DB now just mirrors it).

### Tests / Verification
- 2 new tests in test_users.py: a fresh user with an admin claim returns role=admin from /users/me;
  granting then removing the claim downgrades the DB role. Full suite 283/283 (excl. 2 flaky).
- Now granting admin is one step (set the Firebase claim); the DB syncs on next /users/me.

## 2026-07-05 — TIME-064 (Jira TIME-58): Load .env from repo root regardless of CWD

### Bug
Running the documented `cd backend && uvicorn app.main:app` loaded NO env: config.py used
`env_file=".env"` (relative to CWD), so it looked for `backend/.env`, but the real `.env` is at the
repo root. It silently fell back to defaults — the default `DATABASE_URL` happens to match local
Postgres (so the DB worked), but `firebase_project_id`/`firebase_service_account_json` were empty,
so real token verification failed at runtime with "A project ID is required to access the auth
service." Found while bringing the full stack up locally for the user.

### Fix
- config.py: `env_file=(str(_ROOT_ENV), ".env")` where `_ROOT_ENV = Path(__file__).resolve().
  parents[3] / ".env"` — resolves the repo-root .env by absolute path (found from any CWD), with a
  CWD-relative `.env` kept as an optional local override. Missing files are ignored by pydantic; in
  Docker, injected env vars still take precedence.
- Removed the temporary `backend/.env` symlink used during bring-up — the fix stands on its own.

### Verification
- From `backend/` with no symlink: `settings.firebase_project_id == "timesense-eb7ec"`, service
  account present. Backend restarted via `cd backend && uvicorn` → health 200, `get_firebase_app().
  project_id == "timesense-eb7ec"`, and real token verification works (the user's admin dashboard
  loads end-to-end).
- Full suite 281/281 (excl. 2 flaky) — loading the real .env doesn't affect tests (conftest
  overrides the DB via SQLite + dependency injection and mocks verify_id_token).

## 2026-07-05 — TIME-063 (Jira TIME-57): Fix Alembic migration ordering (tasks before recommendation_feedback)

### Bug
Bringing up a real local Postgres for the running app, `alembic upgrade head` failed on a fresh DB
with `relation "tasks" does not exist` at the `add_recommendation_feedback` migration. Root cause:
`g7h8i9j0k1l2` (recommendation_feedback, FK → tasks.id) and `a1b2c3d4e5f7` (tasks) were **parallel
sibling branches** off the same parent `f6a7b8c9d0e1` (an artifact of the earlier 4-head merge).
Alembic linearized the siblings with feedback *before* tasks, so the FK target didn't exist yet.
Masked from the test suite because tests build the schema from models via `Base.metadata.create_all`,
not by running migrations — so no test ever exercised the migration order.

### Fix
- `g7h8i9j0k1l2` down_revision: `f6a7b8c9d0e1` → `a1b2c3d4e5f7` (tasks now guaranteed first).
- Merge migration `e55970716568` down_revision tuple: dropped `a1b2c3d4e5f7` (no longer a head),
  now `('a7b8c9d0e1f2','b8c9d0e1f2a3','g7h8i9j0k1l2')`.

### Verification
- `alembic heads` → single head `p6q7r8s9t0u1`.
- Dropped + recreated an empty Postgres `timesense` DB and ran `alembic upgrade head` → completes
  end-to-end (31 tables; tasks/recommendation_feedback/users all present). Backend then boots and
  `GET /api/v1/health` → 200.
- Full suite 281/281 (excl. 2 flaky) — unaffected (uses create_all).
- Safe change: no DB had ever successfully migrated from scratch in the old order, so there's no
  already-migrated alembic_version graph to disrupt.

## 2026-07-05 — TIME-062 (Jira TIME-56): Client Firebase Config (iOS + Android)

Interactive session with the user, who registered the iOS/Android/web apps in the real Firebase
project **timesense-eb7ec** and supplied the config files. Wired the iOS + Android clients to real
Firebase (web pending the user's apiKey/appId).

### iOS
- Added the **firebase-ios-sdk** Swift Package and linked **FirebaseAuth + FirebaseCore** to the
  TimeSense target (done programmatically via the xcodeproj gem — the user was blocked on Xcode's
  product-selection dialog; the package *reference* had been added by an earlier Xcode attempt but
  no products were linked, which is why they never appeared in the target's "+" list).
- **Pinned Firebase to 11.x** (resolved to **11.15.0**): the reference Xcode created defaulted to
  12.15.0, which requires Swift tools 6.1 — newer than this Xcode 16.0 / Swift 6.0. Changed the
  requirement to `upToNextMajorVersion 11.0.0`.
- Added the **GoogleSignIn-iOS** package (8.x) and linked **GoogleSignIn** — the real AuthService
  (previously never compiled, hidden behind `#if canImport(FirebaseAuth)`) imports GoogleSignIn for
  its `signInWithGoogle`; the first build after linking Firebase surfaced `no such module
  'GoogleSignIn'`.
- Added **GoogleService-Info.plist** to the app target (project_id timesense-eb7ec, bundle id
  com.aetheranalytics.timesense) — **gitignored, NOT committed** (repo convention; each dev supplies
  their own).

### Android
- Replaced the placeholder `android/app/google-services.json` (was project_id
  "timesense-placeholder") with the user's real one (project timesense-eb7ec). The
  com.google.gms.google-services plugin + firebase-auth deps were already wired (TIME-018-era).

### Repo hygiene
- Committed the reproducible bits: `project.pbxproj` (SPM package refs + product links + plist file
  ref) and `Package.resolved` (pins Firebase 11.15.0, GoogleSignIn, gRPC, abseil, …).
- Added depth-agnostic `.gitignore` rules `xcuserdata/` and `.swiftpm/` — the existing
  `*.xcodeproj/xcuserdata/` pattern is root-anchored and missed the nested `ios/...` dirs.

### Verification
- `xcodebuild -resolvePackageDependencies` → resolved Firebase 11.15.0 + full dep graph
- Simulator build (`-scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'
  CODE_SIGNING_ALLOWED=NO`) → **BUILD SUCCEEDED** — the real FirebaseAuth/GoogleSignIn AuthService
  now compiles
- Booted iPhone 16 sim, installed + launched → app runs (status 0), `FirebaseApp.configure()` runs
  against the real plist without crashing
- Remaining user steps: enable sign-in providers (Apple/Google) in the console; run on a device for
  real interactive sign-in; web/.env.local still needs the web apiKey/appId

## 2026-07-05 — TIME-053 (Jira TIME-55): Google Assistant Integration

### Created
- `backend/app/integrations/google_assistant.py` — Dialogflow fulfillment: `parse_intent(body)`
  (reads queryResult.intent.displayName), `fulfillment_response(text)` (builds the Dialogflow
  WebhookResponse), and `GoogleAssistantService.handle(intent, user_id)` dispatching the same 5
  actions as the iOS App Intents (TIME-052): WhatToDoNext, StartFocus, LogLunch, MarkDone, ReplanDay.
  Intent name matching is case/space-insensitive (`_normalize`). Best-task selection reuses the /now
  logic (TaskRepository + UsableTimeService + TaskScorer)
- `backend/app/api/v1/assistant.py` — POST /api/v1/assistant/webhook, gated on the existing Firebase
  CurrentUser (the account-linked identity stand-in); returns the Dialogflow fulfillment JSON
- `backend/tests/test_google_assistant.py` — 10 tests (each intent's text + side effects: lunch
  logged, best task → done; unknown-intent fallback; no-tasks case; auth required)

### Modified
- `backend/app/api/v1/__init__.py` — register the assistant router

### Design notes
- Backend-only, matching the ticket's stated file (`backend/app/integrations/google_assistant.py`)
  and scope ("Actions on Google / Dialogflow integration"). The on-device shortcut surface was the
  iOS App Intents work (TIME-052); this is the Assistant/Dialogflow backend counterpart, exposing
  the identical 5 actions.
- ReplanDay does NOT headlessly replan — it returns "open the app to approve" (replans require in-app
  approval, same rule as everywhere else).
- Honest scope limits (Non-Goals): Google shut down conversational Actions on Google Assistant in
  June 2023, so this implements the Dialogflow-webhook *contract* (request/response shapes +
  intent→action mapping), verifiable by unit tests, not a live Assistant round-trip. Real Actions-
  on-Google account linking (which would supply the user identity) is out of scope; the webhook is
  gated on the Firebase token as the account-linked stand-in.
- 10 new tests; full suite 281/281 (excluding 2 known-flaky Stripe tests).

## 2026-07-05 — TIME-061 (Jira TIME-54): Backend Real Firebase Token Verification

### What changed
- `app/core/firebase.py` — extracted `_load_service_account(raw) -> dict | None` and made
  `init_firebase()` use it. The .env's FIREBASE_SERVICE_ACCOUNT_JSON is real (project
  timesense-eb7ec) but stored single-line with every newline (structural + private_key) flattened
  to literal `\n`, so the old `json.loads(raw)` failed → the Admin SDK never initialized → real
  auth was never actually exercised (tests always mock verify_id_token). The helper tries compact
  `json.loads` first, then falls back to `json.loads(raw.replace("\\n","\n"), strict=False)` (the
  `strict=False` tolerates the real newlines that end up inside the private_key string), returning
  None on empty/garbage so the existing ADC/projectId fallback still applies.
- `tests/test_firebase_init.py` (new) — 4 unit tests for the helper using a FABRICATED service
  account (never the real key): compact JSON parses; a pretty-printed-then-flattened-to-literal-`\n`
  string parses and recovers a well-formed PEM private_key; empty/`{}`/blank → None; garbage → None.

### Verification
- `pytest tests/test_firebase_init.py` → 4/4. Full suite 271/271 (excluding 2 known-flaky Stripe).
- Out-of-band (not in the committed test, to avoid the real key touching the repo): ran the real
  `init_firebase()` with the actual .env value → logs "Firebase Admin SDK initialized with service
  account for project: timesense-eb7ec" and `get_firebase_app().project_id == "timesense-eb7ec"`.
  Before this fix it silently warned "Firebase init failed". `get_current_user` already calls
  `firebase_admin.auth.verify_id_token`, so the backend now verifies REAL client ID tokens.

### Scope boundary (what's still needed for client end-to-end)
- The .env has only the BACKEND service account. Real sign-in from a client additionally needs
  per-app CLIENT config, which is NOT in .env and must be downloaded/registered in the Firebase
  console for project timesense-eb7ec: iOS `GoogleService-Info.plist`, Android
  `google-services.json`, and web `NEXT_PUBLIC_FIREBASE_API_KEY`/`APP_ID`/`AUTH_DOMAIN`. Those are
  separate follow-ups (and iOS also needs the Firebase SDK resolved via Xcode SPM — a standing gap).
- The real service account private key stays only in .env (gitignored) — never committed.

## 2026-07-05 — TIME-060 (Jira TIME-53): iOS HealthKit Sleep/Wake Read Integration

### Created
- `ios/TimeSense/Core/Health/HealthService.swift` — HKHealthStore wrapper behind
  `#if canImport(HealthKit)` (real branch compiles on iOS; `#else` stub mirrors AuthService's
  Firebase-stub pattern). `connectAndSync()` requests read auth for sleepAnalysis, reads the most
  recent sleep window (earliest asleep start + latest asleep end = wake, grouped within a 6h window
  using `HKCategoryValueSleepAnalysis.allAsleepValues`), and POSTs {wake_time, sleep_start,
  source:"healthkit"} to /api/v1/sleep/events via APIClient. Read-only — never writes to HealthKit.
  Publishes a HealthConnectState (idle/requesting/syncing/synced/noData/unavailable/error)

### Modified
- `ios/TimeSense/TimeSense.entitlements` — added com.apple.developer.healthkit (+ empty
  healthkit.access array)
- `ios/TimeSense.xcodeproj/project.pbxproj` — registered HealthService.swift; added
  INFOPLIST_KEY_NSHealthShareUsageDescription (project uses GENERATE_INFOPLIST_FILE) — read-only
  copy, no NSHealthUpdate since TimeSense only reads
- `ios/TimeSense/Features/Settings/SettingsView.swift` — a "Connect Apple Health" row (Button →
  HealthService.connectAndSync()) with inline status (spinner/checkmark/no-data/error)

### Design notes
- Completes the sleep/wake feature's mobile half (backend contract shipped in TIME-042). No backend
  changes — POST /api/v1/sleep/events already exists (gates on health_data consent, proposes a
  morning replan on a late wake); the response's replan_suggested is surfaced in the sync state.
- Unblocked by two things resolved this session: the Simulator (HealthKit runs there) and TIME-059's
  real Apple signing (the healthkit entitlement can now provision on device).

### Verification
- Simulator build → **BUILD SUCCEEDED**, zero new warnings
- Confirmed HealthKit is really linked (not the stub): the Debug build's real code lives in
  `TimeSense.debug.dylib` (Xcode debug-dylib split — the launcher executable itself has no
  frameworks), and `otool -L` on the dylib shows `HealthKit.framework`, `nm` shows
  `_OBJC_CLASS_$_HKHealthStore` referenced, and `HKCategoryValueSleepAnalysis`/`HealthService`
  strings are present. `canImport(HealthKit)` verified true for the iphonesimulator SDK
- Built `Info.plist` contains the NSHealthShareUsageDescription
- Booted iPhone 16 sim, installed + launched under the NEW bundle id **com.aetheranalytics.timesense**
  (also validates TIME-059's rename end-to-end) → app runs cleanly (launchctl status 0), no crash
  from the HealthKit addition
- Not doable headlessly: the live HealthKit authorization prompt + real sleep data + on-device run —
  those are inherently device/interactive and are the user's step (register a device UDID, run from
  their Xcode). HealthKit auth can also be exercised in the Simulator interactively but not via CLI.

## 2026-07-05 — TIME-059 (Jira TIME-52): iOS Real Apple Signing Configuration

### What changed
- Set `DEVELOPMENT_TEAM = WB5NV894N5` (the user's real Apple Developer Team, from .env) on both
  the TimeSense app and TimeSenseWidgetExtension targets (Debug + Release), via the xcodeproj gem
- Renamed `PRODUCT_BUNDLE_IDENTIFIER`: app `com.timesense.app` → `com.aetheranalytics.timesense`;
  widget `com.timesense.app.TimeSenseWidget` → `com.aetheranalytics.timesense.TimeSenseWidget`
  (both configs). `com.aetheranalytics.timesense` is the user's registered App ID (from .env
  APPLE_BUNDLE_ID)
- Renamed the shared App Group `group.com.timesense.app` → `group.com.aetheranalytics.timesense`
  in all three places that must agree: `TimeSense.entitlements`, `TimeSenseWidget.entitlements`,
  and `WidgetSnapshot.appGroupID` (the widget reads the app's snapshot via this group)

### Files changed
- `ios/TimeSense.xcodeproj/project.pbxproj`, `ios/TimeSense/TimeSense.entitlements`,
  `ios/TimeSenseWidget/TimeSenseWidget.entitlements`, `ios/TimeSense/Core/Widgets/WidgetSnapshot.swift`

### Verification
- Simulator build: `xcodebuild -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone
  16' CODE_SIGNING_ALLOWED=NO` → **BUILD SUCCEEDED** after the rename
- **Real signed-device build (best-effort, per the ticket):** ran `xcodebuild -destination
  'generic/platform=iOS' -allowProvisioningUpdates -authenticationKey{ID,IssuerID,Path}` with the
  user's App Store Connect API key (materialized to a temp .p8 in scratchpad — the .env value is a
  single line with literal `\n` escapes, so it had to be decoded to real newlines; validated with
  `openssl pkey`; the temp key was deleted after use and never committed). Result: the key
  **authenticated with Apple successfully** and signing got all the way to provisioning-profile
  generation, failing only with: *"Your team has no devices from which to generate a provisioning
  profile. Connect a device… No profiles for 'com.aetheranalytics.timesense' were found."* Apple
  raised NO complaint about the team, bundle IDs, app group, or certificate — meaning the project
  is now correctly configured to sign against the real account; the sole remaining step is
  registering a device UDID (i.e. the user plugging in their iPhone via their own Xcode). This is
  the exact "needs physical hardware" boundary and is expected — a *development* profile requires a
  registered device, and there's none in this headless environment.
- Note: automatic signing may have registered the two App IDs in the user's account during the
  attempt (benign — they need to exist anyway); it failed before creating a profile.

## 2026-07-05 — TIME-052 (Jira TIME-51): Siri Shortcuts / App Intents

### Created
- `ios/TimeSense/Intents/TimeSenseAppIntents.swift` — 5 AppIntents:
  - WhatToDoNext (GET /api/v1/now → spoken best task + usable minutes)
  - LogLunch (POST /api/v1/meals lunch/eaten)
  - StartFocus (GET /now → "Focus on {best task}")
  - MarkDone (GET /now → PATCH /api/v1/tasks/{bestTaskId} status=done)
  - ReplanDay (openAppWhenRun=true — replans require in-app approval, never headless)
- `ios/TimeSense/Intents/TimeSenseShortcuts.swift` — AppShortcutsProvider exposing each intent
  with natural, \(.applicationName)-prefixed Siri phrases + SF Symbols

### Modified
- `ios/TimeSense.xcodeproj/project.pbxproj` — registered the Intents group (via the xcodeproj gem)
- `scripts/create_jira_tickets.py` — added the TIME-052 ticket definition

### Design notes
- Intents call the app's single network path (APIClient.shared), reuse the existing
  NowContext/NowTask decodables, and define minimal inline request/response types — no new
  networking layer. Read/simple-write intents run headless; ReplanDay opens the app because the
  product rule "replans require approval" means it must be reviewed in-app, not auto-applied.
- Unauthenticated intent runs surface a friendly "open TimeSense and sign in" dialog rather than a
  raw error (via a shared friendlyMessage() mapping APIError.unauthorized).
- **Environment unblocked:** the user installed an iOS Simulator runtime (iOS 18.0), resolving the
  long-standing "no Simulator runtimes" gap (known_issues.md, now marked RESOLVED). This ticket is
  therefore verified to a higher bar than any prior iOS ticket:
  - `xcodebuild -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'
    CODE_SIGNING_ALLOWED=NO` → BUILD SUCCEEDED, zero new warnings
  - Booted iPhone 16 sim, `simctl install` + `launch` → app runs to its sign-in screen without
    crashing (screenshot captured); confirms it's at the auth gate (expected — real Firebase still
    a placeholder, so headless intent→backend round-trips can't be exercised end-to-end yet)
  - All 5 intents present in the built `TimeSense.app/Metadata.appintents/extract.actionsdata`
    bundle — concrete proof the App Intents extracted/registered (earlier builds logged "Extracted
    no relevant App Intents symbols")
- Real *Siri voice* invocation is a real-device follow-up (Siri isn't in the Simulator); the
  Shortcuts-app registration path is what the Simulator verifies.

## 2026-07-05 — TIME-051 (Jira TIME-50): Notion Integration

### Created
- `backend/app/integrations/task_source_base.py` — **new** TaskSourceProvider ABC + SourceTask
  dataclass. Deliberately separate from MessageSourceProvider: a task source (Notion, later
  Todoist/Things) holds already-structured task-like items, so no LLM detection is needed —
  structured field extraction does the work
- `backend/app/integrations/notion_source.py` — NotionTaskSource querying the Notion API
  POST /v1/databases/{id}/query; `_extract_title` (from the title-type property) and `_extract_due`
  (first date-type property) pull structured fields, no LLM
- `backend/app/models/notion.py` — NotionIntegration (token) + NotionImportItem (import queue,
  status pending|imported|dismissed, carries title/notes/due_at)
- `backend/migrations/versions/p6q7r8s9t0u1_add_notion_integration.py` — both tables
- `backend/app/repositories/notion_repository.py`, `schemas/notion.py`, `services/notion_service.py`
  (connect/disconnect/scan_database/list_pending/import_item/dismiss + NotionNotConnected),
  `api/v1/notion.py`
- `backend/tests/test_notion.py` — 15 tests (5 real property-extraction unit tests + scan/import/
  dismiss + premium gate + isolation)

### Modified
- `backend/app/core/config.py` — notion_client_id/secret + notion_version ("2022-06-28")
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/models
- `backend/app/schemas/task.py` — added "notion" to the TaskSource literal

### Design notes
- Per the user's direction, Notion got its OWN abstraction rather than being bent into the
  MessageSourceProvider shape. Justification: a Notion database row is already a discrete task, so
  the honest operation is structured title/due extraction + explicit user import — not LLM sifting
  of chat noise. This is why there's no ActionItemDetectionService here. The framing is
  import/dismiss (not detect/confirm) to reflect it.
- Same approval-gate discipline as every other external signal: scan_database() creates *pending*
  NotionImportItem rows only; import_item() is the single path that creates a Task (source="notion",
  carrying the extracted due_at). Nothing auto-imports.
- Structured extraction handles Notion's property model: the title lives in whichever property has
  type=="title" (name varies per database); due comes from the first date-type property. Only these
  two fields — richer per-database field mapping is an explicit Non-Goal.
- No real Notion OAuth app (empty NOTION_CLIENT_ID/SECRET) — mobile client posts the token to
  /notion/connect like the other integrations; no server-side OAuth callback. Token plain Text,
  same cross-integration encryption deferral (known_issues.md).
- 15 new tests; full suite 262/262 (excluding 2 known-flaky Stripe tests). Single alembic head,
  both tables compile offline.

## 2026-07-05 — TIME-050 (Jira TIME-49): Microsoft Teams Integration

### Created
- `backend/app/services/action_item_detection.py` — shared, source-neutral
  ActionItemDetectionService (extracted from SlackDetectionService); one copy of the LLM
  action-item-detection prompt now serves both Slack and Teams
- `backend/app/integrations/teams_source.py` — TeamsMessageSource(MessageSourceProvider) reading
  Microsoft Graph /chats/{id}/messages, stripping the HTML message body to plain text
- `backend/app/models/teams.py` — TeamsIntegration (token) + TeamsActionItem (approval queue),
  parallel to the Slack models
- `backend/migrations/versions/o5p6q7r8s9t0_add_teams_integration.py` — both tables
- `backend/app/repositories/teams_repository.py`, `schemas/teams.py`, `services/teams_service.py`
  (connect/disconnect/scan_conversation/confirm/reject + TeamsNotConnected), `api/v1/teams.py`
- `backend/tests/test_teams.py` — 12 tests mirroring test_slack.py

### Modified
- `backend/app/services/slack_service.py` — now imports the shared ActionItemDetectionService;
  keeps `SlackDetectionService` as a backward-compatible alias + re-exports Detection, so the
  merged test_slack.py imports stay green (verified: 14/14 still pass)
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/models
- `backend/app/schemas/task.py` — added "teams" to the TaskSource literal

### Design notes
- Teams is the same shape as Slack, so per the rule of three I generalized the one genuinely
  shared piece (LLM detection) into ActionItemDetectionService and kept the per-source
  models/repos/service/schemas/api parallel — matching the repo's own per-feature-table precedent
  (commute/meal/sleep are similarly parallel). Unifying the Slack+Teams tables into one
  source-tagged message-source schema is deliberately deferred to a third source (decision_log.md +
  the ticket's Non-Goals) to avoid a churny migration of just-merged Slack tables.
- Same approval gate as Slack: scan_conversation() creates *pending* TeamsActionItem rows only;
  confirm() is the single path that creates a Task (source="teams", links created_task_id).
- Reuses the MessageSourceProvider ABC built in TIME-049 — TeamsMessageSource is a new provider,
  not a re-architecture.
- No real Azure AD app: MICROSOFT_CLIENT_ID/SECRET are empty placeholders (present since the
  Phase-6 Outlook scaffold). Mobile client POSTs the Graph token to /teams/connect like
  /slack/connect — no server-side OAuth callback / Graph change-notifications in this ticket.
- Token stored as plain Text, matching Slack/Calendar — cross-integration encryption still the
  same deferred item (known_issues.md).
- 12 new tests (Teams) + Slack's 14 still green; full suite 247/247 (excluding 2 known-flaky Stripe
  tests). Single alembic head; both new tables compile offline.

## 2026-07-05 — TIME-049 (Jira TIME-48): Slack Integration

### Created
- `backend/app/integrations/message_source_base.py` — MessageSourceProvider ABC + SourceMessage
  dataclass (a read-only chat/comms source abstraction, for Slack now + Teams later)
- `backend/app/integrations/slack_source.py` — SlackMessageSource calling Slack's
  conversations.history Web API (handles Slack's `{"ok": false}` 200-response quirk)
- `backend/app/models/slack.py` — SlackIntegration (token storage, same shape as
  CalendarIntegration) + SlackActionItem (approval queue, mirrors PendingCalendarAction)
- `backend/migrations/versions/n4o5p6q7r8s9_add_slack_integration.py` — both tables
- `backend/app/repositories/slack_repository.py` — SlackIntegrationRepository +
  SlackActionItemRepository (incl. exists_for_message for scan-dedup)
- `backend/app/schemas/slack.py`, `backend/app/services/slack_service.py`,
  `backend/app/api/v1/slack.py`
- `backend/tests/test_slack.py` — 14 tests (LLM detection unit tests + scan/confirm/reject API
  tests + premium gate + isolation)

### Modified
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/models
- `backend/app/schemas/task.py` — added "slack" to the TaskSource literal

### Design notes
- The approval gate is the whole point: `scan_channel()` reads messages, runs LLM detection, and
  creates *pending* SlackActionItem rows — NEVER Tasks. `confirm()` is the single path that turns a
  detected item into a Task (source="slack", links created_task_id back onto the item). This mirrors
  the calendar request→approve pattern exactly, satisfying the product's "never auto-create from
  external signals without approval" rule.
- `SlackDetectionService` is split out from `SlackService` so the LLM detection logic is unit-
  testable in isolation. It reuses LLMGateway and degrades gracefully (is_action_item=False) on any
  LLM error — identical fallback discipline to CaptureService.
- Followed the repo's actual flat-file integration convention (calendar_base.py / google_calendar.py)
  rather than the integration-provider-pattern skill's idealized `slack/` subdirectory layout —
  repo is source of truth.
- No real Slack app: SLACK_CLIENT_ID/SECRET/SIGNING_SECRET are empty placeholders in .env (already
  present from an earlier scaffold). The mobile client does OAuth and POSTs the token to
  /slack/connect, exactly like /calendar/connect — no server-side OAuth callback, no Events API /
  signature verification in this ticket (slack_signing_secret stays unused).
- Token stored as plain Text, matching how CalendarIntegration already stores tokens — a cross-
  integration encryption-at-rest pass is separate future work (known_issues.md).
- 14 new tests; full suite 235/235 (excluding 2 known-flaky Stripe tests). `alembic heads` single
  head; offline `--sql` compiles both tables cleanly.

## 2026-07-05 — TIME-048 (Jira TIME-47): Admin Dashboard Foundation (Web)

### Created — web/ (bootstrapped from scratch; first ticket to touch this platform)
- Next.js 16 (App Router) + TypeScript + Tailwind 4, scaffolded via `create-next-app` then
  customized (`npm install firebase`, minimal landing page, real README)
- `lib/firebase.ts` — Firebase app init + a **lazy** `getFirebaseAuth()` getter. `getAuth()`
  validates the API key eagerly and throws `auth/invalid-api-key` immediately when it's empty —
  even during `next build`'s static prerendering of `/_not-found` — so auth is never constructed
  at module-eval time, only on first actual use at runtime, guarded by `isFirebaseConfigured`
- `lib/auth.tsx` — auth context/hook (sign in, sign out, get ID token, current user)
- `lib/api.ts` — `apiFetch()` + `useAdminApi()` hook attaching the Firebase ID token as a Bearer
  header, mirroring ApiClient.swift/ApiClient.kt
- `app/admin/layout.tsx` — role gate (checks GET /api/v1/users/me `role` client-side for UX; the
  real security boundary stays server-side via the existing `AdminUser` FastAPI dependency) + nav
- `app/admin/page.tsx` (metrics + integration status), `users/page.tsx` (search+pagination),
  `invites/page.tsx` (list/create/disable codes + waitlist), `subscriptions/page.tsx`,
  `feedback/page.tsx`
- `.env.local.example` documenting the Firebase + API base URL env vars (none configured — same
  placeholder gap as iOS/Android, open_questions.md)

### Created/Modified — backend (extending admin.py beyond the ticket sequence's literal scope)
- `backend/app/schemas/admin.py` — AdminSubscriptionSummary/ListResponse, AdminFeedbackSummary/
  ListResponse, AdminIntegrationProviderStatus/StatusResponse, AdminMetricsResponse
- `backend/app/api/v1/admin.py` — new GET /admin/subscriptions, /admin/feedback,
  /admin/integrations, /admin/metrics, /admin/waitlist (all AdminUser-gated); extended
  GET /admin/users with a `search` param and fixed `total` (was hardcoded to `len(users)`)
- Repository additions: `user_repository.list_all(search)`/`count_all()`,
  `subscription_repository.list_all()`/`count_by_status()`,
  `recommendation_feedback_repository.list_recent_across_users()` (joins User+Task for display),
  `calendar_repository.count_by_provider()`, `invite_repository.count_waiting()`/`count_active()`
- `backend/tests/test_admin.py` — extended the existing 6-test file to 17 (11 new), covering each
  new/changed endpoint's data correctness + 403-without-admin-role + cross-aggregation correctness

### Design notes
- The ticket sequence's scope line ("Files: web/app/admin/") implied the backend already exposed
  everything needed. In reality only user-listing and invite-code management existed as admin
  endpoints — subscriptions/feedback/integrations/metrics/waitlist had none. Confirmed with the
  user before proceeding: build the missing endpoints rather than ship a dashboard with dead ends.
- Discovered mid-implementation that "view the waitlist" (already committed to in scope) also had
  no backend endpoint — added `GET /api/v1/admin/waitlist` (reusing the existing `WaitlistEntryOut`
  schema, no new schema needed) rather than silently dropping that part of the scope.
- A real, non-lint-blocking discovery: this Next.js/React version's ESLint config enforces a strict
  `react-hooks/set-state-in-effect` rule that flags ANY synchronous `setState` call in an effect
  body that isn't immediately followed by async work in the same branch — including the extremely
  common "setLoading(true) at the top of a data-fetching effect" pattern once other early-return
  branches exist nearby. Fixed by deriving loading state from data (`data === null && error ===
  null`) instead of a separate boolean, per React's own "you might not need an effect" guidance —
  cleaner code, not a workaround. Also fixed a latent bug this surfaced: `error` was never reset
  on a subsequent successful fetch, so a transient failure would blank the UI's error message
  permanently even after later successful loads.
- `npm audit` flags a moderate postcss XSS advisory transitively bundled inside this Next.js
  version; `npm audit fix --force` would downgrade Next.js 16→9 (a completely wrong "fix" from an
  audit database that hasn't caught up with this very new release) — left alone, not actioned.

## 2026-07-05 — TIME-047 (Jira TIME-46): Learned Assumptions Settings

### Created
- `ios/TimeSense/Features/Settings/LearnedAssumptionsViewModel.swift` — GET /api/v1/routines,
  PATCH per routine_type, updates the in-memory list in place on success
- `ios/TimeSense/Features/Settings/LearnedAssumptionsView.swift` — list of the 6 routine types
  with friendly labels + formatted time ranges + an "Edited" badge when is_customized; tapping a
  row opens a sheet with two `DatePicker(.hourAndMinute)` fields (start/end) + Save/Cancel
- `android/.../features/settings/LearnedAssumptionsViewModel.kt` — same two endpoints, OkHttp
- `android/.../features/settings/LearnedAssumptionsScreen.kt` — same list shape; editing uses a
  Material3 `TimePicker` inside an `AlertDialog`, with Starts/Ends toggle buttons since Material3
  doesn't have a two-field time-range picker built in

### Modified
- `ios/TimeSense/Features/Settings/SettingsView.swift` — added a "Learned Assumptions"
  `NavigationLink` row to the Preferences section; extracted `SettingsRowLabel` (icon+title, no
  chevron) from the existing `SettingsRow` so the real `NavigationLink` doesn't double up its own
  disclosure indicator with a second manually-drawn one
- `ios/TimeSense.xcodeproj/project.pbxproj` — registered the two new Swift files (xcodeproj gem)
- `android/.../features/settings/SettingsScreen.kt` — `SettingsItem` gained an `onClick` param
  (previously a no-op `.clickable {}` on every row); added the new row wired to it
- `android/.../navigation/MainNavHost.kt` — registered `"learned_assumptions"` as a new destination
  in the existing single-NavHost tab structure, with `SettingsScreen` now taking an
  `onLearnedAssumptionsClick` callback rather than a `NavController` directly

### Design notes
- Pure UI ticket, no backend changes — GET/PATCH /api/v1/routines (TIME-039) already supported
  everything needed.
- Android has no built-in Material3 "time range" picker, so the edit dialog reuses one
  `TimePicker` with Starts/Ends toggle buttons rather than pulling in a third-party dependency for
  a two-field picker — a deliberate scope-minimizing choice.
- Verified with `xcodebuild -target TimeSense -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO` (BUILD
  SUCCEEDED, zero new warnings) and `./gradlew assembleDebug && ./gradlew test` (BUILD SUCCESSFUL,
  Android-Studio-bundled JBR as JAVA_HOME per known_issues.md).

## 2026-07-05 — TIME-046 (Jira TIME-45): Weekly Insights Generation

### Created
- `backend/app/models/insight.py` — WeeklyInsight model (unique on user_id+week_start)
- `backend/migrations/versions/m3n4o5p6q7r8_add_weekly_insights.py` — weekly_insights table
- `backend/app/repositories/insight_repository.py` — get_by_week/create/list_recent
- `backend/app/schemas/insight.py` — WeeklyInsightResponse
- `backend/app/services/insights_service.py` — InsightsService.get_or_generate_for_week()
  aggregates from 5 existing tables (Task, RecommendationFeedback, MealEvent, SleepWakeEvent,
  CommuteEvent) over a Monday-Sunday range, then calls LLMGateway for a 2-3 sentence summary
  with a templated fallback — identical pattern to RecommendationService._explain(). Idempotent:
  once a week is generated it's returned as-is, never silently recomputed.
- `backend/app/api/v1/insights.py` — GET /insights/weekly (generates the most recently completed
  week on first call), GET /insights/history?limit=8 — both Premium-gated via the existing
  PremiumUser dependency
- `backend/app/workers/insights_tasks.py` — one Celery task generating the just-completed week
  for every active user, scheduled Monday 5am UTC; untested in this environment (no Redis/Docker),
  same precedent as notification_tasks.py
- `backend/tests/test_insights.py` — 17 tests (aggregation math at the service layer, API-layer
  premium gate/wiring/isolation)
- `ios/TimeSense/Features/Insights/InsightsViewModel.swift` — fetches GET /insights/weekly
- `android/.../features/insights/InsightsViewModel.kt` — same, OkHttp/kotlinx.serialization

### Modified
- `backend/app/repositories/task_repository.py` — count_created_in_range/count_completed_in_range
- `backend/app/repositories/recommendation_feedback_repository.py` — count_signals_in_range
- `backend/app/repositories/meal_repository.py` — count_skipped_by_type_in_range
- `backend/app/repositories/sleep_wake_repository.py` — count_late_wakes_in_range
- `backend/app/repositories/commute_repository.py` — count_confirmed_in_range
- `backend/app/api/v1/__init__.py`, `backend/app/models/__init__.py` — registered router/model
- `backend/app/workers/celery_app.py` — registered insights_tasks + Monday 5am beat schedule
- `ios/TimeSense/Features/Insights/InsightsView.swift` — real content (summary card + stats grid)
  replacing the static placeholder, still gated behind the existing isPremium check; registered the
  new ViewModel file into project.pbxproj via the xcodeproj gem (same tooling as TIME-044)
- `android/.../features/insights/InsightsScreen.kt` — real content, same states/gate

### Design notes
- `most_skipped_meal` only reflects meals explicitly logged with status=skipped — it does not
  backfill inferred-but-never-logged skips from MealRepository.get_today_status's live, read-time-
  only computation. Tie-breaks pick the alphabetically-first meal type on equal counts (deterministic
  for tests): `min(items, key=lambda kv: (-count, meal_type))`.
- `tasks_completed`/`tasks_total` use Task.updated_at/created_at as proxies for completion/capture,
  since Task has no explicit completed_at field yet — approximate, documented as such.
- Only fully-completed Monday-Sunday weeks are summarized (no noisy "this week so far" view).
- Verified with `xcodebuild -target TimeSense -sdk iphonesimulator CODE_SIGNING_ALLOWED=NO` (BUILD
  SUCCEEDED, zero new warnings) and `./gradlew assembleDebug && ./gradlew test` (BUILD SUCCESSFUL,
  using the Android-Studio-bundled JBR as JAVA_HOME per known_issues.md).
- Found (but did not fix, out of scope) a latent bug in `tests/test_recommendations.py`'s
  `_MockProvider`: it constructs `LLMResponse(content=..., model="mock")` without the required
  `provider` field, which raises inside the try/except and silently falls through to the fallback
  "why" text rather than actually exercising the mocked LLM path. My own test_insights.py mock hit
  the identical mistake first and I caught it there — flagging test_recommendations.py's version in
  known_issues.md since it means that test isn't verifying what it appears to verify.

## 2026-07-05 — TIME-045 (Jira TIME-44): Android Widgets

### Created
- `android/app/src/main/java/com/timesense/app/widgets/UsableTimeWidget.kt` +
  `UsableTimeWidgetReceiver.kt` — Glance AppWidget rendering usable minutes remaining today, with
  an "Open TimeSense" empty state before the first sync
- `android/app/src/main/java/com/timesense/app/widgets/NextEventWidget.kt` +
  `NextEventWidgetReceiver.kt` — Glance AppWidget rendering the next upcoming non-done event, or
  "Nothing scheduled"
- `android/app/src/main/java/com/timesense/app/widgets/WidgetColors.kt` — mirrors the literal
  day/night color values from `ui/theme/Theme.kt` (kept private there) so widgets get real
  day/night parity with the rest of the app without a Glance Material3 dependency
- `android/app/src/main/res/xml/usable_time_widget_info.xml`,
  `android/app/src/main/res/xml/next_event_widget_info.xml` — AppWidgetProviderInfo resources,
  `updatePeriodMillis="0"` (app-triggered refresh only, no periodic polling)
- `android/app/src/main/res/layout/glance_default_loading_layout.xml` — placeholder Glance
  requires for `initialLayout`/`previewLayout`, replaced at runtime by the actual Glance content
- `android/app/src/test/java/com/timesense/app/features/today/NextEventSelectionTest.kt` — 6 JVM
  unit tests for the new pure `nextUpcomingEvent()` selection function

### Modified
- `android/gradle/libs.versions.toml`, `android/app/build.gradle.kts` — added
  `androidx.glance:glance-appwidget:1.1.1` (latest stable; 1.2.0+ are alpha/beta/rc)
- `android/app/src/main/AndroidManifest.xml` — registered both widget receivers
- `android/app/src/main/java/com/timesense/app/features/now/NowViewModel.kt` — converted
  `ViewModel` → `AndroidViewModel` (needed an Application Context to call Glance's update APIs);
  calls `UsableTimeWidget.updateUsableMinutes()` after a successful `/now` fetch
- `android/app/src/main/java/com/timesense/app/features/today/TodayViewModel.kt` — same
  `AndroidViewModel` conversion; extracted the next-event selection into a standalone top-level
  `nextUpcomingEvent(tasks, now)` function (kept free of Android types so it's a plain JVM test,
  no Robolectric/instrumentation needed) and calls `NextEventWidget.updateNextEvent()`/
  `.clearNextEvent()` after a successful `/timeline/today` fetch

### Design notes
- Unlike iOS's WidgetKit extension (a separate process needing a shared App Group), Android
  AppWidgets run in the same app process — so each widget just reads its own Glance-managed
  Preferences state, written directly by the one ViewModel that owns that data. No shared
  cross-widget blob or App-Group-equivalent was needed, simpler than TIME-044's iOS design.
- Ticket scope intentionally matches `tickets/implementation_sequence.md` exactly: two widgets
  (usable-time, next-event), not iOS's three — no best-next-action widget on Android in this
  ticket, per the ticket's Non-Goals; a third widget can follow later for platform parity if wanted.
- `androidx.glance.color.ColorProvider(day, night)` (not `androidx.glance.unit.ColorProvider`,
  which only takes a single `Color` or `@ColorRes`) is the two-arg day/night constructor;
  `GlanceModifier.background(...)` needs the `androidx.glance.background` extension, not
  `androidx.glance.appwidget.background` — both were found by iterating on real compiler errors
  from `./gradlew assembleDebug`, not guessed correctly on the first pass.
- Environment note: this sandbox has no `java` on PATH and no `JAVA_HOME` set, but
  `/Applications/Android Studio.app/Contents/jbr` (JetBrains Runtime, JDK 21) is installed and
  works as `JAVA_HOME` for Gradle. Both `./gradlew assembleDebug` and `./gradlew test` succeeded
  with `JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"` set. All 6 new
  unit tests pass; only pre-existing, unrelated warnings (deprecated `Divider` in
  `TimelineCard.kt`, JDK 21 deprecating source/target 8) appear in the build output.

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
