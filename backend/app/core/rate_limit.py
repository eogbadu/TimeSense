"""
Lightweight in-process rate limiting (TIME-056).

A fixed-window limiter keyed by (name, caller) where caller is the auth token if present else the
client IP. Used as a FastAPI dependency on abuse-prone endpoints. Single-instance / in-memory —
a Redis-backed limiter for multi-instance deploys is a follow-up.
"""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    def __init__(self, times: int, seconds: int, name: str) -> None:
        self.times = times
        self.seconds = seconds
        self.name = name
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _key(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        client = request.client.host if request.client else "unknown"
        return f"{self.name}:{auth or client}"

    async def __call__(self, request: Request) -> None:
        key = self._key(request)
        now = time.monotonic()
        window_start = now - self.seconds
        hits = [t for t in self._hits[key] if t > window_start]
        if len(hits) >= self.times:
            retry_after = int(self.seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(retry_after)},
            )
        hits.append(now)
        self._hits[key] = hits


# Shared, stateful limiter instances.
_capture_limiter = RateLimiter(settings.rate_limit_capture_per_minute, 60, "capture")
_account_delete_limiter = RateLimiter(settings.rate_limit_account_delete_per_hour, 3600, "account_delete")


# Plain async-function dependencies — FastAPI injects Request into these (it does not into a
# class-instance __call__, which it would treat `request` as a required field).
async def capture_rate_limit(request: Request) -> None:
    await _capture_limiter(request)


async def account_delete_rate_limit(request: Request) -> None:
    await _account_delete_limiter(request)


def _reset_all() -> None:
    """Clear all limiter state — used by tests to keep them isolated."""
    _capture_limiter._hits.clear()
    _account_delete_limiter._hits.clear()
