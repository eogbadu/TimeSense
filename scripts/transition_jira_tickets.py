"""
TimeSense — Jira Ticket Status Updater

Moves Jira tickets to the correct status based on build progress.
Run this after completing each phase or set of tickets.

Usage:
    python scripts/transition_jira_tickets.py

Requires .env with JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY
"""

import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE_URL = os.environ["JIRA_BASE_URL"]
JIRA_EMAIL = os.environ["JIRA_EMAIL"]
JIRA_API_TOKEN = os.environ["JIRA_API_TOKEN"]
JIRA_PROJECT_KEY = os.environ["JIRA_PROJECT_KEY"]

AUTH = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def get_transitions(issue_key: str) -> dict[str, str]:
    """Return {transition_name_lower: transition_id} for an issue."""
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions"
    resp = requests.get(url, headers=HEADERS, auth=AUTH)
    resp.raise_for_status()
    return {t["name"].lower(): t["id"] for t in resp.json().get("transitions", [])}


def transition_ticket(issue_key: str, target_status: str) -> bool:
    """Move a ticket to the named status. Returns True on success."""
    transitions = get_transitions(issue_key)
    target_lower = target_status.lower()

    # Jira transition names vary (e.g. "In Progress", "Done", "To Do")
    # Try exact match first, then partial
    tid = transitions.get(target_lower)
    if tid is None:
        for name, t_id in transitions.items():
            if target_lower in name:
                tid = t_id
                break

    if tid is None:
        print(f"  ✗ {issue_key}: no transition matching '{target_status}'. Available: {list(transitions.keys())}")
        return False

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions"
    payload = json.dumps({"transition": {"id": tid}})
    resp = requests.post(url, data=payload, headers=HEADERS, auth=AUTH)
    if resp.status_code == 204:
        print(f"  ✓ {issue_key} → {target_status}")
        return True
    else:
        print(f"  ✗ {issue_key}: transition failed ({resp.status_code}) {resp.text[:200]}")
        return False


def get_all_project_tickets() -> list[dict]:
    """Return all tickets in the project, ordered by key."""
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    payload = json.dumps({
        "jql": f"project = {JIRA_PROJECT_KEY} ORDER BY created ASC",
        "fields": ["summary", "status"],
        "maxResults": 100,
    })
    resp = requests.post(url, data=payload, headers=HEADERS, auth=AUTH)
    resp.raise_for_status()
    return resp.json().get("issues", [])


def find_ticket_by_summary_fragment(tickets: list[dict], fragment: str) -> dict | None:
    for t in tickets:
        if fragment in t["fields"]["summary"]:
            return t
    return None


def main():
    print("Fetching all project tickets...")
    tickets = get_all_project_tickets()
    print(f"Found {len(tickets)} tickets\n")

    # Map summary fragment -> (target_status)
    # Phase 0 — Done (bootstrap complete, merged to main)
    # Phase 1 — Done (TIME-002 through TIME-006, all merged)
    # Phase 2 TIME-007 — In Progress (just built, PR open)
    # Phase 2 TIME-008 through TIME-010 — To Do (not yet started)
    # All others — To Do

    transitions_plan = [
        # (summary_fragment, target_status)
        ("TIME-001", "Done"),   # Phase 0: bootstrap complete
        ("TIME-002", "Done"),   # FastAPI setup complete
        ("TIME-003", "Done"),   # Database models + Alembic
        ("TIME-004", "Done"),   # Redis + Celery workers
        ("TIME-005", "Done"),   # Firebase Auth
        ("TIME-006", "Done"),   # Core security middleware
        ("TIME-007", "In Progress"),  # User/Profile model — PR open
    ]

    for fragment, target in transitions_plan:
        ticket = find_ticket_by_summary_fragment(tickets, fragment)
        if ticket is None:
            print(f"  ? No ticket found with summary containing '{fragment}' — skipping")
            continue
        issue_key = ticket["key"]
        current_status = ticket["fields"]["status"]["name"]
        if current_status.lower() == target.lower():
            print(f"  – {issue_key} ({fragment}) already '{current_status}' — skipping")
            continue
        transition_ticket(issue_key, target)


if __name__ == "__main__":
    main()
