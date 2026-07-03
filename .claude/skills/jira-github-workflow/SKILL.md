# Skill: Jira / GitHub Workflow

## Purpose
Enforce Jira-ticket-based implementation and GitHub branch/PR discipline for TimeSense.

## When to Use
- Starting any new implementation task
- Creating a branch
- Making commits
- Preparing a PR summary
- Closing a ticket
- Switching between tickets

## Required Inputs
- Active Jira ticket number (TIME-###)
- Ticket scope and acceptance criteria

## Required Process

1. Confirm the active Jira ticket from `tickets/implementation_sequence.md`
2. Create or check out the branch: `feature/TIME-###-short-description`
3. Implement only what the ticket scope defines — nothing more
4. Use commit messages starting with `TIME-###: `
5. Run verification commands defined in the ticket
6. Update project memory files
7. Produce a PR-ready summary using the template in `.github/PULL_REQUEST_TEMPLATE/pull_request_template.md`
8. Note the next recommended ticket in project memory

## Required Outputs
- Code changes on a correctly named branch
- PR-ready summary with all required sections
- Updated project memory

## Branch Format
```
feature/TIME-001-repository-memory-bootstrap
feature/TIME-004-ios-app-shell
bugfix/TIME-018-calendar-token-refresh
chore/TIME-021-update-project-memory
```

## Commit Format
```
TIME-001: add repository memory bootstrap docs
TIME-004: add iOS app shell and bottom navigation
TIME-010: implement recommendation scoring service
```

## Files to Read First
- `tickets/implementation_sequence.md`
- `docs/project_memory/context_summary.md`

## Files to Update
- `docs/project_memory/implementation_log.md`
- `docs/project_memory/phase_status.md`
- `CHANGELOG.md`

## Commands / Checks
```bash
git checkout -b feature/TIME-###-description
git add [specific files]
git commit -m "TIME-###: description"
```

## Prohibited Actions
- Do not bundle multiple unrelated tickets in one branch or PR
- Do not push to main directly
- Do not skip project memory updates after completing a ticket
- Do not use vague commit messages without the ticket key

## End-of-Task Requirements
Every completed ticket must have:
- Correct branch name
- Correct commit messages
- PR-ready summary
- Updated project memory
