#!/usr/bin/env python3
"""
Move a Jira ticket to a new status.

Usage:
  python scripts/move_ticket.py TIME-13 "In Progress"
  python scripts/move_ticket.py TIME-13 done
  python scripts/move_ticket.py TIME-7 TIME-12 done          # bulk range

Accepted status names (case-insensitive):
  todo / to do / backlog
  inprogress / in progress / started
  inreview / in review / review
  done / complete / closed
"""

import json
import os
import sys

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://eogbadu.atlassian.net")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "TIME")

AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

# Transition IDs from GET /rest/api/3/issue/{key}/transitions
TRANSITION_IDS = {
    "todo": "11",
    "inprogress": "21",
    "inreview": "31",
    "done": "41",
}

STATUS_ALIASES = {
    "todo": "todo",
    "to do": "todo",
    "backlog": "todo",
    "inprogress": "inprogress",
    "in progress": "inprogress",
    "started": "inprogress",
    "inreview": "inreview",
    "in review": "inreview",
    "review": "inreview",
    "done": "done",
    "complete": "done",
    "closed": "done",
}


def resolve_status(raw: str) -> str:
    key = raw.strip().lower()
    canonical = STATUS_ALIASES.get(key)
    if canonical is None:
        print(f"Unknown status '{raw}'. Use: todo | in progress | in review | done")
        sys.exit(1)
    return canonical


def get_transitions(issue_key: str) -> dict[str, str]:
    r = requests.get(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
        auth=AUTH,
        headers=HEADERS,
    )
    if r.status_code != 200:
        print(f"  ERROR fetching transitions for {issue_key}: {r.status_code}")
        return {}
    return {t["name"].lower(): t["id"] for t in r.json().get("transitions", [])}


def transition_ticket(issue_key: str, status_canonical: str) -> bool:
    transition_id = TRANSITION_IDS.get(status_canonical)
    if transition_id is None:
        print(f"  No transition ID mapped for '{status_canonical}'")
        return False
    r = requests.post(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
        auth=AUTH,
        headers=HEADERS,
        data=json.dumps({"transition": {"id": transition_id}}),
    )
    if r.status_code == 204:
        return True
    print(f"  ERROR {r.status_code}: {r.text[:200]}")
    return False


def parse_jira_key(project_key: str, raw: str) -> str:
    """Accept 'TIME-13' or plain '13'."""
    raw = raw.strip()
    if raw.startswith(project_key + "-"):
        return raw
    if raw.isdigit():
        return f"{project_key}-{raw}"
    return raw


def get_current_status(issue_key: str) -> str:
    r = requests.get(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
        auth=AUTH,
        headers=HEADERS,
        params={"fields": "status"},
    )
    if r.status_code == 200:
        return r.json()["fields"]["status"]["name"]
    return "unknown"


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    # Detect bulk range: TIME-7 TIME-12 done
    if len(args) == 3 and args[0].startswith(JIRA_PROJECT_KEY) and args[1].startswith(JIRA_PROJECT_KEY):
        start = int(args[0].split("-")[1])
        end = int(args[1].split("-")[1])
        status_canonical = resolve_status(args[2])
        keys = [f"{JIRA_PROJECT_KEY}-{i}" for i in range(start, end + 1)]
    else:
        status_canonical = resolve_status(args[-1])
        keys = [parse_jira_key(JIRA_PROJECT_KEY, k) for k in args[:-1]]

    status_label = {
        "todo": "To Do",
        "inprogress": "In Progress",
        "inreview": "In Review",
        "done": "Done",
    }[status_canonical]

    print(f"Moving {len(keys)} ticket(s) → {status_label}\n")
    for key in keys:
        current = get_current_status(key)
        ok = transition_ticket(key, status_canonical)
        symbol = "✓" if ok else "✗"
        print(f"  {symbol}  {key}  ({current} → {status_label})")


if __name__ == "__main__":
    main()
