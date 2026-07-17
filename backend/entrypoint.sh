#!/bin/sh
# Container entrypoint. Set RUN_MIGRATIONS=1 on the web role so Alembic migrations are applied once
# on startup before the server boots; the worker/beat roles share this image but leave it unset.
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "[entrypoint] applying database migrations (alembic upgrade head)…"
    alembic upgrade head
fi

exec "$@"
