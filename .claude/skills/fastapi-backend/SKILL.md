# Skill: FastAPI Backend

## Purpose
Build the TimeSense backend consistently using FastAPI, PostgreSQL, Firebase Auth, Stripe, background workers, and provider abstractions.

## When to Use
- Creating or modifying backend routes
- Adding services or repositories
- Adding Pydantic schemas
- Creating database migrations
- Implementing auth-protected endpoints
- Implementing background jobs (Celery)
- Implementing Stripe webhooks
- Implementing Apple/Google billing notifications
- Implementing recommendation APIs
- Implementing admin APIs

## Required Inputs
- Active Jira ticket
- Relevant models, services, or schemas to create/modify
- Any provider abstraction to implement

## Required Process

1. Read `docs/architecture/architecture_overview.md` for structural guidance
2. Follow service/repository pattern — thin routes, logic in services, DB in repositories
3. Use Pydantic schemas for all request/response types
4. Use Firebase Auth JWT verification as a FastAPI dependency on protected routes
5. Use provider abstractions — never call provider SDKs directly from route handlers
6. Use Alembic for schema changes — never modify tables directly
7. Add/update tests for new service logic and critical API endpoints
8. Update project memory

## Required Outputs
- Route handler in `backend/app/api/v1/`
- Service in `backend/app/services/`
- Repository in `backend/app/repositories/` (if DB access)
- Pydantic schema in `backend/app/schemas/`
- SQLAlchemy model in `backend/app/models/` (if new table)
- Alembic migration (if schema change)
- Tests in `backend/tests/`

## Files to Read First
- `docs/architecture/architecture_overview.md`
- Existing service files in the area being modified

## Files to Update
- Relevant service, route, model, schema files
- `backend/alembic/versions/` (if migration needed)
- `backend/tests/`

## Commands / Checks
```bash
# Run migrations
alembic upgrade head

# Run tests
pytest backend/tests/ -v

# Start server
uvicorn app.main:app --reload

# Type check
mypy backend/app/

# Lint
ruff check backend/
```

## Architecture Rules
- Route handlers must be thin (< 20 lines of logic)
- Business logic lives in services
- Database queries live in repositories
- Never call OpenAI, Google Calendar, Stripe, etc. directly from route handlers
- Always verify auth via `get_current_user` dependency
- Admin routes must use `require_admin` dependency
- Webhook handlers must be idempotent (check for duplicate events)
- All secrets via environment variables

## Prohibited Actions
- Do not hardcode API keys or secrets
- Do not call provider SDKs directly from route handlers
- Do not write business logic in repositories
- Do not skip migrations — never modify tables with raw SQL in production
- Do not return raw SQLAlchemy models from routes — use Pydantic response schemas

## End-of-Task Requirements
- Migration runs without error
- Tests pass
- No secrets committed
- Project memory updated
