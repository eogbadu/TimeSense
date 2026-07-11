"""One-off cleanup: remove duplicate Jira issues created by the get_existing_tickets() pagination bug
in create_jira_tickets.py (it only read the first page, so full runs re-created every ticket).

Keeps exactly ONE canonical issue per distinct summary (prefer the oldest Done copy; else the oldest
copy overall) and deletes the rest. Dry-run by default — pass --execute to actually delete.

    python scripts/dedupe_jira_tickets.py            # dry-run: report only
    python scripts/dedupe_jira_tickets.py --execute  # delete the duplicates

Safe/resumable: a missing issue (404) on delete is treated as already-gone.
"""
from __future__ import annotations

import collections
import importlib.util
import os
import sys
import tempfile
import time

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("cjt", os.path.join(_HERE, "create_jira_tickets.py"))
cjt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cjt)

BASE, AUTH, HEADERS, PROJECT = cjt.JIRA_BASE_URL, cjt.AUTH, cjt.HEADERS, cjt.JIRA_PROJECT_KEY
SCRATCH = tempfile.gettempdir()


def fetch_all() -> list[dict]:
    """Paginate the ENTIRE project (following nextPageToken — the bug the old code missed)."""
    out, token, pages = [], None, 0
    while True:
        params = {"jql": f"project={PROJECT} ORDER BY created ASC", "maxResults": 100,
                  "fields": "summary,status,created"}
        if token:
            params["nextPageToken"] = token
        r = requests.get(f"{BASE}/rest/api/3/search/jql", auth=AUTH, headers=HEADERS, params=params)
        r.raise_for_status()
        d = r.json()
        for i in d.get("issues", []):
            f = i["fields"]
            out.append({"key": i["key"], "summary": f["summary"] or "",
                        "status": f["status"]["name"], "created": f.get("created") or ""})
        token = d.get("nextPageToken")
        pages += 1
        if not token or pages > 80:
            break
    if token:
        raise SystemExit("ABORT: pagination did not drain (more pages than expected) — not safe to delete.")
    return out


def choose_keep(group: list[dict]) -> dict:
    """Canonical to keep for one summary: oldest Done copy, else oldest copy overall."""
    done = [g for g in group if g["status"] == "Done"]
    pool = done or group
    return min(pool, key=lambda g: g["created"])


def main() -> None:
    execute = "--execute" in sys.argv
    issues = fetch_all()
    total = len(issues)
    by_summary: dict[str, list[dict]] = collections.defaultdict(list)
    for it in issues:
        by_summary[it["summary"]].append(it)
    distinct = len(by_summary)

    keep_keys, delete_keys = set(), []
    for summary, group in by_summary.items():
        keep = choose_keep(group)
        keep_keys.add(keep["key"])
        delete_keys.extend(g["key"] for g in group if g["key"] != keep["key"])

    # ---- safety guards ----
    # (fetch_all already aborts if pagination doesn't fully drain; and choose_keep always keeps one
    # copy per fetched summary, so even a partial fetch can only ever delete *extra* copies, never a
    # canonical — the run is safely resumable. So no absolute count floor is needed.)
    if len(keep_keys) != distinct:
        raise SystemExit("ABORT: keep count != distinct summaries.")
    if len(delete_keys) != total - distinct:
        raise SystemExit("ABORT: delete count != total - distinct.")
    if keep_keys & set(delete_keys):
        raise SystemExit("ABORT: a kept key is also in the delete set.")

    print(f"project={PROJECT}  total={total}  distinct_summaries={distinct}")
    print(f"KEEP {len(keep_keys)}  DELETE {len(delete_keys)}\n")
    dist = collections.Counter(len(g) for g in by_summary.values())
    print("copies-per-summary (count: #summaries):", dict(sorted(dist.items())))

    del_file = os.path.join(SCRATCH, "jira_delete_keys.txt")
    with open(del_file, "w") as fh:
        fh.write("\n".join(delete_keys))
    print(f"\nfull delete list written to {del_file}")

    if not execute:
        print("\nDRY-RUN — nothing deleted. Re-run with --execute to delete.")
        # show a few representative keeps
        for s in list(by_summary)[:5]:
            k = choose_keep(by_summary[s])
            print(f"  keep {k['key']} ({k['status']})  x{len(by_summary[s])}  {s[:50]}")
        return

    print(f"\nEXECUTING: deleting {len(delete_keys)} issues ...")
    gone = failed = 0
    for n, key in enumerate(delete_keys, 1):
        while True:
            r = requests.delete(f"{BASE}/rest/api/3/issue/{key}", auth=AUTH, headers=HEADERS)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", "5"))
                print(f"  429 rate-limited — sleeping {wait}s")
                time.sleep(wait)
                continue
            break
        if r.status_code in (204, 404):
            gone += 1
        else:
            failed += 1
            print(f"  ✗ {key}: {r.status_code} {r.text[:120]}")
        if n % 100 == 0:
            print(f"  ...{n}/{len(delete_keys)} (deleted={gone} failed={failed})")
        time.sleep(0.06)
    print(f"\nDONE: deleted/absent={gone}  failed={failed}")


if __name__ == "__main__":
    main()
