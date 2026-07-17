# Integrations setup (Google Calendar · Gmail · Outlook · Slack)

The OAuth code for every integration is already built. To make a provider **live**, you only need to
create an OAuth app in that provider's console, register its **redirect URI**, and put the resulting
**client id / secret** into the **root `.env`** (`TimeSense/.env`, not `backend/.env`). The moment the
credentials are present and the backend is restarted, the provider's `authorize` endpoint stops
returning `503` and **Settings ▸ Connections ▸ _[provider]_ → Connect** works.

> Connecting is a **Premium** feature. During dev, add your sign-in email to `PREMIUM_TEST_EMAILS`
> (see `.env.example`) so you're treated as Premium past the 14-day intro trial.

The redirect URI is the **backend callback** (which then deep-links back into the app). It must match
the `*_REDIRECT_URI` value in `.env` **exactly** in both the provider console and the env file.

---

## Google Calendar **and** Gmail — one Google Cloud OAuth app covers both

They share a single OAuth client (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`) but use two redirect
URIs and different scopes.

1. **Google Cloud Console** → create an **OAuth 2.0 Client ID** (application type: *Web application*).
2. **Enable APIs**: Google Calendar API **and** Gmail API in the project.
3. **Authorized redirect URIs** — add **both**:
   - `http://localhost:8000/api/v1/integrations/google/callback`  (Calendar)
   - `http://localhost:8000/api/v1/integrations/gmail/callback`   (Gmail)
4. **OAuth consent screen**: add the scopes and add **yourself as a Test user** (both scopes are
   sensitive/restricted, so an unverified app blocks non-test users):
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/gmail.readonly`
5. `.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   # GMAIL_REDIRECT_URI / GOOGLE_REDIRECT_URI default to the localhost callbacks above
   ```

## Outlook / Microsoft

1. **Azure Portal** → App registrations → new registration.
2. **Redirect URI** (platform: *Web*): `http://localhost:8000/api/v1/integrations/microsoft/callback`
3. **API permissions** (delegated): `Calendars.ReadWrite`. Create a **client secret**.
4. `.env`:
   ```
   MICROSOFT_CLIENT_ID=...
   MICROSOFT_CLIENT_SECRET=...
   ```

## Slack

1. **api.slack.com** → create an app → **OAuth & Permissions**.
2. **Bot token scopes**: `channels:history`, `channels:read`, `groups:history`.
3. **Redirect URL**: `.../integrations/slack/callback` — **Slack requires HTTPS**, so plain
   `http://localhost` is rejected. Use a tunnel (`ngrok http 8000`) and register the resulting
   `https://…/api/v1/integrations/slack/callback`, then set `SLACK_REDIRECT_URI` to it.
4. `.env`:
   ```
   SLACK_CLIENT_ID=...
   SLACK_CLIENT_SECRET=...
   SLACK_SIGNING_SECRET=...
   SLACK_REDIRECT_URI=https://<your-ngrok-subdomain>/api/v1/integrations/slack/callback
   ```

---

## After setting credentials

1. Put the vars in the **root `.env`** and restart the backend:
   ```
   cd backend && python run_dev.py
   ```
2. In the app: **Settings ▸ Connections ▸ _[provider]_ → Connect**.

## Two gotchas

- **Simulator vs. physical device.** `http://localhost:8000` works **only on the iOS Simulator** (the
  consent browser runs on your Mac). On a **physical device**, `localhost` is the phone, so the OAuth
  callback can't reach your Mac — point every `*_REDIRECT_URI` at a tunnel/deployed URL and register
  **that** URL in each provider console.
- **Slack forces HTTPS.** The simplest way to make **all four** work at once is to run the backend
  behind a single `ngrok` HTTPS URL and use it for every `*_REDIRECT_URI` (updating each `.env` value
  and registering the matching URL in each console).

## How the flow works (reference)

`GET /api/v1/integrations/{provider}/authorize` (Premium) returns the provider consent URL carrying a
signed `state`. The app opens it in `ASWebAuthenticationSession`; after consent the provider redirects
to `GET /api/v1/integrations/{provider}/callback`, which verifies `state`, exchanges the code for
tokens **server-side** (the client secret never touches the device), stores them **encrypted at rest**,
and deep-links back to `timesense://integrations/connected`. `is_configured()` (client id + secret
present) is what flips `authorize` from `503` to live.
