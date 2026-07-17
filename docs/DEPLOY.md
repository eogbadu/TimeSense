# Deploying TimeSense (Render)

This deploys the **backend** (API + Celery worker + beat) with managed **Postgres** and **Redis**, and
optionally the **web** companion, using the `render.yaml` Blueprint. The images are built from the
existing `backend/Dockerfile` and `web/Dockerfile`.

> **What only you can do:** create the Render account, attach a domain, and supply the secret *values*
> + register prod OAuth redirect URIs. This repo makes everything else ready. Cross-check the launch
> gate in [`docs/launch/release_checklist.md`](launch/release_checklist.md).

## 1. Create the Blueprint
1. Push this repo to GitHub (already there).
2. Render → **New → Blueprint** → pick the repo. Render reads `render.yaml` and proposes: `timesense-api`
   (web), `timesense-worker`, `timesense-beat`, `timesense-redis` (Key Value), and `timesense-db`
   (Postgres), plus the optional `timesense-web`.
3. Apply. The DB + Redis come up; the services build from Docker.

## 2. Set the secrets (the `timesense-secrets` group)
In the dashboard, open the **timesense-secrets** env group and fill every `sync:false` value (they are
listed with descriptions in the PRODUCTION block of `.env.example`). At minimum:
- `DATABASE_URL` — copy the Postgres **Internal Database URL** and change the scheme to
  `postgresql+asyncpg://…` (the async app needs that driver; `DATABASE_URL_SYNC` is auto-wired as plain
  `postgresql://` for Alembic).
- `TOKEN_ENCRYPTION_KEY` — a base64 32-byte Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- `CORS_ORIGINS` — your web origin, e.g. `https://app.yourdomain.com`.
- `FIREBASE_PROJECT_ID` + `FIREBASE_SERVICE_ACCOUNT_JSON`, `OPENAI_API_KEY`, Stripe live keys,
  `GOOGLE_MAPS_API_KEY`, and the OAuth client id/secret + **prod HTTPS** `*_REDIRECT_URI` for each
  provider you use, plus `OAUTH_WEB_SUCCESS_REDIRECT` / `OAUTH_WEB_FAILURE_REDIRECT`.

`SECRET_KEY` is auto-generated; `APP_ENV=production` and `APNS_USE_SANDBOX=false` are preset.

## 3. Migrations
The API service runs `alembic upgrade head` as its **preDeployCommand** before each release goes live
(the `RUN_MIGRATIONS=1` entrypoint path is the equivalent for plain Docker/compose). Verify the first
deploy's logs show the migration ran.

## 4. Domain + TLS
Attach your custom domain to `timesense-api` (e.g. `api.yourdomain.com`) and to `timesense-web`
(`app.yourdomain.com`); Render provisions TLS automatically.

## 5. Register prod OAuth redirect URIs
For every provider (Google/Gmail, Microsoft, Slack, Notion), add the **prod HTTPS** callback in that
provider's console and set the matching `*_REDIRECT_URI` secret:
`https://api.yourdomain.com/api/v1/integrations/<provider>/callback`. (See
[`integrations_setup.md`](integrations_setup.md).)

## 6. Point the clients at prod
- **Web** (`timesense-web`): set `NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com` and the
  `NEXT_PUBLIC_FIREBASE_*` values. These are **build-time** args — Render must pass them as Docker
  build args (their names match the `ARG`s in `web/Dockerfile`); a rebuild is needed after changing
  them. *Simpler alternative:* deploy `web/` to **Vercel** (native Next.js, no build-arg juggling).
- **iOS**: the Release build already points at `https://api.timesense.app` (`APIClient.swift`) — set it
  to your domain, or override per-build with the `API_BASE_URL` scheme env var. `aps-environment` flips
  to production for App Store/TestFlight automatically.

## 7. Verify
- `GET https://api.yourdomain.com/api/v1/health` → healthy.
- Worker + beat services show "running" (beat fires the schedule; the worker executes tasks).
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
