# Shipping TimeSense to TestFlight

Everything here that a machine can do is done by `scripts/testflight_build.sh`. What remains is the
handful of things that need the Apple account holder, listed at the bottom.

---

## The build

```bash
scripts/testflight_build.sh              # archive + export a signed .ipa into build/testflight/
scripts/testflight_build.sh --upload     # ...and send it to App Store Connect
BUILD_NUMBER=7 scripts/testflight_build.sh --upload
```

The script archives, re-signs for distribution, then **verifies the artifact before it will upload
it**: Sign in with Apple entitlement present, `get-task-allow` gone, export compliance declared, and
both privacy manifests bundled. If any check fails it stops rather than uploading a build that
App Store Connect would bounce.

Build numbers default to seconds since 2026-01-01, so they always increase and never collide.
App Store Connect rejects a repeat build number for the same version.

### What makes the artifact uploadable

The archive itself signs with an **Apple Development** identity — that is what automatic signing
picks for a `generic/platform=iOS` archive, and it is fine. The `-exportArchive` step is what turns
it into a distribution build: it re-signs with **Apple Distribution**, strips `get-task-allow`,
flips `aps-environment` to `production`, and adds `beta-reports-active`. An `.xcarchive` on its own
is not uploadable; do not go looking for the fault in the archive step.

---

## Uploading

The upload needs an App Store Connect API key. One-time setup:

1. App Store Connect → **Users and Access → Integrations → App Store Connect API** → generate a key
   with the **App Manager** role.
2. Download the `.p8`. **It can only be downloaded once.**
3. ```bash
   mkdir -p ~/.appstoreconnect/private_keys
   mv ~/Downloads/AuthKey_XXXXXXXXXX.p8 ~/.appstoreconnect/private_keys/
   export ASC_KEY_ID=XXXXXXXXXX
   export ASC_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```

Without a key you can still build the `.ipa` and upload it by hand with **Transporter** (free on the
Mac App Store) or Xcode's Organizer.

Processing takes 5–15 minutes before a build shows up in TestFlight.

---

## App Store Connect record

Create the app once, at App Store Connect → Apps → **+**. These are the only fields the
**New App** sheet asks for:

| Field | Value |
|---|---|
| Platforms | iOS |
| Name | TimeSense |
| Primary Language | English (U.S.) |
| Bundle ID | `com.aetheranalytics.timesense` |
| SKU | `timesense-ios` |
| User Access | Full Access |

**Category is not on that sheet** — it lives under App Store → General → **App Information** after
the app exists, and it is not required for TestFlight at all, only for App Store submission. Set it
to Productivity whenever you get there.

The bundle ID must already exist as an App ID in the Developer portal, and appears in that dropdown
only if it does. It does — automatic signing created it during the first archive, along with the
HealthKit, App Groups, Push and Sign in with Apple capabilities. If the dropdown is empty or missing
it, the App ID never propagated: check developer.apple.com → Certificates, Identifiers & Profiles →
Identifiers.

### App Privacy answers

These must match `ios/TimeSense/PrivacyInfo.xcprivacy`, which is the source of truth. Every item is
**linked to the user**, **not used for tracking**, and collected for **App Functionality**:

- Email Address, User ID
- Precise Location
- Health, Fitness
- Other User Content (tasks, and mirrored calendar events)

Answer **No** to "Do you use data for tracking?".

### Export compliance

Already answered in the app: `ITSAppUsesNonExemptEncryption = false` in `Info.plist`. TimeSense uses
only HTTPS and the platform keychain — standard, exempt cryptography. Uploads should no longer stall
in "Missing Compliance".

---

## Internal vs external testing

**Internal** — up to 100 people who hold a role on your Apple Developer team. No Beta App Review, no
privacy policy required, available as soon as the build finishes processing. Use this first.

**External** — up to 10,000 people by email or public link. Requires **Beta App Review**, which is a
real review by a person and which the checklist below exists to survive.

---

## Test information (external testing)

Paste these into TestFlight → Test Information.

**Beta App Description**

> TimeSense tells you what to do next. Capture a task by typing or speaking it, and TimeSense reads
> your calendar, your energy and where you are to recommend the one thing worth doing right now —
> then learns from what you actually did instead. It is a time assistant that is not, itself,
> another job to manage.

**What to Test**

> - Capture a few tasks, by typing and by voice. Does it understand what you meant?
> - Check the Now tab through the day. Is the recommendation the thing you'd actually pick?
> - Swipe a task Done in Today and say how long it took. Does it ask too often, or not enough?
> - Do a different task than the one recommended, complete it, and see whether tomorrow's
>   recommendations shift.
> - Connect your calendar and Apple Health, and see whether the free-time figure looks right.
> - The widget: does it show the right next action, and does it stay current?

**Feedback email** — a mailbox you actually monitor.

**Beta App Review notes** — this is the part that gets builds rejected. Say all of it:

> **Demo account:** <email> / <password> — pre-loaded with tasks and a calendar, so the app is not
> empty on first launch.
>
> **Permissions.** Every permission is optional and independently requested, and the app works
> without any of them:
> - *Calendar* — reads events to find free blocks. Writes only an event the user has explicitly
>   approved on screen.
> - *Health* — reads sleep and activity to estimate the user's energy through the day. Never writes.
> - *Location (Always)* — used for geofences around places the user saves themselves, like Home or
>   Work, so an errand can be recommended when they are near where it can be done. No continuous
>   location history is recorded or stored. Background location can be declined and the app still
>   works.
> - *Microphone / Speech* — voice capture is transcribed to text, on-device where iOS supports it.
>   Raw audio is never stored or uploaded.
>
> **Subscriptions.** The "Upgrade to Premium" buttons are intentionally inert in this build; no
> purchase is implemented and nothing is charged. New accounts get full functionality.

---

## Human-only checklist

These need the Apple account holder and cannot be scripted from this repository.

- [ ] Create the app record in App Store Connect with bundle ID `com.aetheranalytics.timesense`
- [ ] Create the App Store Connect API key and place the `.p8` (see above)
- [ ] Publish the privacy policy at a public URL — content is in `docs/legal/privacy_policy.md` —
      and put that URL in App Store Connect
- [ ] Publish a support page at a public URL and put it in App Store Connect
- [ ] Replace the placeholder contact address in `docs/legal/privacy_policy.md`
- [ ] Create the demo account on production and note its credentials in the review notes
- [ ] Complete the App Privacy questionnaire using the answers above
- [ ] Confirm `PREMIUM_TEST_EMAILS` on Render covers whoever needs Premium during the beta, or
      accept that testers fall to Basic after their 14-day window
- [ ] Upload a build, add internal testers, then submit for Beta App Review for external testing

## Known gaps a tester will notice

- **Google sign-in is hidden.** The bundled `GoogleService-Info.plist` has no `CLIENT_ID`, because
  the Google provider has never been enabled for iOS in the Firebase console. Rather than offer a
  button that does nothing, the app hides it. Enable the provider, download the new plist, drop it
  in, and the button returns with no code change. Apple and email sign-in both work.
- **The Upgrade buttons do nothing.** StoreKit is not implemented. This is deliberate and is called
  out in the review notes above.
- **Android and web are not release-prepared.** iOS only.
