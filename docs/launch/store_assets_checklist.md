# Store Assets Checklist

These are the visual/binary assets **you** must produce (I can't generate real screenshots or
icons). Sizes are current store requirements; verify against the consoles at submission time.

## iOS — App Store Connect

### App icon
- [ ] 1024×1024 px, PNG, no alpha, no rounded corners (Apple rounds it).

### Screenshots (PNG/JPG, RGB, no transparency)
At least one set is required; localized sets optional. Use the largest device per size class — Apple
scales down.
- [ ] **6.9"** iPhone (e.g. iPhone 16 Pro Max) — 1320×2868 or 2868×1320 — **3–10 shots**
- [ ] **6.5"** iPhone (fallback) — 1242×2688 / 1284×2778 — 3–10 shots
- [ ] **13"** iPad Pro (only if you ship iPad) — 2064×2752 — 3–10 shots
- Suggested shots: Now (best next action) · Today (usable time) · Capture · a connected-integration
  suggestion · Settings (privacy controls).

### Optional
- [ ] App preview video(s) per size (15–30s, portrait).
- [ ] Promotional text already drafted (see `app_store_listing.md`).

### Prerequisites
- [ ] Paid Apple Developer Program membership (Team `WB5NV894N5`).
- [ ] Register the device UDID + provision (signing already wired: `com.aetheranalytics.timesense`).
- [ ] StoreKit products created (monthly/annual/founder) matching the pricing.
- [ ] Sandbox tester account for review.
- [ ] Demo account credentials for the reviewer.
- [ ] Privacy Policy + Support + Marketing URLs live.
- [ ] App Privacy answers entered (see `app_store_listing.md`).

## Android — Play Console

### Icon & graphics
- [ ] **App icon** 512×512 px, 32-bit PNG (with alpha).
- [ ] **Feature graphic** 1024×500 px, PNG/JPG (required).

### Screenshots (PNG/JPG, 16:9 or 9:16, 320–3840 px per side)
- [ ] **Phone** — at least **2** (up to 8). Suggested same five as iOS.
- [ ] **7" tablet** and **10" tablet** — only if you market tablet support.

### Optional
- [ ] Promo video (YouTube URL).

### Prerequisites
- [ ] Google Play Developer account.
- [ ] Signed release AAB (`com.timesense.app`) — `./gradlew bundleRelease` with a release keystore.
- [ ] Play Billing products created matching the pricing.
- [ ] Data Safety form completed (see `play_store_listing.md`).
- [ ] Content rating (IARC) questionnaire completed.
- [ ] Privacy Policy URL live.
- [ ] Demo/test account for review.

## Shared prerequisites
- [ ] Host the privacy policy at a public URL (from `privacy_policy.md`).
- [ ] Host Terms of Use.
- [ ] Real Firebase project client config already in place (iOS plist / Android `google-services.json`).
- [ ] Confirm sign-in providers enabled in Firebase (Email/Password, Apple).
