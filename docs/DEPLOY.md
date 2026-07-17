# Deploying TimeSense (Render)

This deploys the **backend** (API + a single Celery worker with beat embedded) with managed **Postgres**
and **Redis**, using the `render.yaml` Blueprint (images built from `backend/Dockerfile`). The **web**
companion goes on **Vercel** (free, native Next.js) — see §6. A lean always-on setup is roughly
**~$20/mo** (API Starter + worker Starter + small Postgres; Redis on the free tier; web free on Vercel).

> **What only you can do:** create the Render account, attach a domain, and supply the secret *values*
> + register prod OAuth redirect URIs. This repo makes everything else ready. Cross-check the launch
> gate in [`docs/launch/release_checklist.md`](launch/release_checklist.md).

## 1. Create the Blueprint
1. Push this repo to GitHub (already there).
2. Render → **New → Blueprint** → pick the repo. Render reads `render.yaml` and proposes: `timesense-api`
   (web), `timesense-worker` (runs the worker **with beat embedded** — keep it at 1 instance),
   `timesense-redis` (Key Value, free), and `timesense-db` (Postgres).
3. Apply. The DB + Redis come up; the services build from Docker.

## 2. Set the secrets (the `timesense-secrets` group)
The database + Redis URLs are wired automatically (from the managed Postgres and Redis), so **nothing is
needed to make the API boot**. In the dashboard, open the **timesense-secrets** env group and fill the
`sync:false` values you actually use (all listed in the PRODUCTION block of `.env.example`) — the app
runs without them but features degrade (no auth without Firebase, no LLM without OpenAI, etc.):
- `TOKEN_ENCRYPTION_KEY` — a base64 32-byte Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`); if unset it's derived from `SECRET_KEY`.
- `CORS_ORIGINS` — your web origin, e.g. `https://app.yourdomain.com`.
- `FIREBASE_PROJECT_ID` + `FIREBASE_SERVICE_ACCOUNT_JSON`, `OPENAI_API_KEY`, Stripe live keys,
  `GOOGLE_MAPS_API_KEY`, and the OAuth client id/secret + **prod HTTPS** `*_REDIRECT_URI` for each
  provider you use, plus `OAUTH_WEB_SUCCESS_REDIRECT` / `OAUTH_WEB_FAILURE_REDIRECT`.

`SECRET_KEY` is auto-generated; `APP_ENV=production` and `APNS_USE_SANDBOX=false` are preset.

## 3. Migrations
The API service runs `alembic upgrade head` as its **preDeployCommand** before each release goes live
(the `RUN_MIGRATIONS=1` entrypoint path is the equivalent for plain Docker/compose). Verify the first
deploy's logs show the migration ran. The worker runs beat embedded (`celery worker --beat`), so the
scheduled jobs (morning check-ins, the ~30-min push scan, weekly insights) still run — just keep the
worker at **one instance** while beat is embedded.

## 4. Domain + TLS
Attach your custom domain to `timesense-api` (e.g. `api.yourdomain.com`) and to `timesense-web`
(`app.yourdomain.com`); Render provisions TLS automatically.

## 5. Register prod OAuth redirect URIs
For every provider (Google/Gmail, Microsoft, Slack, Notion), add the **prod HTTPS** callback in that
provider's console and set the matching `*_REDIRECT_URI` secret:
`https://api.yourdomain.com/api/v1/integrations/<provider>/callback`. (See
[`integrations_setup.md`](integrations_setup.md).)

## 6. Deploy the web companion on Vercel + point the clients at prod
- **Web → Vercel** (free, native Next.js): New Project → import the repo → **Root Directory = `web`**.
  Set env vars `NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com` and the `NEXT_PUBLIC_FIREBASE_*`
  values, then deploy. Add your web domain (e.g. `app.yourdomain.com`) and set that origin in the
  backend's `CORS_ORIGINS` + `OAUTH_WEB_*` redirects. (If you'd rather self-host it on Render instead,
  `web/Dockerfile` is still there — add a `type: web` Docker service with the `NEXT_PUBLIC_*` build args.)
- **iOS**: the Release build already points at `https://api.timesense.app` (`APIClient.swift`) — set it
  to your domain, or override per-build with the `API_BASE_URL` scheme env var. `aps-environment` flips
  to production for App Store/TestFlight automatically.

## 7. Verify
- `GET https://api.yourdomain.com/api/v1/health` → healthy.
- The worker service shows "running" (it runs beat embedded — fires the schedule and executes tasks).
- A round-trip: sign in on web → connect an integration (OAuth returns to the web app).

## Still your responsibility (from the release checklist)
- **Rotate the previously-exposed Android `google-services.json` / API key** and restrict it before any
  public Android build.
- OpenAI billing enabled; Google Maps key restricted; Sentry DSN (optional) set.
- App Store / Play submissions (listings drafted in `docs/launch/`); privacy policy human review + ToS
  published.

## Scaling notes / follow-ups (not needed for a first deploy)
- The rate limiter is **in-process** — fine for a single API instance; if you scale to >1 replica it
  needs a Redis-backed limiter (a deferred follow-up).
- No CI/CD yet (GitHub Actions running pytest/builds is a deferred follow-up).
