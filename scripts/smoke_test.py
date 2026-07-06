#!/usr/bin/env python3
"""
TimeSense beta smoke test — quick liveness + auth-gate checks against a running backend.

This is the fast "is the server alive and sane?" check. The full behavioral guarantee comes from the
pytest suite (`cd backend && pytest`); this verifies a *deployed/running* instance responds and that
protected routes are actually gated. Manual device flows are in docs/launch/beta_smoke_test.md.

Usage:
    python scripts/smoke_test.py                       # checks http://localhost:8000
    BASE=http://ekeles-MacBook-Pro.local:8000 python scripts/smoke_test.py
"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("BASE", "http://localhost:8000").rstrip("/")


def _status(path: str, method: str = "GET") -> int:
    req = urllib.request.Request(f"{BASE}{path}", method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


CHECKS = [
    ("health is 200", "/api/v1/health", "GET", {200}),
    ("now requires auth", "/api/v1/now", "GET", {401, 403}),
    ("today requires auth", "/api/v1/timeline/today", "GET", {401, 403}),
    ("capture requires auth", "/api/v1/capture", "POST", {401, 403, 422}),
    ("tasks require auth", "/api/v1/tasks", "GET", {401, 403}),
    ("admin requires auth", "/api/v1/admin/metrics", "GET", {401, 403}),
]


def main() -> int:
    print(f"Smoke testing {BASE}\n")
    failures = 0
    for label, path, method, ok in CHECKS:
        code = _status(path, method)
        passed = code in ok
        failures += 0 if passed else 1
        print(f"  [{'PASS' if passed else 'FAIL'}] {label:26} {method} {path} -> {code}")
    print()
    if failures:
        print(f"❌ {failures} check(s) failed.")
        return 1
    print("✅ All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
