# Launch / Store Submission Prep (TIME-057)

Everything needed to submit TimeSense to the App Store and Play Store. The copy and form-answers
here are complete and grounded in the app's actual data practices; the visual assets and console
data entry are your steps.

## Contents
- [`privacy_policy.md`](privacy_policy.md) — publishable privacy policy (host it at a public URL; fill bracketed contact/legal details; have it reviewed).
- [`app_store_listing.md`](app_store_listing.md) — iOS metadata, App Review notes, App Privacy label answers.
- [`play_store_listing.md`](play_store_listing.md) — Android metadata, Data Safety form answers, content-rating notes.
- [`store_assets_checklist.md`](store_assets_checklist.md) — the icons/screenshots/binaries **you** produce, with exact sizes.

## Submission runbook
1. **Host** the privacy policy + terms at public URLs; paste them into both listings.
2. **Produce assets** per `store_assets_checklist.md` (icons, screenshots, feature graphic).
3. **Create billing products** (StoreKit + Play Billing) matching pricing: $14.99/mo · $99/yr · $79/yr founder.
4. **Create a demo/test account** and a payment sandbox tester for reviewers.
5. **iOS:** archive a signed build (`com.aetheranalytics.timesense`), upload via Xcode/Transporter, paste metadata + App Privacy answers + review notes, submit.
6. **Android:** build a signed release AAB (`com.timesense.app`), upload, complete Data Safety + content rating, paste metadata, submit for review.

## Not in scope here
- Actual screenshots / icons / feature graphics / preview videos (design assets).
- App Store Connect / Play Console data entry and binary upload/submission.
- Legal review of the privacy policy (recommended before publishing).

See also: `../product/product_brief.md` (positioning, pricing) and `store_assets_checklist.md`
(prerequisites).
