# TimeSense — Release Checklist (v1)

Go/no-go for shipping a build to beta / the stores. Grouped by area; check what applies to the
target (TestFlight beta vs. public release).

## Engineering
- [x] Backend test suite green (`cd backend && pytest`) — 329 passing
- [x] iOS builds clean (`xcodebuild ... -scheme TimeSense`)
- [x] Web builds clean (`cd web && npm run build`)
- [ ] Android builds clean (`cd android && ./gradlew assembleDebug`) — **not verified**: no JDK on the
      current dev machine (`Unable to locate a Java Runtime`); install a JDK 17 to verify
- [x] Live smoke test passes (`python scripts/smoke_test.py`)
- [x] Alembic migrations apply from empty (`alembic upgrade head`)
- [ ] No secrets committed (`.env`, service-account keys, `google-services.json` gitignored)
- [ ] Beta smoke test signed off (docs/launch/beta_smoke_test.md)

## Backend / infra (before a hosted release)
- [ ] Backend deployed to a real host (not the dev Mac) with HTTPS
- [ ] iOS/Android/web point at the production API URL (not `.local`/localhost)
- [ ] Postgres + Redis provisioned; migrations run on deploy
- [ ] Celery worker + beat running (notifications, learning summaries)
- [ ] Sentry / monitoring DSN configured (TIME-054)
- [ ] Rate limiting + security headers enabled (TIME-056)
- [ ] Real OpenAI key with billing (fallbacks work without it, but the LLM is the good path)
- [ ] `GOOGLE_MAPS_API_KEY` set (Geocoding + Places + Distance Matrix enabled, key restricted) to turn on location-aware travel-time recommendations; without it the engine safely runs location candidates at low confidence and never invents distances

## Auth & data
- [x] Real Firebase project wired (iOS `GoogleService-Info.plist`, Android `google-services.json`, web env)
- [x] Backend verifies real Firebase ID tokens; role synced from claim (TIME-065)
- [x] Account deletion works end-to-end (TIME-055 / Settings ▸ Delete My Data)
- [x] Integration tokens encrypted at rest (TIME-056)

## iOS store prep
- [ ] App icon set (currently placeholder AppIcon.appiconset)
- [ ] Screenshots for App Store (docs/launch/store_assets_checklist.md)
- [ ] App Store listing copy (docs/launch/app_store_listing.md)
- [ ] Privacy nutrition labels match docs/launch/privacy_policy.md
- [ ] Purpose strings present (Health, Local Network) — Local Network added (TIME-087)
- [ ] Register device UDIDs / TestFlight group; signing profile valid

## Android store prep
- [ ] Adaptive icon
- [ ] Play Store listing copy (docs/launch/play_store_listing.md)
- [ ] Data safety form matches the privacy policy
- [ ] **Rotate the previously-committed Android API key** (was exposed; user handling) and restrict it

## Legal / compliance
- [ ] Privacy policy reviewed by a human (docs/launch/privacy_policy.md)
- [ ] Terms of Service published
- [ ] Subscription terms + trial disclosure (14-day trial requires payment info)

## Known follow-ups (post-v1, ticket when ready)
- Working-hours: per-weekday windows; feasibility for all tasks (not just best)
- Duration learning: manual duration entry; category display
- In-app calendar OAuth; in-app subscription purchase (StoreKit); in-app data export download
- Production API URL + deploy pipeline; tunnel/deploy for off-network demos

---
_Last verified: 2026-07-06 — v1 feature-complete; the items above gate the first shipped build._
