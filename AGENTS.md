# TimeSense Agents

## Purpose

This file defines rules for all coding agents (Claude, Codex, or any other) working on TimeSense. Agents must follow these rules without exception.

---

## System Summary

TimeSense is a mobile-first, context-aware personal time assistant. It is:

- A **native iOS app** (Swift/SwiftUI)
- A **native Android app** (Kotlin/Jetpack Compose)
- A **FastAPI backend** (PostgreSQL, Redis, Firebase Auth, Stripe/StoreKit/Google Play, LLM abstraction)
- A **web companion** (secondary product for account/settings/admin)

It is **not** a chatbot, Notion clone, task manager, calendar replacement, or drag-and-drop scheduler.

---

## Required Reading Order Before Coding

Every agent must read these files before writing any code:

1. `docs/project_memory/context_summary.md`
2. `docs/project_memory/phase_status.md`
3. `docs/project_memory/implementation_log.md`
4. `docs/project_memory/decision_log.md`
5. `docs/project_memory/known_issues.md`
6. `docs/project_memory/open_questions.md`
7. `tickets/implementation_sequence.md`
8. `AGENTS.md` (this file)
9. `CLAUDE.md`
10. `README.md`
11. `docs/product/product_brief.md`
12. `docs/architecture/architecture_overview.md`
13. `docs/workflows/jira_github_workflow.md`
14. `docs/workflows/memory_compaction_policy.md`
15. The relevant feature spec for the active ticket

---

## Agent Rules

1. Work from an active Jira ticket (`TIME-###`).
2. Keep scope limited to the active ticket only.
3. Use a GitHub branch that includes the Jira ticket key.
4. Commit messages must start with the ticket key.
5. Read project memory before coding.
6. Read relevant specs before modifying code.
7. Preserve native mobile-first product direction.
8. Keep TimeSense from becoming a task manager, calendar clone, Notion clone, chatbot, or project management system.
9. Use provider abstractions for calendars, LLMs, notifications, and integrations.
10. Keep user approval requirements intact for calendar writes and replans.
11. Keep subscription/paywall logic consistent with the spec.
12. Keep privacy and consent rules intact.
13. Add/update tests for meaningful implementation.
14. Update project-memory files after meaningful changes.
15. Update `CHANGELOG.md`.
16. Produce end-of-task summaries in the required format.

---

## Code Generation Constraints

**Do NOT:**
- Use Docker as a substitute for native iOS or Android development
- Add Docker Compose for native mobile builds
- Build a chatbot-only product
- Build a Notion clone
- Build a task-manager-first app
- Build a drag-and-drop calendar editor
- Add Projects at launch
- Add file/document upload at launch
- Add family/shared mode at launch
- Add full alarm clock replacement at launch
- Hardcode LLM providers in core product logic
- Hardcode calendar providers in core product logic
- Implement unrelated Jira tickets in the same pass
- Let memory files grow without compaction

**DO:**
- Keep implementation modular
- Use FastAPI service/repository-style backend structure
- Use typed Pydantic schemas for API requests/responses
- Use SwiftUI for iOS
- Use Jetpack Compose for Android
- Use PostgreSQL as the primary backend data store
- Use Stripe for web subscription logic
- Use Firebase Auth
- Use background workers for scheduled jobs and notification orchestration
- Maintain compact project memory
- Maintain `CHANGELOG.md`
- Add tests as features are implemented
- Show loading, empty, error, success, and permission-denied states
- Preserve premium native mobile UX

---

## Subagents

Subagent specs live under `agents/subagents/`. Each defines a bounded implementation role.

| Subagent | Responsibility |
|---|---|
| Product Spec Guardian | Enforces product rules, prevents feature creep |
| Mobile iOS Agent | Swift/SwiftUI screens, Apple integrations |
| Mobile Android Agent | Kotlin/Compose screens, Android integrations |
| Backend API Agent | FastAPI routes, services, repositories |
| Database Migration Agent | Schema changes, Alembic migrations |
| Calendar Integration Agent | Calendar provider abstractions and implementations |
| Health Wake Signals Agent | HealthKit, sleep/wake, alarm signals |
| Location Commute Agent | Location permissions, commute detection |
| Notification Orchestration Agent | Notification modes, check-ins, ambient surfaces |
| Recommendation Engine Agent | Scoring, focus windows, usable time, LLM explanations |
| LLM Gateway Agent | Provider-agnostic LLM abstraction layer |
| Subscription Billing Agent | Stripe, StoreKit, Google Play, unified entitlements |
| Admin Dashboard Agent | Admin routes, metrics, invite/waitlist tools |
| Security Privacy Agent | Auth, consent, token storage, audit logs |
| QA Testing Agent | Test coverage, smoke tests, regression checks |
| Release Manager Agent | Beta prep, changelog, App Store/Play Store readiness |

---

## Claude Skills

Skills live under `.claude/skills/`. Load the appropriate skill before beginning work in that domain.

| Skill | When to Use |
|---|---|
| `project-memory` | Session start/end, after completing tickets, context compaction |
| `jira-github-workflow` | Starting tasks, branching, commits, PRs |
| `fastapi-backend` | Backend routes, services, repos, migrations |
| `native-ios-swiftui` | iOS screens, Apple APIs, Xcode builds |
| `native-android-compose` | Android screens, Compose, Gradle builds |
| `mobile-ux-premium` | UI design, screen reviews, onboarding |
| `subscription-entitlements` | Stripe, StoreKit, Google Play, trial logic |
| `integration-provider-pattern` | Calendar, LLM, notification provider abstractions |
| `recommendation-engine` | Scoring, usable time, replanning, insights |
| `privacy-security-consent` | Permissions, consent records, token storage, audit logs |

---

## End-of-Task Requirements

Every agent response that implements code must end with:

```md
## Summary of Changes
## Files Changed
## Commands Run
## Tests / Verification
## Project Memory Updates
## Known Issues
## Next Recommended Step
```

If commands were not run, state that explicitly. If tests were not run, explain why.
