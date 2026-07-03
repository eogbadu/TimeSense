# TimeSense — Claude Operational Guide

## Mission
Build TimeSense: a mobile-first, context-aware personal time assistant. **Don't make managing your day another job.**

## Source of Truth
The **repository is the source of truth**, not chat history. Read project memory before coding. Update it after every meaningful change.

---

## Required Reading Order Before Coding

1. `docs/project_memory/context_summary.md`
2. `docs/project_memory/phase_status.md`
3. `docs/project_memory/implementation_log.md`
4. `docs/project_memory/decision_log.md`
5. `docs/project_memory/known_issues.md`
6. `docs/project_memory/open_questions.md`
7. `tickets/implementation_sequence.md`
8. `AGENTS.md`
9. `docs/product/product_brief.md`
10. `docs/architecture/architecture_overview.md`
11. `docs/workflows/jira_github_workflow.md`
12. Relevant area-specific notes for the active ticket

---

## Commands

```bash
# Backend
cd backend && uvicorn app.main:app --reload
cd backend && alembic upgrade head
cd backend && pytest

# iOS
xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense
xcodebuild test -project ios/TimeSense.xcodeproj -scheme TimeSense

# Android
cd android && ./gradlew assembleDebug
cd android && ./gradlew test

# Web
cd web && npm run dev
cd web && npm test

# Docker infrastructure
docker compose up -d
```

---

## Approved Stack

| Component | Technology |
|---|---|
| iOS | Swift / SwiftUI |
| Android | Kotlin / Jetpack Compose |
| Backend | FastAPI + PostgreSQL + Redis/Celery |
| Auth | Firebase Auth |
| Payments | Stripe (web) · StoreKit (iOS) · Google Play (Android) |
| LLM | LLMGateway abstraction, OpenAI default |
| Web | React / Next.js |

---

## Non-Negotiable Product Rules

- Native mobile apps: SwiftUI (iOS) + Compose (Android)
- Web app is companion only
- Bottom tabs: Now · Today · Capture · Insights · Settings
- No Projects at launch
- No file/document upload at launch
- Calendar writes require user approval
- Replans require user approval
- No drag-and-drop schedule editor
- 14-day trial requires payment info
- Free Basic Mode after trial
- Raw audio storage: explicit opt-in only
- No family/shared mode at launch
- The product must never become another job to manage

---

## Jira Workflow

- Every task = one Jira ticket (`TIME-###`)
- Branch: `feature/TIME-###-description`
- Commit: `TIME-###: description`
- One ticket per branch/PR — no bundling
- See `docs/workflows/jira_github_workflow.md`

---

## GitHub Workflow

- Create PR using `.github/PULL_REQUEST_TEMPLATE/pull_request_template.md`
- Every PR requires: summary, files changed, commands run, tests, memory updates, known issues, next step
- See `docs/workflows/jira_github_workflow.md`

---

## Persistent Project Memory

Update these after every meaningful change:

- `docs/project_memory/implementation_log.md`
- `docs/project_memory/phase_status.md`
- `docs/project_memory/change_summary.md`
- `docs/project_memory/context_summary.md`
- `CHANGELOG.md`
- `docs/project_memory/decision_log.md` (when decisions made)
- `docs/project_memory/known_issues.md` (when issues found)
- `docs/project_memory/open_questions.md` (when human input needed)

See `docs/workflows/memory_compaction_policy.md` for compaction rules.

---

## Context Compaction Rule

Before clearing or compacting context:
1. Finish at a clean checkpoint
2. Update all project memory files
3. Rewrite `docs/project_memory/context_summary.md` with exact current state and next step
4. After clearing: resume using the Session Start reading order above

---

## Implementation Style

### Backend
- Thin route handlers → services → repositories → models
- Use Pydantic schemas for all API contracts
- Use Alembic for all schema changes
- Use provider abstractions for calendar, LLM, notifications
- Background jobs via Celery

### iOS
- SwiftUI exclusively
- Feature-folder structure: `ios/TimeSense/Features/[Feature]/`
- Premium UX per `.claude/skills/mobile-ux-premium/SKILL.md`
- Never write calendar events without approval UI

### Android
- Kotlin + Jetpack Compose exclusively
- Feature-folder structure: `android/.../ui/[feature]/`
- Same UX rules as iOS

### Web
- Route-based structure: `/app/`, `/admin/`
- Admin routes role-protected
- Web is companion, not primary product

### Testing
- Backend: pytest for services, API tests, webhook handlers
- iOS: XCTest for logic and services
- Android: JUnit + Compose tests
- Test coverage required for: auth, subscription state transitions, scoring logic, webhook idempotency

---

## Claude Skills

Load the appropriate skill before starting work in each domain:

| Domain | Skill File |
|---|---|
| Project memory | `.claude/skills/project-memory/SKILL.md` |
| Jira / GitHub | `.claude/skills/jira-github-workflow/SKILL.md` |
| FastAPI backend | `.claude/skills/fastapi-backend/SKILL.md` |
| iOS / SwiftUI | `.claude/skills/native-ios-swiftui/SKILL.md` |
| Android / Compose | `.claude/skills/native-android-compose/SKILL.md` |
| Mobile UX | `.claude/skills/mobile-ux-premium/SKILL.md` |
| Subscriptions | `.claude/skills/subscription-entitlements/SKILL.md` |
| Integrations | `.claude/skills/integration-provider-pattern/SKILL.md` |
| Recommendations | `.claude/skills/recommendation-engine/SKILL.md` |
| Privacy/Security | `.claude/skills/privacy-security-consent/SKILL.md` |

---

## Required End-of-Task Format

Every implementation response must end with:

```md
## Summary of Changes
## Files Changed
## Commands Run
## Tests / Verification
## Project Memory Updates
## Known Issues
## Next Recommended Step
```

If commands were not run, say so explicitly. If tests were not run, explain why.

---

## Key Documents

| Document | Purpose |
|---|---|
| `docs/product/product_brief.md` | Product vision and non-negotiable rules |
| `docs/architecture/architecture_overview.md` | System architecture |
| `tickets/implementation_sequence.md` | Full phased ticket plan (TIME-001 to TIME-058) |
| `AGENTS.md` | Agent rules, subagents, constraints |
| `docs/workflows/jira_github_workflow.md` | Ticket, branch, commit, PR rules |
| `docs/workflows/memory_compaction_policy.md` | Context compaction rules |
| `docs/project_memory/context_summary.md` | Current build state and next step |
| `docs/project_memory/decision_log.md` | All settled decisions — do not re-litigate |
