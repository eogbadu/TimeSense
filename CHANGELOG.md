# Changelog

All notable changes to TimeSense are documented here.

Format: `[DATE] TIME-### Short description`

---

## Unreleased

### Phase 14 — Beta Hardening and Launch Readiness

- [2026-07-05] TIME-057: App Store + Play Store prep — docs/launch/ with a publishable privacy policy, iOS + Android store listings, App Privacy / Play Data Safety label answers, App Review notes, and a required-assets checklist (all grounded in actual data practices; assets/console entry are the user's step)
- [2026-07-05] TIME-056: Security hardening — integration OAuth tokens now encrypted at rest (Fernet EncryptedString on Calendar/Slack/Teams/Notion; no migration), security-headers middleware, and in-process rate limiting on POST /capture + DELETE /privacy/account (429 + Retry-After). Audit confirmed Stripe webhook already verifies signatures
- [2026-07-05] TIME-055: Privacy — data export + account deletion — GET /api/v1/privacy/export (portable JSON bundle of all the user's data, OAuth tokens redacted) and DELETE /api/v1/privacy/account?confirm=true (erases the user + cascades all their data + deletes the Firebase Auth user); test conftest now enforces SQLite foreign keys so cascade is exercised
- [2026-07-05] TIME-054: Error monitoring + analytics (backend) — Sentry-optional error monitoring (no-op without a DSN) wired into the error handlers; a privacy-respecting analytics pipeline (analytics_events table + AnalyticsService gated on the `analytics` consent), emits task_captured from /capture, GET /api/v1/admin/analytics event counts. Client analytics deferred

### Fixes

- [2026-07-11] TIME-213: The confidence % on a recommendation now reflects how strong the pick actually is (its real score) and shows the same value everywhere — a clear best-thing reads high, a "nothing pressing" pick reads lower — instead of a fixed 70-ish number that ignored the score and disagreed between screens
- [2026-07-11] TIME-212: The "Why this recommendation?" screen now shows the plain-language summary at the top instead of the bottom, so the takeaway is the first thing you read
- [2026-07-11] TIME-211: Fixed inverted location alerts — leaving home now correctly says "You left Home" and arriving says "You're at Home" (they were swapped). Direction is now read from your actual position at the moment you cross, not a stale cached fix
- [2026-07-10] TIME-210: Your weekly Insights now show a "Recommendations accepted" stat — the share of the week's suggestions you acted on, with the count shown (on iOS and web)
- [2026-07-10] TIME-209: Weekly insights now record how well that week's recommendations landed for you (shown, accepted, acceptance rate, average confidence), pulled from the recommendation feedback loop
- [2026-07-10] TIME-208: TimeSense now tunes how strongly it weights an action type by how often you actually accept it — a smooth acceptance-rate signal rather than an all-or-nothing nudge
- [2026-07-10] TIME-205..207: TimeSense now shows you what it's learned about you — a "What TimeSense has learned" section (in Learned Patterns on iOS, and on the web Insights page) with plain-language notes like "You usually act on focus blocks" or "You tend to skip meeting prep in the evening"
- [2026-07-10] TIME-202..204: TimeSense now learns from your reactions — action types you keep passing on get shown less (and less at the times of day you tend to reject them), and ones you consistently accept get shown more. Powered by the new feedback + measurement loop
- [2026-07-10] TIME-196..201: TimeSense can now measure how good its recommendations are — it records each suggestion it shows and how you react (Agree/Disagree/Snooze), then computes an acceptance rate and confidence calibration (admin metrics). Privacy-respecting (consent-gated, included in data export/delete). The groundwork for the app learning from your reactions
- [2026-07-10] TIME-189..195: Hardened capture — input is validated and cleaned (timezone, location, dates, blank/oversized text), the AI parse output is bounded and sanity-checked, prompt-injection in captured text is neutralized, rapid duplicate captures are deduped, and all apps cap input at 2000 chars. Groundwork for measuring and improving recommendations
- [2026-07-10] TIME-185..188: The Best Next Action screen now asks "Agree / Disagree" first — Agree reveals Done/Snooze to act on it; Disagree swaps in a different recommendation (the one you passed on drops down but isn't hidden, so it can come back later). Live on backend + iOS + Android + web; a cleaner signal of how good each recommendation is
- [2026-07-10] TIME-184: An appointment coming up within the hour now reliably shows as your top recommendation, instead of occasionally being edged out by a generic "wind down for the night" nudge (also fixes a flaky test)
- [2026-07-10] TIME-183: Android now has a Connections screen (Settings ▸ Connections) to connect Google Calendar, Outlook, and Slack — opens the sign-in in your browser and returns to the app when done
- [2026-07-10] TIME-182: iOS now has a Connections screen (Settings ▸ Connections) to connect Google Calendar, Outlook, and Slack via a secure in-app sign-in sheet
- [2026-07-10] TIME-181: Backend support to connect Slack — a real OAuth flow so you can authorise TimeSense to scan channels for action items (activates once the Slack app credentials are set)
- [2026-07-10] TIME-180: TimeSense can now connect Outlook / Microsoft calendars — a new Microsoft Graph provider plus its OAuth flow, alongside Google (activates once the Microsoft app credentials are set)
- [2026-07-10] TIME-179: The mobile apps now recognise your real Premium status on sign-in — fixing Insights, which previously showed the "Upgrade" gate to everyone (even paying/trial users) because the app never checked your subscription
- [2026-07-10] TIME-178: Everyone now gets Premium free for their first 2 weeks (no payment) — a true 14-day intro trial that unlocks Insights, the "why" explanations, integrations, and all Premium features from day one
- [2026-07-09] TIME-177: Backend groundwork to connect Google Calendar — a real OAuth handshake (/integrations/google/authorize + /callback) that gets consent, exchanges the code server-side, and stores tokens encrypted. Goes live once the Google OAuth app credentials are set; calendar writes stay approval-gated
- [2026-07-09] TIME-176: The TimeSense logo across the web now uses the real app-icon mark — a glowing blue→violet ring with a sparkle — instead of a plain circle, with a matching favicon
- [2026-07-09] TIME-175: The web Now page now has a "Why this recommendation?" explainer — tap it to see the summary, the signals TimeSense weighed (with what's connected vs not), what tipped the decision, and the alternatives it considered
- [2026-07-09] TIME-174: Removed the Next.js dev-tools "N" badge from the web app
- [2026-07-09] TIME-173: The website now has a Terms of Service at /terms (linked from the footer, cross-linked with Privacy) — plain-language and TimeSense-specific: recommendations are suggestions you approve, the trial/Free-Basic/billing rules, acceptable use, your content, and clear disclaimers. No app-store links yet (pending real URLs)
- [2026-07-09] TIME-172: The website now has a real Privacy Policy at /privacy (linked from the footer) — plain-language, TimeSense-specific: what we collect, the opt-in-only raw-audio rule, how captures are parsed by AI, who we share with, and your controls (approval-first, opt-in connections, export, delete). No ads, no selling data
- [2026-07-09] TIME-171: The web companion now has an Insights tab — Premium users see their weekly summary and stats (tasks, completion rate, most-skipped meal, late wake-ups, commutes); everyone else sees a preview of what Premium unlocks
- [2026-07-09] TIME-170: The web is now a real companion app — signed-in users get /app with their best next action (Now), today's plan (Today), and quick Capture, all in the cosmic domain-colour style. Admin moved to the footer
- [2026-07-09] TIME-169: Clicking the TimeSense logo now returns you to the top of the home page (it previously did nothing when you were already on the page), and in-page links land cleanly below the sticky nav
- [2026-07-09] TIME-168: The companion website is now a real marketing landing page — a cosmic hero, five feature sections with app screenshots, a capability grid, and a download CTA, all matching the app's look (admin login still one click away)
- [2026-07-09] TIME-167: When you attach a place to an errand at capture, TimeSense now recommends and routes to that exact place — instead of guessing the location from the task's title. Works even without maps by estimating travel from distance
- [2026-07-09] TIME-165: Capture chips now reveal a matching input — Reminder/Schedule show a date with an optional time, and Errand shows a location autocomplete (your saved places + maps). What you pick overrides what the text parsed, and it all stays optional
- [2026-07-09] TIME-164: Capture can now take an explicit time, date, or location that overrides what the text parsed — tasks store a real location (name + coordinates), and a new places search (your saved places + maps) powers errand autocomplete
- [2026-07-09] TIME-163: The Capture chips now do something — tapping one (Task/Reminder/Schedule/Errand/Idea) tags your capture so TimeSense parses it that way (e.g. Idea = low-priority, no deadline). They're also fully visible now (wrap to two rows) instead of scrolling off-screen
- [2026-07-09] TIME-162: Capture and Insights are no longer mono-purple — Capture chips and detectors now use distinct colours + icons (blue/amber/violet/cyan/green), and each Insights card has its own accent with a glowing chart
- [2026-07-09] TIME-161: Added App Store marketing screenshots (5 frames, 1290×2796) — real cosmic-themed app screens with Didot serif headlines, plus a reproducible build script
- [2026-07-09] TIME-160: TimeSense now senses when you've been sitting a while (inferred from your step activity) and nudges a short walk — 'You've been sitting for 82 min, a short walk will reset your focus' — with the sitting time also shown on the Energy card
- [2026-07-09] TIME-159: TimeSense now reads your steps and activity from Apple Health (in addition to sleep) and shows a real Steps card on Now. Read-only; TimeSense never writes to Health
- [2026-07-09] TIME-158: Backend now stores daily HealthKit activity (steps, active energy, exercise minutes) and surfaces steps/activity in the Now dashboard payload — groundwork for the real Steps/Activity cards
- [2026-07-09] TIME-157: The 'Why this recommendation' screen now matches the theme — its header is a domain-colored hero with a matching confidence ring, and the signals use colored icon chips with green checks
- [2026-07-09] TIME-156: The cosmic + domain-color look now extends across Today, Capture, and Insights — Today's recommendation is a domain-colored hero, task rows use the semantic accents, the Capture orb is a blue→violet gradient with a glow, and Insights stats get colored icon chips
- [2026-07-09] TIME-155: The recommendation card now matches the reference — a dark card whose glow, icon, and pills take the COLOR of the recommendation (green for a walk/health, blue for focus, cyan for errands, violet for meetings), instead of a fixed blue→violet gradient. The dashboard now uses richer multi-color accents
- [2026-07-09] TIME-154: Unified the theme so backgrounds and colors match everywhere — one near-black neutral navy across the background, cards, chips, footer, and tab bar (no more purple wash or mismatched tones), matched to the reference design
- [2026-07-09] TIME-153: Premium glassmorphism pass — the recommendation card now uses a soft blue→violet gradient (no more flat blue) with a neon violet glow, cards are frosted glass, and the background blends navy→indigo→violet with soft glows
- [2026-07-09] TIME-152: Today's agenda gets glowing accent dots on each time-of-day header (Morning/Afternoon/Evening) — the finishing touch on the cosmic redesign
- [2026-07-09] TIME-151: The Now screen gains a glanceable dashboard — Calendar (next meeting), Tasks (due/done today), Energy (from your sleep), and Nearby (where you are) — all from real data, with cards that hide themselves when the signal isn't there
- [2026-07-09] TIME-150: The whole app now wears the cosmic theme — every tab sits on the deep-navy background with soft auras, and all cards use a consistent translucent 'glass' style
- [2026-07-09] TIME-149: The Now screen goes cosmic — the 'Best Next Action' is now a glowing blue→violet gradient card with a domain icon and signal pills, on a deep-navy background with soft auras. The color shifts by recommendation type (green for health, blue for errands, violet for focus). The cross-domain 'TimeSense suggests' card gets the same treatment
- [2026-07-09] TIME-148: New cosmic theme foundation — deep-navy background, blue→violet accents, gradient + glow tokens, and a semantic energy green, all sampled from the app icon. App now defaults to the dark cosmic look (still switchable in Settings)
- [2026-07-09] TIME-147: New app icon — the blue→violet glowing ring with a guiding-star clock (installed full-bleed; anchors the upcoming cosmic theme)
- [2026-07-08] TIME-146: Fixed voice capture — it now keeps listening through pauses (continuing your sentence appends instead of wiping what you already said), and the waveform stays live and reacts to your voice the whole time
- [2026-07-08] TIME-145: Voice capture now shows a live, audio-reactive waveform while listening — the bars rise and fall with your voice
- [2026-07-08] TIME-144: Voice capture — tap the mic on Capture and speak; TimeSense transcribes on-device (live) into the field and turns it into a task. Raw audio is never stored
- [2026-07-08] TIME-143: The engine now surfaces upcoming appointments — an appointment within ~an hour becomes the top recommendation ('Coming up: …' / 'Head out soon for …') instead of being buried, and it no longer recommends squeezing an errand into the time right before a commitment
- [2026-07-08] TIME-142: The Now 'analyzed your day' banner now counts up over time ('just now' → '2 min ago') instead of appearing frozen — it wasn't hard-coded, it just lacked a timer
- [2026-07-08] TIME-141: The 'Why this recommendation' Calendar signal now shows your REAL free time — until your next meeting/task or the end of your working day, accounting for your calendar and scheduled tasks — instead of the misleading hard-capped '240 minutes'
- [2026-07-08] TIME-140: Capturing 'Go to Walmart today at 5pm' now actually schedules it at 5pm (a specific time becomes a real time block); a date without a time becomes a due date. The deterministic parser runs alongside the LLM and fills whatever it misses, so times stop getting dropped
- [2026-07-08] TIME-139: The app now sends your device's timezone to the backend on launch (it was stuck on UTC) — so greetings, 'today', working hours, and scheduling all use your real local time
- [2026-07-08] TIME-138: Tapping a notification now takes you somewhere useful — a 'block time for X' push opens Today with the scheduler pre-filled for that task; other notifications open Now
- [2026-07-08] TIME-137: TimeSense now proactively offers to block time for high-priority/overdue unscheduled tasks — a push ('Block time for X? You have a free slot tomorrow at 2pm') when the engine has no more urgent recommendation, using a calendar-aware free slot. POST /api/v1/devices/test-offer fires one on demand
- [2026-07-08] TIME-136: 'Find a time' now rolls to the next few days when today is full — the suggested slot searches today through +3 days (respecting each day's working hours + your calendar) and tells you which day
- [2026-07-08] TIME-135: Engine-suggested time blocks — 'Find a time & add to calendar' (long-press a Today task) now asks the engine for the earliest free slot that avoids your meetings and scheduled tasks and respects working hours, then pre-fills the native editor with it for approval
- [2026-07-08] TIME-134: Add a task to your calendar — long-press a task on Today ▸ 'Add to Calendar' opens Apple's native event editor pre-filled with the task; you review and tap Add (calendar writes always require your approval). The new event then syncs back
- [2026-07-08] TIME-133: Your connected calendar now shows on the Today screen — an 'On your calendar' section lists today's events (time, title, location), read-only
- [2026-07-08] TIME-132: Connect Apple Calendar (Settings ▸ Calendar) — grants calendar access, reads your upcoming events, and syncs them so recommendations factor your schedule (meeting prep, free-block timing). Re-syncs on launch. Reads any calendars added to iOS, including Google
- [2026-07-08] TIME-131: Apple Calendar (backend) — synced-events store + PUT/GET /api/v1/calendar/synced so the app can push the events it reads from EventKit; the recommendation engine now factors your real calendar (meeting prep/join/leave, free-block from the next event). All-day events are ignored for meeting logic
- [2026-07-08] TIME-130: Push diagnostics (launch marker, registration, device token, foreground-present) now log only in Debug builds via a debugLog helper — no console noise or token logging in production
- [2026-07-08] TIME-129: Notifications now appear even when the app is open (foreground) — previously iOS suppressed them, which looked like the push hadn't arrived. Verified APNs push works end-to-end on device
- [2026-07-08] TIME-128: Push token never arrived because FirebaseAuth's app-delegate swizzling was swallowing the APNs registration callback — disabled it via FirebaseAppDelegateProxyEnabled=NO so our delegate receives the device token
- [2026-07-08] TIME-127: Added loud launch + push-registration console markers to confirm a fresh build is running (diagnostic for the on-device push setup)
- [2026-07-08] TIME-126: The app now registers for APNs push on every launch regardless of notification permission (previously it only registered if you'd granted permission, so the device token was never obtained). Logs the token to the Xcode console for debugging
- [2026-07-08] TIME-125: Fixed two on-device bugs — (1) location posting / device registration / place sync were 500-ing on Postgres because four migrations were missing the created_at/updated_at defaults (added a migration to fix them); (2) the Today page showed an empty 'your day is open' in the evening because untimed tasks were only included when the client date matched the server's UTC date — now tolerant of the local/UTC date boundary
- [2026-07-07] TIME-124: Fixed the Capture screen trapping you with the keyboard up — added a 'Done' keyboard button and swipe-down-to-dismiss (the multi-line field made Return add a newline, and there was previously no way to close the keyboard)
- [2026-07-07] TIME-123: Added a Celery beat service to docker-compose (fires the schedules incl. the 30-min proactive-push scan) and POST /api/v1/devices/test-push — sends a push to your own devices immediately (engine text or a {title, body} override), bypassing eligibility/cooldown, for verifying the APNs chain
- [2026-07-07] TIME-122: iOS registers for APNs remote push and syncs its device token to /api/v1/devices — enabling the backend's proactive push (needs Apple APNs creds on the server + a push-enabled provisioning profile to deliver)
- [2026-07-07] TIME-121: APNs remote push backend — device-token registration (PUT/DELETE /api/v1/devices), a gated Google-style APNs sender (ES256 JWT over HTTP/2; no-op without credentials), and a ProactivePushService that pushes the engine's LLM-phrased text only when eligible_for_push and outside a 45-min cooldown (same-type suppressed; high-urgency overrides), driven by a Celery task every 30 min. Also: location_fit now defaults to neutral (0.5) for location-independent actions so strong tasks can reach the push threshold
- [2026-07-07] TIME-120: Arrival/departure notifications now use the engine's LLM-phrased recommendation text (via /now/recommendation) instead of a plain 'Best next: X' line — and stay quiet (light acknowledgement) when there's nothing worthwhile to suggest
- [2026-07-07] chore(config): consolidated to a SINGLE root .env — migrated the 13 backend-only keys (incl. GOOGLE_MAPS_API_KEY) into the canonical root .env.example, deleted the redundant backend/.env.example, and simplified config to load only the root .env. Fixes the confusion of two drifting env templates
- [2026-07-07] TIME-119: The Now screen now surfaces the engine's full cross-domain recommendation (wind-down, prep-for-meeting, nearby errand…) as a 'TimeSense suggests' card with the LLM explanation, confidence, and travel info — via /now/recommendation. Task picks keep the existing best-action card
- [2026-07-07] TIME-118: New GET /api/v1/now/recommendation — returns the FULL engine decision (any domain: task, health, routine, planning, location, calendar…) with LLM-phrased text, reason codes, confidence, score, push eligibility, related_task_id (when task-backed), destination/travel (when present), and alternatives. Also: a task due very soon is no longer night-suppressed (only non-urgent work is)
- [2026-07-07] TIME-117: LLM explanation layer — the engine can now phrase its already-selected recommendation via the LLM (friendly title/body/explanation), with strict guardrails (never changes the action, never invents distances/times) and deterministic fallback on any failure. Documented GOOGLE_MAPS_API_KEY in .env.example + release checklist
- [2026-07-07] TIME-116: The app now syncs your saved places (with coordinates) to the backend, so the recommendation engine can resolve errands and compute real travel time (needs a maps API key set on the server)
- [2026-07-07] TIME-115: Real maps provider — added a Google Maps provider (geocode/nearby/travel-time) gated by GOOGLE_MAPS_API_KEY, a user_places store + GET/PUT /api/v1/places to sync saved places with coordinates, and context plumbing (preferred destinations + travel origin from the current saved place). With a key + synced places, the engine computes real driving time and errands lead only when the trip actually fits
- [2026-07-07] TIME-114: /now is now driven by the deterministic recommendation engine — best_task ordering comes from generate→score→rank (task + location domains) over a real UserContext (tasks, location, sleep-derived health, work hours), replacing the ad-hoc TaskScorer + rerank. An at-home errand with no confirmed travel never leads; existing behaviors (overdue, priority, suppression, wind-down) preserved
- [2026-07-07] TIME-113: Recommendation engine decision core — multi-domain candidate generation (calendar/task/location/health/routine/planning/context-switch/fallback), deterministic weighted scoring + hard-rule penalties, ranking, selection, and push-eligibility. Errands that can't be confirmed feasible never win; meeting-soon suppresses deep work; night suppresses errands; poor sleep favors recovery. 17 new tests
- [2026-07-07] TIME-112: Deterministic recommendation engine — foundation (phases 1-6): typed engine package (no Any), centralized time & location services, maps-skill wrapper with a NullMapsProvider (degrades to low-confidence, never invents distances), travel-feasibility service, and context normalization. 15 new tests
- [2026-07-07] TIME-111: Swipe a Today task left to reveal Done + Delete buttons (replaces the long-press menu)
- [2026-07-07] TIME-110: Location is now always factored — an errand (e.g. 'Go to Walmart') can never be the top recommendation while you're home, and the app now syncs your current place even when you were already there. Errands still surface when you're out
- [2026-07-07] TIME-109: Delete tasks from Today — long-press a task in the Smart Plan for 'Mark done' / 'Delete task'
- [2026-07-07] TIME-108: Location now shapes the recommendation — the app reports your current place (POST /location/place; only the name, never raw coords), and Now surfaces errands when you're out / de-prioritizes them at home. 'Why this recommendation?' Location signal shows your real place
- [2026-07-07] TIME-107: Save any number of named places — replaced the fixed Home/Work buttons with a name field + quick-pick chips (Home/Work/Gym/School/Errands), up to iOS's 20-region limit
- [2026-07-07] TIME-106: Geofence radius reduced 150->100m so departures are detected after less travel (100m is iOS's reliable floor; TIME-105 dedups any jitter)
- [2026-07-07] TIME-105: More reliable arrival/departure notifications — verify the authoritative geofence state and dedup stale/out-of-order events (fixes 'you left home' showing on arrival); radius 130->150m
- [2026-07-07] TIME-104: 'Allow Always' now guides you to iOS Settings — tapping it did nothing because iOS silently no-ops the in-app Always prompt; the Location & Places screen now shows an 'Open iOS Settings' button + explainer for the While-Using state
- [2026-07-06] TIME-103: Location-aware arrival notifications — with Always location, TimeSense monitors geofences around your saved places (Home/Work) and, on arrival/departure, fires a local notification with your best next task. Settings ▸ Location & Places. Raw location is never stored (needs on-device testing)
- [2026-07-06] TIME-102: Visual polish — darkened light-mode secondary text for better contrast/legibility (chips, card hierarchy, and section headers were delivered across the screen redesigns)
- [2026-07-06] TIME-101: Settings home regrouped into AI Planning / Integrations / Privacy / Account for a more structured, mature feel
- [2026-07-06] TIME-100: Subscription redesigned — Current Plan card, 'Basic includes' checklist, and an indigo 'Premium unlocks' card + Upgrade CTA
- [2026-07-06] TIME-099: Privacy & Consent redesigned — signal rows with status labels (Calendar/Health/Location/Audio) + data controls (Delete/Export) + encrypted-never-sold note
- [2026-07-06] TIME-098: Calendar screen redesigned — hero + 'Connect your calendar' + Connect CTA + supported providers (Google/Apple) + privacy note
- [2026-07-06] TIME-097: Working Hours redesigned — an explainer banner ('why this matters'), Start/End rows, and a Repeat day selector (Mon-Fri)
- [2026-07-06] TIME-096: Renamed 'Learned Assumptions' to 'Learned Patterns' and redesigned it — explainer banner + icon rows with confidence/source + an add button
- [2026-07-06] TIME-095: Insights locked state now previews the AI value — a 'Your AI Insights' banner + sample preview cards (best focus window, patterns, schedule balance, routine consistency) instead of a bare paywall
- [2026-07-06] TIME-094: Redesigned Capture to feel AI-native — hero capture icon, clearer AI copy, quick type chips, a voice affordance, and a 'TimeSense can detect' row
- [2026-07-06] TIME-093: Redesigned the 'Why this recommendation?' screen — a Recommended-action + confidence-ring header, 'Signals analyzed' (Calendar/Time of day/Location/Priority/Energy with checks), 'Alternatives considered', and a plain-English summary
- [2026-07-06] TIME-092: Redesigned the Today page — date + progress header, an 'AI Recommended Now' card, and a 'Smart Plan' grouped into Morning/Afternoon/Evening with tap-to-complete rows
- [2026-07-06] TIME-091: Now context chips (Calendar/Routine/Location/Time/Tasks) now all fit on one row — removed the horizontal scroll
- [2026-07-06] TIME-090: Redesigned the Now page to the approved mockup — analysis banner, context chips, a richer Best Next Action card with an inline confidence bar and category icon, and an 'Other good options' list
- [2026-07-06] TIME-089: "Why This Recommendation?" is now a full breakdown — recommended action, the context used (calendar/time/energy/location/task), decision factors, alternatives considered, a confidence score, and a summary; opens as a sheet. Backed by a real explanation pipeline with an audit trail
- [2026-07-06] TIME-088: Renamed the Now recommendation-explanation link from "Why this?" to "Why This Recommendation?"
- [2026-07-06] TIME-058: v1 close-out — beta smoke-test script + manual beta checklist + go/no-go release checklist (docs/launch/); v1 is feature-complete
- [2026-07-06] TIME-087: On-device demos work — the app now reaches the Mac's dev backend over the LAN (via its .local name) with local-network HTTP allowed, instead of failing on localhost
- [2026-07-05] TIME-086: Working hours are configurable (Settings ▸ Working Hours) — auto-scheduling and feasibility now use your hours instead of a fixed 8am–9pm
- [2026-07-05] TIME-085: TimeSense now auto-places new tasks into the next open slot in your day (using its time estimate, your working hours, and existing blocks) — with a one-tap 'Undo' on Today
- [2026-07-05] TIME-084: Feasibility warnings — when the best task can't be finished before it's due (given its estimate, your working hours, and existing blocks), Now shows a gentle heads-up with the next realistic slot
- [2026-07-05] TIME-083: TimeSense learns your pace — completing a task briefly asks 'How long did that take?' (~15/30/60m), but only while it's still learning that kind of task, then stops. Feeds the per-user duration estimates
- [2026-07-05] TIME-082: Task duration brain — every task now gets a realistic time estimate from a seed lookup table (works without the LLM), plus a per-user learned table the assistant refines from real durations over time (foundation for scheduling + feasibility)
- [2026-07-05] TIME-081: 'Usable minutes' on Now now measures time left until your LOCAL midnight (was UTC), so the number is correct for your timezone
- [2026-07-05] TIME-080: Now is local-time-aware — fixed the greeting (was UTC-based) and added a gentle wind-down 'moment' when it's late locally and nothing is urgent, instead of always pushing a task
- [2026-07-05] TIME-079: 'Why this?' now consistently justifies the recommended task instead of occasionally arguing to rest/do it later — tightened the LLM prompt and reframed the time-of-day energy hints
- [2026-07-05] TIME-078: 'Why this?' now loads lazily on tap (new GET /now/why) so the Now screen stays instant — the LLM explanation is only fetched when you ask for it
- [2026-07-05] TIME-077: Now shows two alternative options and a real 'Why this?' — the LLM explains why the best task beats the alternatives given the time of day, likely energy, free time, and deadlines (deterministic fallback when the LLM is unavailable)
- [2026-07-05] TIME-076: Settings rows now work — Profile, Subscription, Notifications, Appearance (light/dark), Privacy, Calendar, About are real screens; added Sign Out and a working Delete My Data (erases account + signs out)
- [2026-07-05] TIME-075: Now hero card has a 'Why this?' explanation (hidden by default, expands on tap) — e.g. "Recommended because it's due today and it fits your 240 free minutes."
- [2026-07-05] TIME-074: Now quick actions fixed — Snooze/Not-now now work (record feedback; /now hides snoozed/dismissed tasks so a new best task appears) and the action labels no longer wrap
- [2026-07-05] TIME-073: Premium visual redesign (calm/minimal, Apple-like) — white cards on a soft-gray canvas, deep indigo accent, SF Pro typography, soft shadows, redesigned Now hero. Elevates every screen via the shared design tokens
- [2026-07-05] TIME-072: Capture extracts dates without the LLM — when OpenAI is unavailable (e.g. 429/quota), a rule-based parser pulls today/tomorrow/weekday/"Month Dayth"/"at 5pm" from the text so tasks still get a due date (and a cleaner title), and Now's best-task prioritization works
- [2026-07-05] TIME-071: Today tab now shows untimed pending tasks (your captured to-dos), not just scheduled blocks — so you can see your full list (Now still shows the single best next action by design)
- [2026-07-05] TIME-070: iOS recovers from 401s — a launch race showed "session expired" on a valid session with no way back to sign-in; APIClient now refreshes the token and retries on 401, and a persistent 401 signs out to the sign-in screen
- [2026-07-05] TIME-069: Add backend/run_dev.py dual-stack dev launcher — the iOS Simulator connects to IPv6 localhost (::1) but `uvicorn app.main:app` binds IPv4 only; run_dev.py serves both ::1 and 127.0.0.1. Documented in CLAUDE.md
- [2026-07-05] TIME-068: Now/Today now reload when you return to the tab (e.g. after capturing a task) and support pull-to-refresh — SwiftUI .task didn't re-run on tab switches since TabView keeps views mounted
- [2026-07-05] TIME-067: Fix day-view task visibility — iOS APIClient no longer mangles query strings (URL.appending(path:) was percent-encoding '?query' → 404 on Today and every query-param endpoint); backend Now now surfaces unscheduled just-captured tasks (were excluded as neither scheduled-today nor overdue)
- [2026-07-05] TIME-066: Fix iOS invisible UI — the project had no asset catalog, so DesignTokens named colors (TextPrimary/Surface/Background/etc.) resolved to invisible fallbacks and nearly the whole UI rendered white-on-white; added Assets.xcassets with all colorsets (light+dark) + an AppIcon set
- [2026-07-05] TIME-065: Sync DB user role from the Firebase token claim — `/users/me` now mirrors the claim into the DB `role`, so granting admin is one step (set the claim) instead of also updating the DB row; the claim is the single source of truth
- [2026-07-05] TIME-064: Load `.env` from the repo root regardless of working directory — `cd backend && uvicorn` previously loaded no env (looked for backend/.env), silently disabling real Firebase auth at runtime; config.py now resolves the root .env by absolute path
- [2026-07-05] TIME-063: Fix Alembic migration ordering — recommendation_feedback (FK→tasks) and tasks were parallel sibling branches, so a fresh `alembic upgrade head` could run feedback before tasks and fail; repointed feedback to depend on the tasks migration. A fresh Postgres now migrates end-to-end (tests missed it because they build schema via create_all)

### Auth & Native Capabilities

- [2026-07-05] TIME-062: Client Firebase config (iOS + Android) — linked firebase-ios-sdk (11.x) + GoogleSignIn to the iOS app and added GoogleService-Info.plist; replaced the Android google-services.json placeholder with the real timesense-eb7ec config. iOS builds + runs with real Firebase (web config still pending)
- [2026-07-05] TIME-061: Backend real Firebase token verification — robust service-account parse so the Admin SDK initializes with the real .env credential (project timesense-eb7ec); the backend now verifies real Firebase ID tokens (client config files still needed for end-to-end)

### iOS Signing & Native Capabilities

- [2026-07-05] TIME-060: iOS HealthKit sleep/wake read — HealthService reads Apple Health sleep analysis (read-only) and syncs the latest wake to POST /api/v1/sleep/events (completes the TIME-042 sleep/wake feature's mobile half); HealthKit entitlement + usage string + a "Connect Apple Health" Settings row
- [2026-07-05] TIME-059: iOS real Apple signing config — DEVELOPMENT_TEAM + bundle IDs + App Group aligned to the real Apple Developer account (com.aetheranalytics.timesense, Team WB5NV894N5); verified the App Store Connect key provisions against the account (blocked only on a registered device)

### Phase 13 — Integrations Expansion

- [2026-07-05] TIME-053: Google Assistant integration — Dialogflow fulfillment webhook exposing the same 5 actions as the iOS App Intents (what to do next, log lunch, start focus, mark done, replan day); POST /api/v1/assistant/webhook, backend-only, unit-tested intent→action mapping
- [2026-07-05] TIME-052: Siri Shortcuts / App Intents — 5 App Intents (what to do next, log lunch, start focus, mark done, replan day) exposed to Siri and the Shortcuts app via an AppShortcutsProvider; verified with a real iOS Simulator build + install/launch (Simulator runtime now available)
- [2026-07-05] TIME-051: Notion integration — read a Notion database's pages as candidate tasks (structured title + due extraction, no LLM), user-imported into Tasks; POST /api/v1/notion/connect, /scan (Premium-gated), /pending, /items/{id}/import|dismiss. Introduces a TaskSourceProvider abstraction, distinct from the chat-oriented MessageSourceProvider
- [2026-07-05] TIME-050: Microsoft Teams integration — read Teams chat messages via Microsoft Graph, LLM-detect action items, approve-before-task-creation; POST /api/v1/teams/connect, /scan (Premium-gated), /pending, /actions/{id}/confirm|reject. Extracts a shared source-neutral action-item detection service reused by Slack + Teams
- [2026-07-05] TIME-049: Slack integration — read recent Slack messages, LLM-detect action items, surface each as a pending suggestion the user must confirm before it becomes a Task (never auto-created); POST /api/v1/slack/connect, /scan (Premium-gated), /pending, /actions/{id}/confirm|reject

### Phase 12 — Admin Dashboard

- [2026-07-05] TIME-048: Admin dashboard foundation (web) — bootstraps web/ (Next.js + Firebase Auth) with a role-protected /admin dashboard (metrics, user search, invite codes, subscriptions, feedback review); adds the missing backend admin endpoints (subscriptions/feedback/integrations/metrics/waitlist) alongside it

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
