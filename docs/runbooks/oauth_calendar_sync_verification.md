# Runbook — Verify OAuth Calendar Sync (Google / Outlook) end-to-end

**What this covers:** confirming that a calendar connected in-app via OAuth (Google or Microsoft/Outlook)
actually flows into the Smart Plan in production — i.e. that TIME-277's sync writes `SyncedCalendarEvent`
rows and TIME-276's plan surfaces them.

**Why it needs a human:** the sync makes real calls to Google/Microsoft with your OAuth app
credentials and runs on the Celery worker. The automated tests mock the network
(`tests/test_calendar_providers_http.py`, `tests/test_calendar_oauth_sync.py`), so the JSON parsing,
error handling, token refresh, and the full `sync_all` DB path are all verified — but the live
credential + network round-trip can only be confirmed against the real services.

---

## 0. Prerequisites (one-time)

| Provider | Env vars required | Status (as of writing) |
|---|---|---|
| Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | **configured** |
| Microsoft / Outlook | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_REDIRECT_URI` | **client id/secret empty** — Outlook sync is inert until these are set |

- The OAuth app's redirect URI must be registered with the provider and match `*_REDIRECT_URI`.
- Google scope must include `.../auth/calendar.events` and be consented with `access_type=offline`
  (so a **refresh token** is issued — required for the periodic sync to keep working).
- Check presence (never print values):
  ```bash
  cd backend && python -c "from app.core.config import settings; \
  print('google', bool(settings.google_client_id and settings.google_client_secret)); \
  print('microsoft', bool(settings.microsoft_client_id and settings.microsoft_client_secret))"
  ```

## 1. Connect a calendar (device under test / API)

Complete the in-app OAuth connect flow for Google (Settings ▸ Connections), or drive it directly:
`GET /api/v1/calendar/google/authorize` → consent → callback stores the encrypted tokens.

Confirm the integration is active:
```bash
# as an admin, or check the DB directly
psql "$DATABASE_URL" -c "select provider, is_active, token_expires_at from calendar_integrations;"
```

## 2. Trigger an immediate sync (on-demand path)

No need to wait for the beat job — hit the on-demand endpoint as the connected user:
```bash
curl -sS -X POST https://<api-host>/api/v1/calendar/oauth/sync \
  -H "Authorization: Bearer <firebase-id-token>" | jq
# => {"synced": <N>}   # N = timed events written (all-day events are skipped by design)
```
- `synced > 0` with events on your calendar in the next ~36h → **success**.
- `synced == 0` with events present → see Troubleshooting.

## 3. Confirm the events landed and reach the plan

```bash
# raw store
psql "$DATABASE_URL" -c \
  "select source, title, starts_at from synced_calendar_events where source in ('google','microsoft') order by starts_at;"

# the unified plan the iOS app renders (kind=\"event\" rows are the meetings)
curl -sS "https://<api-host>/api/v1/timeline/today/plan?date=$(date +%F)" \
  -H "Authorization: Bearer <firebase-id-token>" | jq '.[] | {kind, title, start}'
```
On device: open **Today** → the meeting appears as a read-only "Calendar" row in the Smart Plan, and
"usable time" reflects it (TIME-275).

## 4. Confirm the periodic job runs

The Celery beat entry `sync-oauth-calendars` runs `timesense.sync_oauth_calendars` every 30 min.
- Ensure the worker is deployed with beat enabled (the combined worker service; see `docs/DEPLOY.md`).
- Watch a cycle:
  ```bash
  # worker logs should show the task firing on the :00/:30 boundary
  # then, without calling the on-demand endpoint, a fresh calendar change appears within ~30 min:
  psql "$DATABASE_URL" -c "select max(updated_at) from synced_calendar_events where source='google';"
  ```

## 5. Token-refresh check (optional, ~1h)

Access tokens expire (~1h for Google). Leave the integration idle past expiry, then trigger step 2
again — it should still return `synced > 0`. The service refreshes the access token once on a `401`
(`refresh_access_token`) and retries; a successful sync after expiry confirms refresh works. Verify the
stored token rotated:
```bash
psql "$DATABASE_URL" -c "select provider, token_expires_at from calendar_integrations;"
```

---

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `synced == 0`, events exist | all events are all-day (skipped by design) | add a timed event and retry |
| `401`/connect fails | redirect URI mismatch or missing scope | fix the OAuth app config; reconnect |
| Sync works once, fails after ~1h | no refresh token stored | reconnect with `access_type=offline` + `prompt=consent` |
| Outlook never syncs | `MICROSOFT_CLIENT_ID/SECRET` empty | set the Microsoft OAuth app creds |
| Beat never fires | worker running without `--beat`, or Redis down | check the worker service config / Redis |

## Sign-off

- [ ] On-demand `POST /calendar/oauth/sync` returns `synced > 0`
- [ ] `synced_calendar_events` has `source='google'` (and `'microsoft'` once configured) rows
- [ ] `GET /timeline/today/plan` shows the meeting as a `kind="event"` row; usable time reflects it
- [ ] A change appears within ~30 min via the beat job (no manual trigger)
- [ ] Sync still succeeds after token expiry (refresh works)
