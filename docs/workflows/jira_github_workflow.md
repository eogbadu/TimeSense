# Jira / GitHub Workflow

## Overview

Every TimeSense implementation task maps to a Jira ticket. All code lives on GitHub branches named after the ticket. This prevents unbounded scope creep and makes project memory recoverable.

---

## Ticket Format

```
TIME-001
TIME-002
TIME-003
```

Use `TIME-###` prefix for all tickets in the TimeSense Jira project.

---

## Ticket Structure

Each ticket must include:

```
Ticket Key:   TIME-###
Title:        Short descriptive title
Goal:         What this ticket achieves
Scope:        What is in scope
Non-goals:    What is explicitly not in scope
Files:        Files likely to be created or modified
Acceptance:   Criteria that must pass before closing
Verification: Commands/steps to verify
Memory:       Project memory files to update after completion
```

See `tickets/jira_ticket_template.md` for the full template.

---

## Branch Naming

```
feature/TIME-001-repository-memory-bootstrap
feature/TIME-002-backend-foundation
feature/TIME-004-ios-app-shell
bugfix/TIME-018-calendar-token-refresh
chore/TIME-021-update-project-memory
```

Rules:
- Always include the Jira ticket key
- Use lowercase, hyphen-separated
- Keep it short but descriptive

---

## Commit Messages

```
TIME-001: add repository memory bootstrap docs
TIME-004: add iOS app shell and bottom navigation
TIME-010: implement recommendation scoring service
TIME-018: fix calendar token refresh handling
```

Rules:
- Begin every commit message with the ticket key
- Use lowercase, present-tense verb
- Describe what changed, not why (the why lives in the ticket and PR description)

---

## Automatic Jira Sync via GitHub Actions

`.github/workflows/jira-sync.yml` transitions tickets automatically:

| Event | Transition |
|---|---|
| Push to `feature/TIME-*` | → In Progress |
| PR opened targeting `main` | → In Review |
| PR merged to `main` | → Done |

**Required GitHub Secrets** (set once at https://github.com/eogbadu/TimeSense/settings/secrets/actions):

| Secret | Value |
|---|---|
| `JIRA_BASE_URL` | `https://eogbadu.atlassian.net` |
| `JIRA_EMAIL` | your Jira login email |
| `JIRA_API_TOKEN` | from https://id.atlassian.com/manage-profile/security/api-tokens |

Until secrets are set, run transitions manually with `python scripts/move_ticket.py TIME-### <status>`.

---

## Pull Request Workflow

1. **Read** project memory and the relevant spec before coding.
2. **Confirm** the active Jira ticket.
3. **Create** or **use** the branch named after the ticket.
4. **Move ticket → In Progress**: `python scripts/move_ticket.py TIME-### "in progress"` *(if Actions haven't fired)*
5. **Implement** only what the ticket scope allows.
6. **Add or update** tests.
7. **Run** verification commands.
8. **Update** project memory files.
9. **Update** `CHANGELOG.md`.
10. **Create** PR using the template in `.github/PULL_REQUEST_TEMPLATE/pull_request_template.md`.
11. **Move ticket → In Review**: `python scripts/move_ticket.py TIME-### "in review"` *(immediately after `gh pr create`)*
12. **Link** the PR to the Jira ticket in the PR description.
13. **After merge — move ticket → Done**: `python scripts/move_ticket.py TIME-### done`
14. **Record** next step in project memory.

---

## PR Checklist

Every PR must include:
- [ ] Jira ticket key in title and description
- [ ] Summary of changes
- [ ] Files changed list
- [ ] Commands run (or note that none were run)
- [ ] Tests / verification (or explicit note if not run)
- [ ] Project memory updates listed
- [ ] Known issues noted
- [ ] Security / privacy notes (if applicable)
- [ ] Next recommended step

---

## Branch Protection Rules (configure on GitHub)

Recommended settings for `main`:
- Require pull request before merging
- Require at least 1 approval
- Require status checks to pass (CI tests)
- Restrict direct pushes to main
- Require branches to be up to date before merging

---

## Implementation Sequence

See `tickets/implementation_sequence.md` for the full ordered list of planned Jira tickets.

---

## Do Not Bundle Unrelated Tickets

Each branch and PR must address exactly one Jira ticket. Do not implement multiple tickets in one PR unless they are explicitly described as a single ticket scope.

---

## Context Recovery

If an agent loses context, it must:
1. Read `docs/project_memory/context_summary.md`
2. Read `docs/project_memory/phase_status.md`
3. Continue from the documented next step
4. Never re-litigate settled decisions in `docs/project_memory/decision_log.md`
