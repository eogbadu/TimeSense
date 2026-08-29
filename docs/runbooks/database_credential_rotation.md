# Runbook — rotating the production database credential (Render)

Written 2026-08-29 after doing it the slow way. Following this takes ~10 minutes; not knowing the
trap below cost about an hour.

## The trap, read this first

`render.yaml` declares the database URL as wired from the managed Postgres:

```yaml
- key: DATABASE_URL
  fromDatabase: { name: timesense-db, property: connectionString }
```

**The running services do not work that way.** They hold **literal** `DATABASE_URL` and
`DATABASE_URL_SYNC` values in their dashboard environment. Blueprint wiring is resolved when a
service is created or the blueprint is synced; after that the dashboard value wins and never
re-resolves.

Consequence: creating a new default credential and redeploying does **nothing**. The service simply
re-reads the same literal string and reconnects as the old user. We redeployed three times before
spotting this.

## Facts that matter

- **`DATABASE_URL_SYNC` is never read.** It is declared in `app/core/config.py` and used nowhere;
  `migrations/env.py` builds alembic's URL from `database_url`. Update it anyway so it isn't a
  landmine pointing at a deleted role.
- **Paste Render's connection string verbatim.** `config.py` coerces `postgres://` /
  `postgresql://` to `postgresql+asyncpg://`. Do not hand-edit the scheme.
- **Use the *Internal* Database URL** for services running inside Render. External is for your
  laptop.
- **A bad URL means the API does not start at all.** `backend/entrypoint.sh` runs
  `alembic upgrade head` under `set -e` before exec'ing the server, with `RUN_MIGRATIONS=1` on the
  api service. There is no degraded mode — it either boots or it doesn't.

## Procedure

1. **Create the new credential.** Render → `timesense-db` → Credential Rotation →
   *+ New default credential*. Name it with the date, e.g. `timesense_user_20260829`, so the row to
   delete is never ambiguous. Nothing depends on the username — it appears nowhere in the repo.
2. **Confirm the Internal Database URL now contains the new username.**
3. **Edit the env vars on BOTH services** (`timesense-api`, `timesense-worker`): set `DATABASE_URL`
   and `DATABASE_URL_SYNC` to that internal URL. Editing, not adding — they already exist.
4. **Redeploy both services.**
5. **Verify before deleting anything** (see below). Do not skip this.
6. **Delete the old credential.** This is the step that actually invalidates the old password.
   Everything before it is just making this safe.

## Verification

Connect with the OLD credential (still valid at this point) and check who holds connections.
`pg_stat_activity` is ground truth; the dashboard's OPEN CONNECTIONS column can lag.

```sql
SELECT usename AS db_user, count(*) AS conns, state,
       max(backend_start)::timestamp(0) AS newest
FROM pg_stat_activity
WHERE datname = 'timesense' AND usename IS NOT NULL AND pid <> pg_backend_pid()
GROUP BY usename, state ORDER BY usename;
```

`pid <> pg_backend_pid()` excludes your own psql session — without it you will always see a
connection on whichever credential you connected with and conclude the migration failed.

**Green light: zero connections on the old role.** A single lingering connection is not
automatically a blocker — check whether anything *reconnects*:

```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname='timesense' AND usename='<old_role>' AND pid <> pg_backend_pid();
```

Wait longer than the Celery beat interval (the shortest is `send-appointment-reminders`, every 2
minutes). If nothing comes back on the old role, the cutover is complete. If it reconnects, a
service still holds the old literal value — go back to step 3.

Terminating an `idle` or `idle in transaction` session is safe. An `idle in transaction` session is
worth killing regardless: it holds locks and blocks vacuum.

## Afterwards

- Confirm the old credential is genuinely dead by attempting to connect with it and expecting a
  rejection. That is the proof the exposure is closed.
- If the old credential leaked (e.g. pasted into a chat or a log), deletion is the only remedy —
  changing the default does not revoke it.
