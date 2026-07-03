"""
TimeSense — Jira Ticket Status Updater

Moves Jira tickets to the correct status based on build progress.
Run this after completing each phase or set of tickets.

Usage:
    python scripts/transition_jira_tickets.py

Requires .env with JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY
"""

import json
import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"]
JIRA_EMAIL = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]
JIRA_PROJECT_KEY = os.environ["JIRA_PROJECT_KEY"]

AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

# Transition IDs for this project (from GET /rest/api/3/issue/{key}/transitions)
TRANSITION_IDS = {
    "to do": "11",
    "in progress": "21",
    "in review": "31",
    "done": "41",
}


def transition_ticket(issue_key: str, target_status: str) -> bool:
    """Move a ticket to the named status. Returns True on success."""
    target_lower = target_status.lower()
    tid = TRANSITION_IDS.get(target_lower)

    if tid is None:
        # Fall back to live API lookup
        r = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
            headers=HEADERS,
            auth=AUTH,
        )
        for t in r.json().get("transitions", []):
            if target_lower in t["name"].lower():
                tid = t["id"]
                break

    if tid is None:
        print(f"  ✗ {issue_key}: no transition matching '{target_status}'")
        return False

    resp = requests.post(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
        data=json.dumps({"transition": {"id": tid}}),
        headers=HEADERS,
        auth=AUTH,
    )
    if resp.status_code == 204:
        print(f"  ✓ {issue_key} → {target_status}")
        return True
    print(f"  ✗ {issue_key}: transition failed ({resp.status_code}) {resp.text[:200]}")
    return False


def get_all_project_tickets() -> list[dict]:
    """Return all tickets in the project ordered by creation date."""
    resp = requests.get(
        f"{JIRA_BASE_URL}/rest/api/3/search/jql",
        params={
            "jql": f"project = {JIRA_PROJECT_KEY} ORDER BY created ASC",
            "fields": "summary,status",
            "maxResults": 100,
        },
        headers=HEADERS,
        auth=AUTH,
    )
    resp.raise_for_status()
    return resp.json().get("issues", [])


def find_ticket(tickets: list[dict], fragment: str) -> dict | None:
    for t in tickets:
        if fragment in t["fields"]["summary"]:
            return t
    return None


def main() -> None:
    print("Fetching all project tickets...")
    tickets = get_all_project_tickets()
    print(f"Found {len(tickets)} tickets\n")

    # Current build state as of 2026-07-03:
    #   Phase 0–1 (TIME-001 through TIME-006): merged to main → Done
    #   Phase 2 (TIME-007 through TIME-010): PRs open, code complete → In Review
    #   Everything else: not started → To Do
    transitions_plan = [
        # Phase 0 — merged
        ("TIME-001", "Done"),
        # Phase 1 — all merged to main
        ("TIME-002", "Done"),
        ("TIME-003", "Done"),
        ("TIME-004", "Done"),
        ("TIME-005", "Done"),
        ("TIME-006", "Done"),
        # Phase 2 — PRs open, code complete and tested
        ("TIME-007", "In Review"),
        ("TIME-008", "In Review"),
        ("TIME-009", "In Review"),
        ("TIME-010", "In Review"),
    ]

    for fragment, target in transitions_plan:
        ticket = find_ticket(tickets, fragment)
        if ticket is None:
            print(f"  ? No ticket found containing '{fragment}' — skipping")
            continue
        key = ticket["key"]
        current = ticket["fields"]["status"]["name"]
        if current.lower() == target.lower():
            print(f"  – {key} ({fragment}) already '{current}' — skipping")
            continue
        transition_ticket(key, target)


if __name__ == "__main__":
    main()
