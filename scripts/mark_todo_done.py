"""One-off: transition the leftover "To Do" tickets to Done.

After the duplicate cleanup (see dedupe_jira_tickets.py / known_issues.md) the project had 205 distinct
tickets, 53 of them stuck in "To Do" — the canonical copies of logical tickets TIME-118..170 whose
move-to-Done historically landed on a (now-deleted) duplicate. All 53 are verified shipped work, so we
mark them Done.

    python scripts/mark_todo_done.py            # dry-run: list the To Do tickets
    python scripts/mark_todo_done.py --execute  # transition them to Done

Idempotent: an already-Done ticket has no "done" transition and is skipped.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import time

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("cjt", os.path.join(_HERE, "create_jira_tickets.py"))
cjt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cjt)

BASE, AUTH, HEADERS, PROJECT = cjt.JIRA_BASE_URL, cjt.AUTH, cjt.HEADERS, cjt.JIRA_PROJECT_KEY
EXPECTED = 53


def fetch_todo() -> list[tuple[str, str]]:
    out, token, pages = [], None, 0
    while True:
        params = {"jql": f'project={PROJECT} AND status="To Do" ORDER BY created ASC',
                  "maxResults": 100, "fields": "summary"}
        if token:
            params["nextPageToken"] = token
        r = requests.get(f"{BASE}/rest/api/3/search/jql", auth=AUTH, headers=HEADERS, params=params)
        r.raise_for_status()
        d = r.json()
        out.extend((i["key"], i["fields"]["summary"] or "") for i in d.get("issues", []))
        token = d.get("nextPageToken")
        pages += 1
        if not token or pages > 20:
            break
    if token:
        raise SystemExit("ABORT: To Do pagination did not drain.")
    return out


def main() -> None:
    execute = "--execute" in sys.argv
    todo = fetch_todo()

    def lognum(kv: tuple[str, str]) -> int:
        m = re.match(r"TIME-(\d+)", kv[1])
        return int(m.group(1)) if m else 9999

    todo.sort(key=lognum)
    print(f"{len(todo)} tickets currently in To Do:\n")
    for k, s in todo:
        print(f"  {k:10s} | {s[:70]}")

    if len(todo) != EXPECTED:
        raise SystemExit(f"\nABORT: expected {EXPECTED} To Do tickets, found {len(todo)} — "
                         "review before transitioning.")

    if not execute:
        print(f"\nDRY-RUN — nothing changed. Re-run with --execute to mark all {len(todo)} Done.")
        return

    print(f"\nEXECUTING: transitioning {len(todo)} tickets to Done ...")
    done = failed = 0
    for k, _ in todo:
        if cjt.transition_ticket(k, "done"):
            done += 1
        else:
            failed += 1
            print(f"  ✗ {k}: transition to Done failed")
        time.sleep(0.05)
    print(f"\nDONE: transitioned={done}  failed={failed}")


if __name__ == "__main__":
    main()
