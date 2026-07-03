# Backend API Agent

## Purpose
Implement and maintain the TimeSense FastAPI backend: routes, services, repositories, schemas, models, migrations, and background workers.

## Inputs
- Active Jira ticket
- Relevant spec section
- Database models to create/modify
- API endpoints to implement

## Outputs
- FastAPI route handlers in `backend/app/api/v1/`
- Services in `backend/app/services/`
- Repositories in `backend/app/repositories/`
- Pydantic schemas in `backend/app/schemas/`
- SQLAlchemy models in `backend/app/models/`
- Alembic migrations
- Tests in `backend/tests/`

## Allowed Files / Areas
- `backend/` (all subdirectories)
- `docs/project_memory/` (memory updates)
- `CHANGELOG.md`

## Forbidden Actions
- Do not modify iOS or Android source files
- Do not hardcode secrets or API keys
- Do not call provider SDKs directly from route handlers
- Do not skip migrations — no raw SQL schema changes

## Required Tests
- Service unit tests
- API integration tests (authenticated and unauthenticated)
- Webhook idempotency tests
- Admin route protection tests

## Project Memory Updates
After each ticket:
- `docs/project_memory/implementation_log.md`
- `docs/project_memory/phase_status.md`
- `docs/project_memory/context_summary.md`
- `CHANGELOG.md`

## Skill to Use
`.claude/skills/fastapi-backend/SKILL.md`
