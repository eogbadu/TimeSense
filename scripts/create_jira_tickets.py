"""
TimeSense — Jira Ticket Creator
Creates all TIME-### tickets with full detail via Jira REST API v3.

Usage:
    python scripts/create_jira_tickets.py

Requires .env with JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY
"""

import os
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


# ─────────────────────────────────────────────────────────────────────────────
# ADF Helpers
# ─────────────────────────────────────────────────────────────────────────────

def h2(text):
    return {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": text}]}

def h3(text):
    return {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": text}]}

def p(text):
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}

def bullet_list(items):
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": item}]}]}
            for item in items
        ]
    }

def code_block(text, language="bash"):
    return {
        "type": "codeBlock",
        "attrs": {"language": language},
        "content": [{"type": "text", "text": text}]
    }

def divider():
    return {"type": "rule"}

def doc(*nodes):
    return {"type": "doc", "version": 1, "content": list(nodes)}


# ─────────────────────────────────────────────────────────────────────────────
# Ticket definitions
# ─────────────────────────────────────────────────────────────────────────────

TICKETS = [

    # ── PHASE 0 ──────────────────────────────────────────────────────────────

    {
        "summary": "TIME-001: Repository, Memory, and Workflow Bootstrap",
        "labels": ["phase-0", "docs", "bootstrap"],
        "description": doc(
            h2("Goal"),
            p("Create the full repository operating system before any product code is written. "
              "After this ticket, Claude (or any other agent) must be able to resume the build "
              "from project memory files alone, without relying on chat history."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Root README.md — product summary, stack, setup instructions, key documents",
                "Root AGENTS.md — agent rules, subagents, code generation constraints, end-of-task format",
                "Root CLAUDE.md (operational) — shorter version pointing to docs/, replaces bootstrap spec",
                "Root CHANGELOG.md — initialized with Phase 0 entry",
                "Root .gitignore — Python, iOS, Android, Node, secrets, Docker overrides",
                "Root .env.example — all required environment variable keys, no values",
                "docs/product/product_brief.md — product vision, rules, non-negotiables",
                "docs/architecture/architecture_overview.md — full system architecture",
                "docs/project_memory/context_summary.md — current build state and next step",
                "docs/project_memory/phase_status.md — phase tracking with acceptance criteria",
                "docs/project_memory/decision_log.md — all settled product and technical decisions",
                "docs/project_memory/implementation_log.md — what has been built",
                "docs/project_memory/known_issues.md — bugs and failed approaches",
                "docs/project_memory/open_questions.md — questions needing human input",
                "docs/project_memory/change_summary.md — recent changes log",
                "docs/workflows/jira_github_workflow.md — ticket/branch/commit/PR rules",
                "docs/workflows/memory_compaction_policy.md — context compaction procedure",
                "tickets/implementation_sequence.md — full TIME-001 to TIME-058 ordered ticket plan",
                "tickets/jira_ticket_template.md — template for creating new tickets",
                "agents/subagents/ — spec files for all major subagents",
                ".claude/skills/ — 10 SKILL.md files covering all major build domains",
                ".github/PULL_REQUEST_TEMPLATE/pull_request_template.md",
                "scripts/create_jira_tickets.py — this script",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No product application code in this phase",
                "No backend API routes",
                "No mobile app screens",
                "No database schema",
                "No Docker files",
                "No Stripe, Firebase, or third-party SDK integration",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Repository is understandable from documentation alone",
                "Claude can resume from project memory without chat history",
                "All required project memory files exist and have useful content",
                "All 10 Claude skill files exist with TimeSense-specific instructions",
                "Jira/GitHub workflow is documented",
                "PR template exists at .github/PULL_REQUEST_TEMPLATE/pull_request_template.md",
                "tickets/implementation_sequence.md defines the full phased ticket plan",
                "Docker strategy is clear: backend/web infrastructure only, not native mobile",
                "No product application code was added during Phase 0",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "# Confirm all required files exist\n"
                "ls docs/project_memory/\n"
                "ls .claude/skills/\n"
                "ls agents/subagents/\n"
                "ls tickets/\n"
                "ls .github/PULL_REQUEST_TEMPLATE/\n\n"
                "# Confirm .env is gitignored\n"
                "git check-ignore -v .env\n\n"
                "# Confirm no application code\n"
                "ls backend/ 2>/dev/null || echo 'backend not yet created — correct'"
            ),
            divider(),
            h2("Dependencies"),
            p("None — this is the first ticket."),
            divider(),
            h2("Next Ticket"),
            p("TIME-002: FastAPI App Structure and Health Endpoint"),
        ),
    },

    # ── PHASE 1 ──────────────────────────────────────────────────────────────

    {
        "summary": "TIME-002: FastAPI App Structure and Health Endpoint",
        "labels": ["phase-1", "backend"],
        "description": doc(
            h2("Goal"),
            p("Bootstrap the FastAPI backend with the correct project structure, configuration system, "
              "and a working health endpoint. Establish the service/repository pattern that all future "
              "backend tickets must follow."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/ directory with the full app package structure",
                "backend/app/main.py — FastAPI app entry point, CORS middleware, router registration",
                "backend/app/core/config.py — Settings class using pydantic-settings, reads from .env",
                "backend/app/core/errors.py — global exception handlers (404, 422, 500)",
                "backend/app/api/v1/health.py — GET /health endpoint returning status and version",
                "backend/app/api/v1/__init__.py and router registration",
                "backend/requirements.txt — fastapi, uvicorn, pydantic-settings, python-dotenv, httpx",
                "backend/requirements-dev.txt — pytest, pytest-asyncio, httpx, ruff, mypy",
                "backend/.env.example — backend-specific env vars (DATABASE_URL, REDIS_URL, SECRET_KEY, etc.)",
                "backend/Makefile or scripts for common commands (run, test, lint, migrate)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No database connection yet (TIME-003)",
                "No authentication yet (TIME-005)",
                "No business logic or models yet",
                "No Docker yet (TIME-006)",
                "No Celery/Redis yet (TIME-004)",
            ]),
            divider(),
            h2("Project Structure"),
            code_block(
                "backend/\n"
                "  app/\n"
                "    main.py\n"
                "    core/\n"
                "      config.py\n"
                "      errors.py\n"
                "    api/\n"
                "      v1/\n"
                "        __init__.py\n"
                "        health.py\n"
                "    services/          # empty placeholder\n"
                "    repositories/      # empty placeholder\n"
                "    schemas/           # empty placeholder\n"
                "    models/            # empty placeholder\n"
                "    workers/           # empty placeholder\n"
                "    integrations/      # empty placeholder\n"
                "    llm/               # empty placeholder\n"
                "  tests/\n"
                "    __init__.py\n"
                "    conftest.py\n"
                "    test_health.py\n"
                "  requirements.txt\n"
                "  requirements-dev.txt\n"
                "  .env.example\n",
                "text"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Backend starts with: uvicorn app.main:app --reload",
                "GET /health returns HTTP 200 with JSON: {\"status\": \"ok\", \"version\": \"0.1.0\"}",
                "CORS middleware configured (restrict in production, allow localhost in dev)",
                "pydantic-settings reads config from environment variables",
                "Unknown routes return structured JSON 404, not HTML",
                "test_health.py passes with pytest",
                "ruff check passes with no errors",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend\n"
                "python -m venv .venv && source .venv/bin/activate\n"
                "pip install -r requirements.txt -r requirements-dev.txt\n\n"
                "# Run server\n"
                "uvicorn app.main:app --reload\n\n"
                "# In another terminal\n"
                "curl http://localhost:8000/health\n"
                "# Expected: {\"status\": \"ok\", \"version\": \"0.1.0\"}\n\n"
                "# Run tests\n"
                "pytest tests/test_health.py -v\n\n"
                "# Lint\n"
                "ruff check app/"
            ),
            divider(),
            h2("Project Memory Updates"),
            bullet_list([
                "docs/project_memory/implementation_log.md — log backend structure created",
                "docs/project_memory/phase_status.md — check off TIME-002",
                "docs/project_memory/context_summary.md — update current state",
                "CHANGELOG.md — add entry",
            ]),
            divider(),
            h2("Dependencies"),
            p("TIME-001 must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-003: PostgreSQL Connection and Alembic Migrations"),
        ),
    },

    {
        "summary": "TIME-003: PostgreSQL Connection and Alembic Migrations",
        "labels": ["phase-1", "backend", "database"],
        "description": doc(
            h2("Goal"),
            p("Connect the FastAPI backend to PostgreSQL using SQLAlchemy async engine. "
              "Set up Alembic as the migration tool. Create the base declarative model. "
              "Run a clean initial migration so the database is ready for application tables."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/core/database.py — async SQLAlchemy engine, SessionLocal, get_db dependency",
                "backend/app/models/base.py — DeclarativeBase with created_at/updated_at mixins",
                "backend/alembic.ini — Alembic config pointing to async engine",
                "backend/alembic/env.py — async-compatible env.py importing app models",
                "backend/alembic/versions/ — empty initial migration",
                "Add asyncpg, sqlalchemy[asyncio], alembic to requirements.txt",
                "Update backend/.env.example with DATABASE_URL",
                "Update docker-compose.yml stub with postgres service (even if Docker ticket is TIME-006)",
                "tests/conftest.py — async test client, test database setup using SQLite or test Postgres",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No application tables yet — those come in Phase 2 (TIME-007+)",
                "No Redis or Celery (TIME-004)",
                "No auth (TIME-005)",
                "Do not create user/subscription models in this ticket",
            ]),
            divider(),
            h2("Database Pattern"),
            code_block(
                "# core/database.py\n"
                "from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession\n"
                "from app.core.config import settings\n\n"
                "engine = create_async_engine(settings.database_url, echo=settings.debug)\n"
                "AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)\n\n"
                "async def get_db() -> AsyncGenerator[AsyncSession, None]:\n"
                "    async with AsyncSessionLocal() as session:\n"
                "        yield session",
                "python"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "alembic upgrade head runs without error on a fresh database",
                "alembic current shows the current revision",
                "alembic revision --autogenerate works for future schema additions",
                "get_db() yields an AsyncSession correctly in tests",
                "Test database strategy documented in conftest.py comments",
                "No direct SQL — all DB access will go through SQLAlchemy ORM",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend\n"
                "source .venv/bin/activate\n\n"
                "# Run migration\n"
                "alembic upgrade head\n\n"
                "# Check current\n"
                "alembic current\n\n"
                "# Generate a test revision to confirm autogenerate works\n"
                "alembic revision --autogenerate -m 'test'\n"
                "# Then revert\n"
                "git checkout alembic/versions/\n\n"
                "# Tests\n"
                "pytest tests/ -v"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-002 must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-004: Redis and Celery Background Worker Setup"),
        ),
    },

    {
        "summary": "TIME-004: Redis and Celery Background Worker Setup",
        "labels": ["phase-1", "backend", "workers"],
        "description": doc(
            h2("Goal"),
            p("Add Redis as the message broker and result backend. Set up Celery as the background "
              "worker framework. This infrastructure will power notification orchestration, integration "
              "sync jobs, recommendation generation, and weekly insight generation in later phases."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/core/redis.py — Redis connection using redis-py async client",
                "backend/app/workers/celery_app.py — Celery app configured with Redis broker + backend",
                "backend/app/workers/health_task.py — simple health-check Celery task for verification",
                "Add celery, redis, flower (optional) to requirements.txt",
                "Update backend/.env.example with REDIS_URL",
                "Makefile target: make worker (starts celery worker)",
                "Document worker startup in README backend section",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No application-specific tasks yet — those come in later phases",
                "No notification tasks yet",
                "No integration sync tasks yet",
                "No production Redis config (TLS, auth) — that is deployment config",
            ]),
            divider(),
            h2("Celery Pattern"),
            code_block(
                "# workers/celery_app.py\n"
                "from celery import Celery\n"
                "from app.core.config import settings\n\n"
                "celery_app = Celery(\n"
                "    'timesense',\n"
                "    broker=settings.redis_url,\n"
                "    backend=settings.redis_url,\n"
                "    include=['app.workers.health_task'],\n"
                ")\n\n"
                "celery_app.conf.update(\n"
                "    task_serializer='json',\n"
                "    result_serializer='json',\n"
                "    accept_content=['json'],\n"
                "    timezone='UTC',\n"
                "    enable_utc=True,\n"
                ")",
                "python"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Celery worker starts: celery -A app.workers.celery_app worker --loglevel=info",
                "Health-check task can be called and returns a result",
                "Redis connection is verified on worker startup",
                "Worker connects to the same Redis as the FastAPI app",
                "No Celery import errors on fresh install",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend\n"
                "source .venv/bin/activate\n\n"
                "# Start worker (requires Redis running locally or via Docker)\n"
                "celery -A app.workers.celery_app worker --loglevel=info\n\n"
                "# In another terminal — call health task\n"
                "python -c \"\n"
                "from app.workers.health_task import health_check\n"
                "result = health_check.delay()\n"
                "print(result.get(timeout=5))\n"
                "\""
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-003 must be complete. Redis must be running locally or via Docker."),
            divider(),
            h2("Next Ticket"),
            p("TIME-005: Firebase Auth Integration and Protected Routes"),
        ),
    },

    {
        "summary": "TIME-005: Firebase Auth Integration and Protected Routes",
        "labels": ["phase-1", "backend", "auth"],
        "description": doc(
            h2("Goal"),
            p("Integrate Firebase Auth as the authentication layer. Verify Firebase JWT tokens "
              "server-side on every protected request. Create a get_current_user FastAPI dependency "
              "that all authenticated routes will use. Add admin role enforcement as a second "
              "dependency. This is the security foundation that all Phase 2+ routes will build on."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/core/firebase.py — Firebase Admin SDK initialization from service account JSON",
                "backend/app/core/security.py — verify_firebase_token(), get_current_user() dependency, require_admin() dependency",
                "backend/app/api/v1/auth.py — GET /auth/me endpoint (returns current user info from token)",
                "backend/app/schemas/auth.py — TokenUser schema (uid, email, role)",
                "Add firebase-admin to requirements.txt",
                "Update .env.example with FIREBASE_PROJECT_ID and FIREBASE_SERVICE_ACCOUNT_JSON",
                "tests/test_auth.py — test valid token, expired token, missing token, admin vs non-admin",
                "conftest.py — mock Firebase token verification for tests (avoid real Firebase calls in unit tests)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No user database record yet — that is TIME-007",
                "No signup or onboarding flow yet",
                "No Firebase client SDK — this is server-side token verification only",
                "No custom email/password auth — Firebase handles auth client-side on mobile/web",
            ]),
            divider(),
            h2("Auth Pattern"),
            code_block(
                "# core/security.py\n"
                "async def get_current_user(authorization: str = Header(...)) -> TokenUser:\n"
                "    token = authorization.removeprefix('Bearer ')\n"
                "    decoded = firebase_admin.auth.verify_id_token(token)\n"
                "    return TokenUser(uid=decoded['uid'], email=decoded.get('email'), role=decoded.get('role', 'user'))\n\n"
                "async def require_admin(user: TokenUser = Depends(get_current_user)) -> TokenUser:\n"
                "    if user.role != 'admin':\n"
                "        raise HTTPException(status_code=403, detail='Admin access required')\n"
                "    return user\n\n"
                "# Usage in a route\n"
                "@router.get('/me')\n"
                "async def get_me(user: TokenUser = Depends(get_current_user)):\n"
                "    return user",
                "python"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Valid Firebase JWT returns 200 with user info",
                "Missing Authorization header returns 401",
                "Expired or invalid JWT returns 401 with clear error message",
                "Non-admin user hitting require_admin route returns 403",
                "Admin user (role=admin in Firebase custom claims) passes require_admin",
                "Firebase Admin SDK initializes from environment variables, not hardcoded credentials",
                "All auth tests pass with mocked Firebase (no real network calls in tests)",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend\n"
                "source .venv/bin/activate\n\n"
                "pytest tests/test_auth.py -v\n\n"
                "# Manual test with a real Firebase token (optional)\n"
                "curl -H 'Authorization: Bearer <FIREBASE_ID_TOKEN>' \\\n"
                "  http://localhost:8000/api/v1/auth/me"
            ),
            divider(),
            h2("Security Notes"),
            bullet_list([
                "Never log or return raw JWT tokens",
                "Firebase service account JSON must be in .env, never committed to git",
                "Admin role is set via Firebase custom claims — not user-controllable",
                "Token expiry is enforced by Firebase Admin SDK automatically",
            ]),
            divider(),
            h2("Dependencies"),
            p("TIME-002, TIME-003 must be complete. Firebase project must exist (see open_questions.md)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-006: Docker Compose for Backend Infrastructure"),
        ),
    },

    {
        "summary": "TIME-006: Docker Compose for Backend Infrastructure",
        "labels": ["phase-1", "backend", "infra", "docker"],
        "description": doc(
            h2("Goal"),
            p("Provide a reproducible local development environment for the backend and web "
              "infrastructure using Docker Compose. This covers PostgreSQL, Redis, the FastAPI backend, "
              "and the Celery worker. Docker is NOT used for iOS or Android development — native "
              "mobile tooling (Xcode, Android Studio) is always required for mobile."),
            divider(),
            h2("Scope"),
            bullet_list([
                "docker-compose.yml — services: postgres, redis, backend (FastAPI), worker (Celery)",
                "docker-compose.override.yml.example — local overrides template (volume mounts for hot reload)",
                "backend/Dockerfile — production-ready multi-stage Python image",
                "backend/.dockerignore — exclude .venv, __pycache__, .env, tests",
                "Update root .env.example with Docker-friendly DATABASE_URL and REDIS_URL defaults",
                "Update README.md — Docker backend setup section",
                "Makefile at root — targets: up, down, logs, migrate, test",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No iOS build in Docker — ever",
                "No Android build in Docker — ever",
                "No production Kubernetes or cloud deployment config yet",
                "No SSL/TLS config in Docker (that is deployment config)",
                "No web companion Docker config yet (that comes with the web app ticket)",
            ]),
            divider(),
            h2("Docker Compose Services"),
            code_block(
                "services:\n"
                "  postgres:\n"
                "    image: postgres:16-alpine\n"
                "    environment:\n"
                "      POSTGRES_USER: timesense\n"
                "      POSTGRES_PASSWORD: timesense\n"
                "      POSTGRES_DB: timesense\n"
                "    ports: ['5432:5432']\n"
                "    volumes: [postgres_data:/var/lib/postgresql/data]\n\n"
                "  redis:\n"
                "    image: redis:7-alpine\n"
                "    ports: ['6379:6379']\n\n"
                "  backend:\n"
                "    build: ./backend\n"
                "    ports: ['8000:8000']\n"
                "    env_file: .env\n"
                "    depends_on: [postgres, redis]\n"
                "    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload\n\n"
                "  worker:\n"
                "    build: ./backend\n"
                "    env_file: .env\n"
                "    depends_on: [postgres, redis]\n"
                "    command: celery -A app.workers.celery_app worker --loglevel=info\n\n"
                "volumes:\n"
                "  postgres_data:",
                "yaml"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "docker compose up -d starts all four services without errors",
                "GET http://localhost:8000/health returns 200",
                "PostgreSQL is reachable at localhost:5432",
                "Redis is reachable at localhost:6379",
                "Celery worker connects and shows as ready in logs",
                "alembic upgrade head runs successfully against the Dockerized Postgres",
                ".env is NOT copied into the Docker image (env_file mount only)",
                "Secrets are never baked into Dockerfile or docker-compose.yml",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "# Start all services\n"
                "docker compose up -d\n\n"
                "# Check all containers are healthy\n"
                "docker compose ps\n\n"
                "# Health check\n"
                "curl http://localhost:8000/health\n\n"
                "# Run migrations against Dockerized Postgres\n"
                "docker compose exec backend alembic upgrade head\n\n"
                "# View worker logs\n"
                "docker compose logs worker\n\n"
                "# Stop\n"
                "docker compose down"
            ),
            divider(),
            h2("Important Notes"),
            bullet_list([
                "iOS development uses Xcode — never Docker",
                "Android development uses Android Studio and Gradle — never Docker",
                "Apple HealthKit, EventKit, StoreKit, and Siri cannot run in Docker",
                "Docker is for backend/web infrastructure reproducibility only",
            ]),
            divider(),
            h2("Dependencies"),
            p("TIME-002, TIME-003, TIME-004 must be complete so the Dockerized services have something to run."),
            divider(),
            h2("Next Ticket"),
            p("TIME-007: User and Profile Data Model"),
        ),
    },

    # ── PHASE 2 ──────────────────────────────────────────────────────────────

    {
        "summary": "TIME-007: User and Profile Data Model",
        "labels": ["phase-2", "backend", "database"],
        "description": doc(
            h2("Goal"),
            p("Implement the foundational user, profile, and preferences data model. "
              "This is the first set of real application tables. All future features that need "
              "to know who the user is will depend on these tables."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/models/user.py — User model (id, firebase_uid, email, role, created_at, is_active, onboarding_complete)",
                "backend/app/models/profile.py — UserProfile model (display_name, timezone, locale, avatar_url, onboarding_path)",
                "backend/app/models/preferences.py — UserPreferences model (notification_mode, capture_auto_create, theme, language)",
                "Alembic migration: create users, user_profiles, user_preferences tables",
                "backend/app/repositories/user_repository.py — get_by_firebase_uid, create, update",
                "backend/app/services/user_service.py — get_or_create_user (called on first auth)",
                "backend/app/schemas/user.py — UserResponse, UserProfileUpdate, UserPreferencesUpdate",
                "backend/app/api/v1/users.py — GET /users/me, PATCH /users/me/profile, PATCH /users/me/preferences",
                "tests/test_users.py — create user, get user, update profile, update preferences",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No subscription tables yet (TIME-011)",
                "No consent records yet (TIME-009)",
                "No assistant personality yet (TIME-008)",
                "No onboarding state machine — just the onboarding_complete boolean flag for now",
            ]),
            divider(),
            h2("User Model Key Fields"),
            code_block(
                "class User(Base):\n"
                "    __tablename__ = 'users'\n"
                "    id: uuid (PK)\n"
                "    firebase_uid: str (unique, indexed)\n"
                "    email: str (unique)\n"
                "    role: str (default='user', values: user|admin)\n"
                "    is_active: bool (default=True)\n"
                "    onboarding_complete: bool (default=False)\n"
                "    created_at: datetime\n"
                "    updated_at: datetime",
                "python"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Migration creates users, user_profiles, user_preferences tables cleanly",
                "GET /users/me returns current user info (requires valid Firebase JWT)",
                "PATCH /users/me/profile updates display_name, timezone, locale",
                "PATCH /users/me/preferences updates notification_mode, capture_auto_create",
                "get_or_create_user() creates a user on first login and returns existing on subsequent calls",
                "Admin role field exists and is enforced by require_admin dependency",
                "All endpoints require authentication — unauthenticated requests return 401",
                "Tests cover: create, retrieve, update, duplicate firebase_uid handling",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend && source .venv/bin/activate\n\n"
                "alembic upgrade head\n"
                "pytest tests/test_users.py -v"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-005 (Firebase auth) and TIME-006 (Docker/DB) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-008: Assistant Personality and Onboarding State"),
        ),
    },

    {
        "summary": "TIME-008: Assistant Personality and Onboarding State",
        "labels": ["phase-2", "backend"],
        "description": doc(
            h2("Goal"),
            p("Persist the user's chosen assistant personality and detailed onboarding progress. "
              "Onboarding state must survive app restarts so users can resume where they left off "
              "across sessions and devices."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/models/onboarding.py — AssistantPersonalitySettings model, OnboardingState model",
                "AssistantPersonalitySettings fields: user_id (FK), personality_type (calm_premium | friendly_companion | high_performance_coach), set_at",
                "OnboardingState fields: user_id (FK), current_step, steps_completed (JSON array), skipped_integrations (JSON array), completed_at",
                "Alembic migration: create assistant_personality_settings, onboarding_states tables",
                "backend/app/services/onboarding_service.py — get_onboarding_state, advance_step, skip_integration, complete_onboarding",
                "backend/app/schemas/onboarding.py — OnboardingStateResponse, PersonalityUpdate",
                "backend/app/api/v1/onboarding.py — GET /onboarding/state, POST /onboarding/personality, POST /onboarding/advance, POST /onboarding/complete",
                "tests/test_onboarding.py — personality persists, steps advance, skip integration, complete",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No onboarding UI screens in this ticket (handled in mobile tickets)",
                "No changes to the User model itself",
                "No A/B testing of onboarding flows",
            ]),
            divider(),
            h2("Onboarding Steps"),
            bullet_list([
                "welcome",
                "path_selection",
                "personality_selection",
                "learning_mode_explanation",
                "calendar_setup",
                "health_setup",
                "location_permission",
                "notifications_permission",
                "tasks_reminders_setup",
                "optional_integrations",
                "goals_setup",
                "capture_preference",
                "audio_consent",
                "subscription_trial",
                "complete",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Personality choice persists across sessions",
                "Onboarding state resumes correctly after app restart",
                "Steps can be advanced in order",
                "Integrations can be skipped and the skipped list is stored",
                "onboarding_complete flag on User is set when POST /onboarding/complete is called",
                "All endpoints require authentication",
                "Tests cover all state transitions",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend && source .venv/bin/activate\n\n"
                "alembic upgrade head\n"
                "pytest tests/test_onboarding.py -v"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-007 (User model) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-009: Consent Records"),
        ),
    },

    {
        "summary": "TIME-009: Consent Records",
        "labels": ["phase-2", "backend", "privacy"],
        "description": doc(
            h2("Goal"),
            p("Store every user consent decision in the database. Consent records are required for "
              "legal compliance and for the privacy model defined in the product spec. "
              "Raw audio storage and model-training use require separate, additional explicit opt-ins "
              "beyond the microphone permission."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/models/consent.py — ConsentRecord model",
                "ConsentRecord fields: id, user_id (FK), consent_type (enum), granted (bool), granted_at, revoked_at, ip_address, user_agent",
                "Consent types: audio_storage, model_training, location, health, calendar_full_detail, calendar_free_busy_only, notifications, microphone",
                "Alembic migration: create consent_records table",
                "backend/app/repositories/consent_repository.py — create, get_by_user, revoke",
                "backend/app/services/consent_service.py — grant_consent, revoke_consent, has_active_consent",
                "backend/app/schemas/consent.py — ConsentCreate, ConsentResponse, ConsentRevoke",
                "backend/app/api/v1/privacy.py — POST /privacy/consent, DELETE /privacy/consent/{type}, GET /privacy/consent",
                "tests/test_consent.py — grant, revoke, check active, duplicate grant handling",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No data deletion/export endpoints yet (that is Phase 14, TIME-055)",
                "No audio file storage yet",
                "No UI for consent — onboarding handles that in TIME-020",
            ]),
            divider(),
            h2("Consent Model"),
            code_block(
                "class ConsentRecord(Base):\n"
                "    __tablename__ = 'consent_records'\n"
                "    id: uuid (PK)\n"
                "    user_id: uuid (FK -> users.id)\n"
                "    consent_type: ConsentType (enum)\n"
                "    granted: bool\n"
                "    granted_at: datetime\n"
                "    revoked_at: datetime | None\n"
                "    ip_address: str | None\n"
                "    user_agent: str | None",
                "python"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Consent records are created when user grants a permission",
                "Revoking consent sets revoked_at timestamp (does not delete the record)",
                "has_active_consent() returns True only if granted=True and revoked_at is None",
                "Multiple grants of the same type update the existing record rather than creating duplicates",
                "All endpoints require authentication",
                "ip_address and user_agent stored from request headers",
                "Tests cover: grant, revoke, re-grant, has_active_consent checks",
            ]),
            divider(),
            h2("Privacy Note"),
            bullet_list([
                "Audio storage consent is separate from microphone permission",
                "Model training use consent is separate from audio storage consent",
                "Users can revoke any consent at any time via DELETE /privacy/consent/{type}",
                "Revocation must trigger cleanup of stored data for the relevant type (implementation in TIME-055)",
            ]),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend && source .venv/bin/activate\n\n"
                "alembic upgrade head\n"
                "pytest tests/test_consent.py -v"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-007 (User model) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-010: Admin Role Enforcement"),
        ),
    },

    {
        "summary": "TIME-010: Admin Role Enforcement",
        "labels": ["phase-2", "backend", "admin", "auth"],
        "description": doc(
            h2("Goal"),
            p("Finalize admin role enforcement with an audit log and the /admin route foundation. "
              "Normal users must never be able to access admin routes. All admin actions must be "
              "logged. This is the security foundation for the admin dashboard built in TIME-048."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/models/audit.py — AdminAuditLog model",
                "AdminAuditLog fields: id, admin_user_id (FK), action, target_type, target_id, payload (JSON), ip_address, created_at",
                "Alembic migration: create admin_audit_logs table",
                "backend/app/core/security.py — finalize require_admin() dependency, add log_admin_action() helper",
                "backend/app/api/v1/admin/__init__.py — admin router (all routes under /api/v1/admin)",
                "backend/app/api/v1/admin/health.py — GET /admin/health (admin-only health check with system info)",
                "backend/app/api/v1/admin/users.py — GET /admin/users (user list with search), GET /admin/users/{id}",
                "backend/app/schemas/admin.py — AdminUserResponse, AdminAuditLogResponse",
                "tests/test_admin_auth.py — non-admin blocked (403), admin passes, audit log entry created",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No full admin dashboard UI yet (TIME-048)",
                "No invite code management yet (TIME-017)",
                "No subscription admin views yet (TIME-012+)",
                "No metrics dashboard yet (TIME-048)",
            ]),
            divider(),
            h2("Audit Log Pattern"),
            code_block(
                "# Every admin action calls this:\n"
                "async def log_admin_action(\n"
                "    db: AsyncSession,\n"
                "    admin_user_id: str,\n"
                "    action: str,          # e.g. 'user.view', 'invite.create', 'invite.disable'\n"
                "    target_type: str,     # e.g. 'user', 'invite_code'\n"
                "    target_id: str,       # the affected record ID\n"
                "    payload: dict = {},   # sanitized action payload (no secrets)\n"
                "    ip_address: str = ''\n"
                ") -> None: ...",
                "python"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Non-admin user hitting any /admin/* route receives HTTP 403",
                "Admin user successfully accesses admin routes",
                "GET /admin/users returns paginated user list",
                "Admin action creates an entry in admin_audit_logs",
                "Audit log is append-only — no delete or update endpoints for audit logs",
                "Admin user cannot elevate their own role via any API endpoint",
                "Tests cover: 403 for non-admin, 200 for admin, audit log entry created",
            ]),
            divider(),
            h2("Security Note"),
            p("Admin role is set via Firebase custom claims server-side only. "
              "There is no API endpoint that allows a user to set their own role. "
              "Role escalation must go through Firebase Admin SDK directly."),
            divider(),
            h2("Verification Commands"),
            code_block(
                "cd backend && source .venv/bin/activate\n\n"
                "alembic upgrade head\n"
                "pytest tests/test_admin_auth.py -v"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-005 (auth), TIME-007 (user model) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-011: Subscription Data Model"),
        ),
    },

    # ── PHASE 3 ──────────────────────────────────────────────────────────────

    {
        "summary": "TIME-011: Stripe Customer and Trial Foundation",
        "labels": ["phase-3", "backend", "subscriptions", "stripe"],
        "description": doc(
            h2("Goal"),
            p("Build the unified Subscription model and Stripe customer creation so every new web user "
              "can start a 14-day free trial. This is the foundation all monetisation flows build on."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Subscription SQLAlchemy model: user_id FK, platform (stripe/apple/google), status, platform_customer_id, platform_subscription_id, plan, trial_start/end, current_period_end, cancel_at_period_end",
                "SubscriptionRepository: start_trial(), update(), get_by_user_id(), get_by_platform_customer_id()",
                "SubscriptionService: start_trial() creates Stripe Customer on web path; handle_stripe_event() dispatches webhook types",
                "Alembic migration: subscriptions table",
                "POST /api/v1/subscriptions/trial — idempotent, 14-day trial",
                "GET /api/v1/subscriptions/me — current subscription state",
                "GET /api/v1/subscriptions/me/entitlement — {is_premium, status, platform}",
                "POST /webhooks/stripe — validates Stripe signature before dispatch",
                "POST /webhooks/apple and /webhooks/google — handler stubs",
                "Apple and Google webhook handlers in SubscriptionService (stubbed)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No actual payment capture in this ticket (Stripe Checkout / payment links)",
                "No subscription management UI",
                "No cancellation flow",
                "No referral logic",
            ]),
            divider(),
            h2("Key Files"),
            code_block(
                "backend/app/models/subscription.py\n"
                "backend/app/repositories/subscription_repository.py\n"
                "backend/app/services/subscription_service.py\n"
                "backend/app/schemas/subscription.py\n"
                "backend/app/api/v1/subscriptions.py\n"
                "backend/migrations/versions/d4e5f6a7b8c9_add_subscriptions.py\n"
                "backend/tests/test_subscriptions.py",
                "text"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /subscriptions/trial creates subscription with status=trialing and Stripe customer ID",
                "POST /subscriptions/trial is idempotent (same subscription returned on repeat calls)",
                "GET /subscriptions/me/entitlement returns is_premium=True during trial",
                "Stripe webhook returns 400 on bad signature, 503 if secret not configured",
                "invoice.paid event moves status from trialing to active",
                "43 backend tests passing",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_subscriptions.py -v\n"
                "cd backend && pytest -q  # full suite\n"
                "# Stripe webhook test:\n"
                "stripe trigger invoice.paid --stripe-secret $STRIPE_SECRET_KEY"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-007 (user model), TIME-005 (Firebase auth) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-012: Subscription Status Gates and Feature Flags"),
        ),
    },

    {
        "summary": "TIME-012: Subscription Gates and Feature Flags",
        "labels": ["phase-3", "backend", "subscriptions", "entitlements"],
        "description": doc(
            h2("Goal"),
            p("Implement the PremiumUser FastAPI dependency gate and a complete feature flag system "
              "so every route and client knows exactly what a user can access based on their subscription tier."),
            divider(),
            h2("Scope"),
            bullet_list([
                "PremiumUser dependency: require_premium() — 403 SUBSCRIPTION_REQUIRED for non-premium users",
                "feature_flags(is_premium) function: returns dict of all feature access flags",
                "PREMIUM_FEATURES: ai_suggestions, calendar_write, replan, insight_trends, capture_unlimited, integrations, smart_scheduling, focus_modes",
                "FREE_FEATURES: capture_basic (5/day), today_view, manual_task_entry, basic_reminders",
                "GET /subscriptions/me/features — full feature flag dict for app launch",
                "Demonstration endpoint: GET /subscriptions/premium-only-example",
                "FeatureFlagsResponse schema",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No per-feature enforcement in business logic (enforcement is in service layer calls, not the flag dict itself)",
                "No A/B testing or experiment flags",
            ]),
            divider(),
            h2("Key Files"),
            code_block(
                "backend/app/core/entitlements.py\n"
                "backend/app/api/v1/subscriptions.py (updated)\n"
                "backend/app/schemas/subscription.py (updated)\n"
                "backend/tests/test_entitlements.py",
                "text"
            ),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Free user gets 403 SUBSCRIPTION_REQUIRED on premium-gated route",
                "Trialing user can access premium-gated route",
                "GET /me/features returns is_premium=False and ai_suggestions=False for free user",
                "GET /me/features returns all premium flags=True for trialing user",
                "48 backend tests passing",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_entitlements.py -v\n"
                "cd backend && pytest -q  # full suite"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-011 (subscription model) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-013: LLM Gateway Abstraction"),
        ),
    },

    {
        "summary": "TIME-013: LLM Gateway Abstraction",
        "labels": ["phase-3", "backend", "llm", "ai"],
        "description": doc(
            h2("Goal"),
            p("Build a provider-agnostic LLM gateway so all AI features (suggestions, scheduling, "
              "coaching messages) call a single internal interface that can be swapped between "
              "OpenAI, Anthropic, or other providers without changing feature code."),
            divider(),
            h2("Scope"),
            bullet_list([
                "LLMProvider abstract base class: complete(prompt, system, model, max_tokens) -> str",
                "OpenAIProvider implementation using openai SDK",
                "AnthropicProvider implementation using anthropic SDK (stub if SDK not installed)",
                "LLMGateway: wraps provider, handles retries, timeout, cost logging",
                "get_llm_gateway() FastAPI dependency returning configured gateway from settings",
                "OPENAI_API_KEY and ANTHROPIC_API_KEY in settings (already in .env.example)",
                "LLM_PROVIDER setting: openai | anthropic (default: openai)",
                "Test with mocked provider — no real API calls in tests",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No streaming responses in this ticket",
                "No function calling / tool use",
                "No prompt versioning system",
                "No cost tracking dashboard",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "LLMGateway.complete() returns string response from mocked provider in tests",
                "Switching LLM_PROVIDER setting changes the active provider",
                "Provider errors propagate as HTTP 502 with a clean message",
                "No real API calls in test suite",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_llm_gateway.py -v\n"
                "cd backend && pytest -q  # full suite"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-005 (config/settings pattern) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-014: Calendar Provider Abstraction"),
        ),
    },

    {
        "summary": "TIME-014: Calendar Provider Abstraction",
        "labels": ["phase-3", "backend", "calendar", "integrations"],
        "description": doc(
            h2("Goal"),
            p("Build a provider-agnostic calendar integration layer so Google Calendar and Apple Calendar "
              "(via CalDAV) can be read and written through a single internal interface. "
              "Calendar writes always require explicit user approval — never auto-write."),
            divider(),
            h2("Scope"),
            bullet_list([
                "CalendarProvider abstract base: list_events(user_id, start, end), create_event(user_id, event, approval_token)",
                "GoogleCalendarProvider: OAuth2 token exchange, list/create events via Google Calendar API",
                "AppleCalendarProvider stub: CalDAV endpoint (full impl deferred to mobile)",
                "CalendarEvent schema: title, start, end, location, description, calendar_id",
                "PendingCalendarAction model: stores calendar writes awaiting user approval",
                "POST /calendar/events/pending — queue a calendar write for approval",
                "POST /calendar/events/pending/{id}/approve — user approves, event is written",
                "POST /calendar/events/pending/{id}/reject — user rejects, action discarded",
                "GET /calendar/events — list upcoming events (read-only, no approval needed)",
                "CalendarIntegration model: stores OAuth tokens per user per provider",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No drag-and-drop schedule editor",
                "No recurring event management",
                "No calendar conflict detection in this ticket",
                "No Apple Calendar native integration (handled on-device in iOS ticket)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Calendar writes are never executed without an approval token",
                "Pending calendar actions have a 24h expiry",
                "Approved action calls provider.create_event() and marks action as approved",
                "Rejected action is soft-deleted",
                "Tests cover approval and rejection flows with mocked provider",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_calendar.py -v\n"
                "cd backend && pytest -q  # full suite"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-007 (user model), TIME-011 (entitlements for premium gate on calendar write)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-015: Notification and Replan Approval System"),
        ),
    },

    {
        "summary": "TIME-015: Notification and Replan Approval System",
        "labels": ["phase-3", "backend", "notifications", "replanning"],
        "description": doc(
            h2("Goal"),
            p("Build the backend approval flow for AI-generated schedule replans. "
              "The AI proposes a replan; the user must approve or reject before any calendar changes occur. "
              "Also build the notification preference enforcement layer."),
            divider(),
            h2("Scope"),
            bullet_list([
                "ReplanProposal model: user_id, proposed_changes (JSON), status (pending/approved/rejected), expires_at",
                "ReplanRepository: create, get, approve, reject",
                "POST /replans — AI creates a replan proposal (premium only)",
                "GET /replans/pending — list pending proposals for user",
                "POST /replans/{id}/approve — user approves; triggers calendar writes",
                "POST /replans/{id}/reject — user rejects; proposal discarded",
                "NotificationQueue model: stores scheduled push notifications with delivery status",
                "Notification modes: gentle (1x/day), balanced (3x/day), active_coach (unlimited)",
                "Celery task: process_pending_notifications — checks mode limits before sending",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No actual push notification delivery in this ticket (FCM/APNs integration is a later ticket)",
                "No smart scheduling algorithm (TIME-030+)",
                "No replan UI (mobile tickets)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Replan proposals require Premium entitlement (403 for free users)",
                "Replan cannot auto-approve — user action required",
                "Approved replan triggers calendar write via CalendarProvider",
                "Notification mode limits are enforced (gentle users don't get spammed)",
                "Tests cover approval, rejection, and mode-limit enforcement",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_notifications.py -v\n"
                "cd backend && pytest -q  # full suite"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-011 (entitlements), TIME-014 (calendar provider) must be complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-016: Referral Program"),
        ),
    },

    # ── PHASE 4 ──────────────────────────────────────────────────────────────

    {
        "summary": "TIME-018: iOS App Shell and Navigation",
        "labels": ["phase-4", "ios", "swiftui", "navigation"],
        "description": doc(
            h2("Goal"),
            p("Create the native SwiftUI app shell with bottom tab navigation, empty state screens "
              "for all five tabs, design token system, and the API client foundation. "
              "After this ticket the app builds and runs on simulator showing a polished empty state "
              "for each tab. No real data yet."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Xcode project: ios/TimeSense.xcodeproj — bundle ID com.timesense.app",
                "TimeSenseApp.swift — @main entry point, environment setup",
                "RootTabView.swift — TabView with 5 tabs: Now, Today, Capture, Insights, Settings",
                "Feature folder per tab: ios/TimeSense/Features/{Now,Today,Capture,Insights,Settings}/",
                "Empty state view per tab with SF Symbol icon, title, and subtitle",
                "Design tokens: Colors.swift (brand palette), Typography.swift (font styles), Spacing.swift",
                "APIClient.swift — async/await URLSession wrapper, auth header injection",
                "Endpoints.swift — typed endpoint enum (health, auth, users, onboarding)",
                "AppConfig.swift — reads API base URL from Info.plist",
                "AuthState.swift — @Observable auth state enum",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No Firebase Auth integration in this ticket",
                "No real API calls — APIClient compiles but is not wired to live data",
                "No onboarding flow screens",
                "No subscription or paywall UI",
                "No push notification registration",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "App builds with xcodebuild without errors",
                "All 5 tabs visible and tappable in simulator",
                "Each tab shows a placeholder with SF Symbol icon, title, and subtitle",
                "Design tokens used everywhere — no hardcoded hex colors or font sizes",
                "APIClient compiles and injectable via @Environment",
                "No force-unwraps in shipping code",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build \\\n"
                "  -project ios/TimeSense.xcodeproj \\\n"
                "  -scheme TimeSense \\\n"
                "  -destination 'platform=iOS Simulator,name=iPhone 16' \\\n"
                "  CODE_SIGNING_ALLOWED=NO | tail -5"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-002 (FastAPI health endpoint) complete."),
            divider(),
            h2("Next Ticket"),
            p("TIME-019: Android App Shell and Navigation"),
        ),
    },

    {
        "summary": "TIME-019: Android App Shell and Navigation",
        "labels": ["phase-4", "android", "kotlin", "compose", "navigation"],
        "description": doc(
            h2("Goal"),
            p("Create the native Kotlin/Jetpack Compose Android app shell with bottom navigation, "
              "empty state screens for all five tabs, design token system, and the API client foundation. "
              "After this ticket the app builds, installs on emulator, and shows polished empty states "
              "for each tab. No real data yet."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Android project: android/ — package com.timesense.app, minSdk 26, targetSdk 35",
                "MainActivity.kt — single-activity entry point, edge-to-edge display",
                "TimeSenseNavigation.kt — NavHost with 5 bottom nav destinations",
                "BottomNavBar.kt — Material3 NavigationBar with icon + label per tab",
                "Feature folder per tab: android/app/.../ui/{now,today,capture,insights,settings}/",
                "Empty state composable per screen: icon, title, subtitle",
                "DesignTokens.kt — brand color scheme (light + dark), typography, spacing, shapes",
                "APIClient.kt — OkHttp wrapper, Bearer auth header, typed error sealed class",
                "AppConfig.kt — reads API base URL from BuildConfig",
                "AppViewModel.kt — auth state and premium flag",
                "Gradle files: settings.gradle.kts, app/build.gradle.kts with Compose BOM 2024.x",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No Firebase Auth integration in this ticket",
                "No real API calls — APIClient compiles but not wired to live data",
                "No onboarding flow screens",
                "No subscription or paywall UI",
                "No push notification registration",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "App builds with ./gradlew assembleDebug without errors",
                "All 5 bottom nav tabs visible and tappable",
                "Each screen shows a non-empty placeholder (icon + title + subtitle)",
                "Design tokens used — no hardcoded color values or sp/dp magic numbers",
                "No force non-null assertions (!!) in shipping code",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd android && ./gradlew assembleDebug\n"
                "# Expect: BUILD SUCCESSFUL\n\n"
                "cd android && ./gradlew test\n"
                "# Expect: BUILD SUCCESSFUL"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-018 (iOS shell) for design parity reference."),
            divider(),
            h2("Next Ticket"),
            p("TIME-020: iOS Firebase Auth + Onboarding"),
        ),
    },

    {
        "summary": "TIME-020: iOS Firebase Auth and Onboarding Flow",
        "labels": ["phase-4", "ios", "swift", "auth", "firebase"],
        "description": doc(
            h2("Goal"),
            p("Implement Firebase Auth on iOS: Google Sign-In, Email/Password sign-in, "
              "Apple Sign-In coordinator, a polished SignInView, and an OnboardingView "
              "shown to new users after first authentication. AppState and TimeSenseApp "
              "are wired to AuthService so auth state drives navigation."),
            divider(),
            h2("Scope"),
            bullet_list([
                "ios/TimeSense/Core/Auth/AuthService.swift — FirebaseAuth wrapper, @Published currentUser, Google + Apple + Email sign-in",
                "ios/TimeSense/Core/Auth/AppleSignInCoordinator.swift — ASAuthorizationController delegate",
                "ios/TimeSense/Features/Auth/SignInView.swift — sign-in screen (Google, Apple, Email/Password)",
                "ios/TimeSense/Features/Auth/OnboardingView.swift — welcome + get-started for new users",
                "ios/TimeSense/App/AppState.swift — bind(to: AuthService) drives isAuthenticated",
                "ios/TimeSense/App/ContentView.swift and TimeSenseApp.swift — auth-gated navigation",
                "ios/Package.swift — Firebase + GoogleSignIn SPM packages",
                "Xcode project.pbxproj updated to include all auth source files",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No backend user profile creation in this ticket",
                "No subscription or paywall UI",
                "No calendar or notification permission requests",
                "No Google Sign-In client ID wired — placeholder used; real value in TIME-022",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "App builds: xcodebuild -target TimeSense -sdk iphonesimulator BUILD SUCCEEDED",
                "SignInView shows Google, Apple, and Email/Password sign-in options",
                "Unauthenticated users see SignInView; authenticated users see MainTabView",
                "New users (isNewUser=true) see OnboardingView before MainTabView",
                "AuthService properly removes auth state listener on deinit",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild -target TimeSense -sdk iphonesimulator18.0 "
                "CODE_SIGNING_ALLOWED=NO -quiet 2>&1 | tail -3\n"
                "# Expect: ** BUILD SUCCEEDED **"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-018 (iOS App Shell) — TabView and AppState foundation."),
            divider(),
            h2("Next Ticket"),
            p("TIME-021: Android Firebase Auth and Onboarding Flow"),
        ),
    },

    {
        "summary": "TIME-021: Android Firebase Auth and Onboarding Flow",
        "labels": ["phase-4", "android", "kotlin", "auth", "firebase"],
        "description": doc(
            h2("Goal"),
            p("Implement Firebase Auth on Android: Google Sign-In via Credential Manager, "
              "Email/Password sign-in, a polished SignInScreen composable, and an OnboardingScreen "
              "shown to new users. AppViewModel is wired to AuthRepository so auth state drives "
              "navigation in TimeSenseApp composable."),
            divider(),
            h2("Scope"),
            bullet_list([
                "android/.../core/auth/AuthRepository.kt — FirebaseAuth wrapper, authStateFlow, Google + Email",
                "android/.../features/auth/AuthViewModel.kt — CredentialManager Google sign-in, email/password",
                "android/.../features/auth/SignInScreen.kt — sign-in composable (Google OutlinedButton + Email form)",
                "android/.../features/auth/OnboardingScreen.kt — welcome screen for new users",
                "android/.../AppViewModel.kt — maps AuthRepository.authStateFlow to AppUiState",
                "android/.../TimeSenseApp.kt — AnimatedContent showing auth vs main vs onboarding",
                "android/app/build.gradle.kts — Firebase BOM, auth-ktx, credentials, Google Identity",
                "android/gradle/libs.versions.toml — all library version entries",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No backend user profile creation in this ticket",
                "No subscription or paywall UI",
                "No Google Sign-In client ID wired — placeholder (BuildConfig.GOOGLE_SERVER_CLIENT_ID = '')",
                "google-services.json is a placeholder; real values added when Firebase project created",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "App builds: ./gradlew assembleDebug BUILD SUCCESSFUL",
                "SignInScreen shows Google button and email/password form",
                "Unauthenticated users see SignInScreen; authenticated users see MainNavHost",
                "New users (isNewUser=true in AppUiState) route to OnboardingScreen",
                "No Firebase runtime crash on app launch (placeholder google-services.json present)",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd android && ./gradlew assembleDebug\n"
                "# Expect: BUILD SUCCESSFUL"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-019 (Android App Shell) — bottom nav and AppViewModel foundation."),
            divider(),
            h2("Next Ticket"),
            p("TIME-022: Backend Onboarding State APIs"),
        ),
    },

    {
        "summary": "TIME-022: Backend Onboarding State APIs",
        "labels": ["phase-4", "backend", "fastapi", "onboarding"],
        "description": doc(
            h2("Goal"),
            p("Build the backend endpoints that mobile clients call during and after onboarding: "
              "create/get user profile, persist onboarding state so users can resume mid-flow, "
              "and save consent records. After this ticket a mobile client can POST credentials, "
              "create a user row, and store their onboarding step."),
            divider(),
            h2("Scope"),
            bullet_list([
                "UserProfile model: id, firebase_uid, email, display_name, onboarding_step, completed_onboarding, created_at",
                "OnboardingState model: user_id, step (enum), metadata (JSON), updated_at",
                "POST /api/v1/users/profile — create or upsert user profile from Firebase token",
                "GET  /api/v1/users/profile — return current user's profile",
                "PATCH /api/v1/users/profile — update display name, onboarding step",
                "POST /api/v1/users/onboarding — save onboarding step + metadata",
                "GET  /api/v1/users/onboarding — resume onboarding (returns current step)",
                "Alembic migration for user_profiles and onboarding_states tables",
                "Unit tests: upsert idempotency, onboarding state persistence",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No subscription or payment records in this ticket",
                "No calendar integration setup in this ticket",
                "No push notification token registration",
                "No admin user management",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/users/profile is idempotent (same firebase_uid → upsert, not duplicate)",
                "PATCH /api/v1/users/profile updates only provided fields",
                "Onboarding step persists across app restarts (GET returns last saved step)",
                "All endpoints require valid Firebase JWT (401 without token)",
                "Alembic migration applies cleanly: alembic upgrade head",
                "pytest -k users passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "# Expect: no errors\n\n"
                "cd backend && pytest tests/test_users.py -v\n"
                "# Expect: all tests pass\n\n"
                "cd backend && pytest\n"
                "# Full suite still green"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-002 (FastAPI structure), TIME-003 (auth middleware), TIME-004 (DB + Alembic)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-033: Task Model and Internal Reminders"),
        ),
    },

    {
        "summary": "TIME-033: Task Model and Internal Reminders",
        "labels": ["phase-5", "backend", "fastapi", "task"],
        "description": doc(
            h2("Goal"),
            p("Build the core Task data model and CRUD API that all downstream features depend on: "
              "capture, scheduling, the Today screen, scoring, and the recommendation engine. "
              "A Task represents something a user needs to do; an InternalReminder is a generated "
              "system reminder tied to a task or a time. After this ticket the mobile clients can "
              "create, list, update, and delete tasks."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Task model: id, user_id, title, description, status (pending|in_progress|done|cancelled), "
                "priority (1–5), estimated_minutes, scheduled_start, scheduled_end, due_at, "
                "source (capture|calendar|manual), raw_input, created_at, updated_at",
                "InternalReminder model: id, user_id, task_id (FK nullable), type, trigger_at, "
                "delivered_at, status (pending|delivered|dismissed)",
                "Alembic migration for tasks and internal_reminders tables",
                "TaskRepository: create, get_by_id, list_by_user (status filter, date range), update, soft-delete",
                "TaskService: create_from_capture (stores raw_input), update_status, reschedule, list_for_today",
                "POST /api/v1/tasks — create task",
                "GET  /api/v1/tasks — list tasks (query params: status, date)",
                "GET  /api/v1/tasks/{task_id} — get single task",
                "PATCH /api/v1/tasks/{task_id} — update task fields",
                "DELETE /api/v1/tasks/{task_id} — soft-delete (status=cancelled)",
                "Pydantic schemas: TaskCreate, TaskUpdate, TaskResponse",
                "Unit tests: create, list by date, status transitions, delete idempotency",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No LLM parsing in this ticket — raw_input stored as-is",
                "No scheduling algorithm — scheduled_start/end set by caller or null",
                "No push notification delivery",
                "No calendar event creation from tasks",
                "No recurrence rules",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/tasks creates a task and returns TaskResponse",
                "GET /api/v1/tasks?status=pending returns only pending tasks for the authenticated user",
                "GET /api/v1/tasks?date=2026-07-03 returns tasks scheduled on that date",
                "PATCH /api/v1/tasks/{id} updates only provided fields",
                "DELETE /api/v1/tasks/{id} sets status=cancelled (not hard-deleted)",
                "Tasks from one user are not visible to another user",
                "Alembic migration applies cleanly",
                "pytest -k tasks passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "# Expect: no errors\n\n"
                "cd backend && pytest tests/test_tasks.py -v\n"
                "# Expect: all pass\n\n"
                "cd backend && pytest -q\n"
                "# Full suite still green"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-022 (user profile API — user_id FK), TIME-002 (FastAPI structure)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-037: LLM Gateway"),
        ),
    },

    {
        "summary": "TIME-037: LLM Gateway",
        "labels": ["phase-5", "backend", "llm", "fastapi"],
        "description": doc(
            h2("Goal"),
            p("Build an LLM provider abstraction (LLMGateway ABC + OpenAI implementation) "
              "and a CaptureParser service that converts raw user text into a structured "
              "TaskCreate. After this ticket, the Capture screen can submit text and get back "
              "a fully parsed task with title, estimated_minutes, due_at, and priority."),
            divider(),
            h2("Scope"),
            bullet_list([
                "app/integrations/llm_base.py — LLMGateway ABC: complete(messages, model, max_tokens, temperature) → str",
                "app/integrations/openai_gateway.py — OpenAI implementation using openai Python SDK",
                "app/services/capture_service.py — CaptureParser.parse(raw_input, user_timezone) → TaskCreate",
                "System prompt: extract title, estimated_minutes (nullable), due_at (nullable ISO datetime), priority (1–5 int)",
                "POST /api/v1/capture — accepts {raw_input: str}, returns TaskResponse (creates and saves the task)",
                "Fallback: if LLM parse fails return Task with title=raw_input, other fields null",
                "Unit tests: parse basic input, parse with time ('call dentist tomorrow at 2pm'), fallback on LLM error",
                "OPENAI_API_KEY added to app/core/config.py (optional — gateway no-ops if not set)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No streaming LLM responses in this ticket",
                "No Anthropic / other provider implementations (just OpenAI default + ABC)",
                "No voice transcription in this ticket",
                "No multi-turn conversation",
                "No calendar event creation from capture",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/capture with raw_input='call dentist tomorrow at 2pm' returns status 201 with a Task",
                "Task title is parsed from raw input (not just the raw string)",
                "If OPENAI_API_KEY not set, capture falls back gracefully — task created with raw_input as title",
                "LLMGateway is an ABC — OpenAI implementation is swappable",
                "pytest -k capture passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_capture.py -v\n"
                "# Expect: all pass\n\n"
                "cd backend && pytest -q\n"
                "# Full suite still green"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-033 (Task Model — CaptureParser creates a Task), TIME-002 (FastAPI structure)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-030: Capture Screen (iOS and Android connect to POST /capture)"),
        ),
    },

    {
        "summary": "TIME-030: Capture Screen — Connect iOS and Android to POST /capture",
        "labels": ["phase-5", "ios", "android", "capture"],
        "description": doc(
            h2("Goal"),
            p("Wire the existing Capture UI stubs on iOS and Android to POST /api/v1/capture. "
              "After this ticket users can type a task in plain text, tap Capture, and see it "
              "created with LLM-extracted fields. Loading and error states are shown inline."),
            divider(),
            h2("Scope"),
            bullet_list([
                "iOS: ios/TimeSense/Features/Capture/CaptureView.swift — call APIClient POST /capture, show loading spinner, clear on success",
                "iOS: ios/TimeSense/Features/Capture/CaptureViewModel.swift — ObservableObject wrapping capture API call, uiState (idle/loading/success/error)",
                "Android: CaptureScreen.kt — call ApiClient POST /capture via CaptureViewModel, show CircularProgressIndicator, clear on success",
                "Android: features/capture/CaptureViewModel.kt — ViewModel with StateFlow<CaptureUiState>",
                "Shared: capture API response is a Task — display success toast/banner with extracted title",
                "Error handling: show inline error message with retry option",
                "Empty input: Capture button disabled until text is non-blank",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No voice recording in this ticket",
                "No offline queue — if network fails show error",
                "No task list refresh on this screen (Today screen will pick it up)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Typing text and tapping Capture calls POST /api/v1/capture",
                "Loading spinner visible during request",
                "On success: input cleared, success message shows extracted task title",
                "On network error: error message shown, input preserved",
                "Capture button disabled when input is empty",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "# iOS build\n"
                "xcodebuild -target TimeSense -sdk iphonesimulator18.0 CODE_SIGNING_ALLOWED=NO -quiet\n"
                "# Expect: ** BUILD SUCCEEDED **\n\n"
                "# Android build\n"
                "cd android && ./gradlew assembleDebug\n"
                "# Expect: BUILD SUCCESSFUL"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-037 (POST /capture endpoint), TIME-018 (iOS App Shell), TIME-019 (Android App Shell)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-031: Today Screen — Realistic Timeline"),
        ),
    },

    {
        "summary": "TIME-031: Today Screen — Realistic Timeline",
        "labels": ["phase-5", "ios", "android", "backend"],
        "description": doc(
            h2("Goal"),
            p("Render a full-day scrollable timeline on the Today tab showing scheduled tasks "
              "in past/current/future visual states. Data comes from GET /api/v1/timeline/today "
              "which aggregates today's tasks sorted by scheduled_start."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: GET /api/v1/timeline/today — returns tasks scheduled for today, sorted by scheduled_start. Returns TimelineItem list with id, title, scheduled_start, scheduled_end, status.",
                "iOS: ios/TimeSense/Features/Today/TodayView.swift — scrollable List/ScrollView of TimelineCard rows",
                "iOS: ios/TimeSense/Features/Today/TodayViewModel.swift — @MainActor ObservableObject, loads /timeline/today on appear",
                "iOS: ios/TimeSense/Features/Today/TimelineCard.swift — shows title, time, duration, visual state (past=dimmed, current=highlighted, future=normal)",
                "Android: features/today/TodayScreen.kt — LazyColumn of TimelineCard composables, observes TodayViewModel StateFlow",
                "Android: features/today/TodayViewModel.kt — loads timeline on init, exposes StateFlow<TodayUiState>",
                "Android: features/today/TimelineCard.kt — composable matching iOS visual spec",
                "Visual states: past tasks dimmed (50% opacity), current task has accent border, future normal",
                "Empty state: 'Nothing scheduled today — use Capture to add tasks' message",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No calendar events integration (Phase 6)",
                "No drag-and-drop reordering (non-negotiable, not at launch)",
                "No routine blocks rendering",
                "No task editing from this screen",
                "No pull-to-refresh (auto-load on appear is sufficient)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/api/v1/timeline.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/tests/test_timeline.py (new)",
                "ios/TimeSense/Features/Today/TodayView.swift",
                "ios/TimeSense/Features/Today/TodayViewModel.swift (new)",
                "ios/TimeSense/Features/Today/TimelineCard.swift (new)",
                "android/.../features/today/TodayScreen.kt",
                "android/.../features/today/TodayViewModel.kt (new)",
                "android/.../features/today/TimelineCard.kt (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/timeline/today returns 200 with task list for authenticated user",
                "Tasks are sorted by scheduled_start ascending",
                "iOS Today tab shows timeline list on load",
                "Past tasks visually dimmed, current task highlighted",
                "Empty state message shown when no tasks scheduled",
                "iOS build succeeds: xcodebuild → BUILD SUCCEEDED",
                "Android build succeeds: ./gradlew assembleDebug → BUILD SUCCESSFUL",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "# Backend tests\n"
                "cd backend && pytest tests/test_timeline.py -v\n\n"
                "# iOS build\n"
                "xcodebuild -target TimeSense -sdk iphonesimulator18.0 CODE_SIGNING_ALLOWED=NO -quiet\n"
                "# Expect: ** BUILD SUCCEEDED **\n\n"
                "# Android build\n"
                "cd android && ./gradlew assembleDebug\n"
                "# Expect: BUILD SUCCESSFUL"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-030 (Capture wired), TIME-033 (Task model — GET /tasks already exists)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-032: Now Screen — Current Context and Recommendation"),
        ),
    },

    {
        "summary": "TIME-032: Now Screen — Current Context and Recommendation",
        "labels": ["phase-5", "ios", "android", "backend"],
        "description": doc(
            h2("Goal"),
            p("Show the user's current moment: how much usable time is available right now, "
              "the single best next task to work on, and quick action buttons (Done / Snooze / "
              "Not Now / Ask). Data comes from GET /api/v1/now which returns context + "
              "one best recommendation from the tasks scheduled today."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: GET /api/v1/now — returns usable_minutes (hardcoded 60 for now), best_task (highest-priority pending task scheduled today or overdue), greeting string",
                "Backend: NowResponse schema: greeting, usable_minutes, best_task (TaskResponse | null)",
                "Backend: 5 tests: authenticated, no tasks returns null best_task, picks highest priority, picks overdue task, unauthenticated 401",
                "iOS: NowView — hero card with greeting, usable time pill, task card with title/estimated time, quick action row (Done/Snooze/Not Now)",
                "iOS: NowViewModel — loads /api/v1/now on .task, handles Done action (PATCH /tasks/{id} status=done), Snooze action (stub for now)",
                "Android: NowScreen — same hero layout, LazyColumn not needed (single card), collectAsState",
                "Android: NowViewModel — same logic as iOS ViewModel",
                "Quick actions: Done calls PATCH /api/v1/tasks/{id} with {status: done}, then reloads; Snooze is no-op stub; Not Now reloads",
                "Empty state: 'Nothing on your plate right now' when best_task is null",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No real usable-time calculation (Phase 8 — UsableTimeCalculator)",
                "No LLM-generated recommendation explanations (Phase 8)",
                "No 'Why this?' action in this ticket",
                "No Replan action in this ticket",
                "No calendar integration",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/api/v1/now.py (new)",
                "backend/app/api/v1/__init__.py",
                "backend/tests/test_now.py (new)",
                "ios/TimeSense/Features/Now/NowView.swift",
                "ios/TimeSense/Features/Now/NowViewModel.swift (new)",
                "android/.../features/now/NowScreen.kt",
                "android/.../features/now/NowViewModel.kt (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/now returns 200 with greeting, usable_minutes, best_task",
                "best_task is null when no pending tasks exist",
                "best_task is the highest-priority pending task for today",
                "iOS Now tab shows hero card and task card on load",
                "Tapping Done updates task status and reloads",
                "iOS build succeeds",
                "Android build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py -v\n\n"
                "xcodebuild -target TimeSense -sdk iphonesimulator18.0 CODE_SIGNING_ALLOWED=NO -quiet\n"
                "# Expect: ** BUILD SUCCEEDED **\n\n"
                "cd android && ./gradlew assembleDebug\n"
                "# Expect: BUILD SUCCESSFUL"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-031 (Today screen, tasks endpoint), TIME-033 (Task model)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-034: Usable Time Calculator (Phase 8 — Recommendation Engine V1)"),
        ),
    },

    {
        "summary": "TIME-034: Usable Time Calculator",
        "labels": ["phase-8", "backend"],
        "description": doc(
            h2("Goal"),
            p("Replace the hardcoded 60-minute stub in GET /api/v1/now with a real calculation "
              "of how many usable minutes remain between now and the next scheduled block (or "
              "end of the workday at 18:00 local time). Wire the result into GET /api/v1/now."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/services/usable_time.py: UsableTimeCalculator class",
                "calculate(tasks: list[Task], user_timezone: str) -> int: minutes from now to next block or EOD",
                "Considers: scheduled_start of pending/in_progress tasks; end of work day = 18:00 local",
                "Returns 0 if current time is past EOD",
                "backend/app/api/v1/now.py: replace usable_minutes=60 with UsableTimeCalculator.calculate()",
                "Pass user_preferences.timezone (default UTC) into the calculator",
                "Tests: 6+ tests covering free afternoon, task starting soon, task in progress, past EOD, no tasks",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No calendar integration (Phase 6)",
                "No routine/meal/commute blocks (Phase 9)",
                "No focus window detection (beyond simple free-time calculation)",
                "No mobile changes",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/usable_time.py (new)",
                "backend/app/api/v1/now.py (update usable_minutes stub)",
                "backend/tests/test_usable_time.py (new)",
                "backend/tests/test_now.py (update to check usable_minutes varies)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "usable_minutes in GET /api/v1/now is calculated, not hardcoded",
                "If next task starts in 45 min, usable_minutes = 45",
                "If no tasks scheduled, usable_minutes = minutes until 18:00 local (capped at 480)",
                "If past 18:00, usable_minutes = 0",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_usable_time.py tests/test_now.py -v"),
            divider(),
            h2("Dependencies"),
            p("TIME-032 (GET /api/v1/now stub), TIME-033 (Task model)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-035: Task Scoring Service"),
        ),
    },

    {
        "summary": "TIME-035: Task Scoring Service",
        "labels": ["phase-8", "backend"],
        "description": doc(
            h2("Goal"),
            p("Score pending task candidates by priority, deadline urgency, and estimated duration "
              "vs usable time. Returns a ranked list so the recommendation engine can pick the best."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/services/task_scorer.py: TaskScorer class",
                "score(task, usable_minutes, now) -> float: lower = better",
                "Scoring factors: priority (1-5, weight 0.5), deadline urgency (overdue=0, due today=0.2, future=0.5+), estimated fit (fits in window=bonus, exceeds window=penalty)",
                "rank(tasks, usable_minutes, now) -> list[Task]: sorted by score ascending",
                "Tests: 6+ tests covering priority ordering, deadline urgency, overdue tasks, duration fit",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No energy level scoring (Phase 9)",
                "No goal alignment scoring (Phase 9)",
                "No LLM-based scoring",
                "No mobile changes",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/task_scorer.py (new)",
                "backend/tests/test_task_scorer.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Priority 1 task scores better than priority 5 with same deadline",
                "Overdue task ranks above future task of same priority",
                "Task that fits in usable window scores better than one that doesn't",
                "All scorer tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_task_scorer.py -v"),
            divider(),
            h2("Dependencies"),
            p("TIME-034 (UsableTimeCalculator for usable_minutes input)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-036: Recommendation API V1"),
        ),
    },

    {
        "summary": "TIME-036: Recommendation API V1",
        "labels": ["phase-8", "backend"],
        "description": doc(
            h2("Goal"),
            p("Return one best recommendation and up to two alternatives to the mobile app. "
              "Replace the simple priority-sort in GET /api/v1/now with TaskScorer. "
              "Add a 'why' field with a brief LLM-generated explanation."),
            divider(),
            h2("Scope"),
            bullet_list([
                "GET /api/v1/recommendations — new endpoint returning RecommendationResponse",
                "RecommendationResponse: best (TaskResponse + why: str), alternatives: list[TaskResponse] (up to 2)",
                "Uses TaskScorer.rank() for ordering, UsableTimeCalculator.calculate() for context",
                "LLM 'why' explanation via LLMGateway.complete_simple() — short one-sentence reason",
                "Fallback 'why' when LLM unavailable: 'High priority task due soon.'",
                "Update GET /api/v1/now to use TaskScorer instead of min(priority) sort",
                "Tests: 6+ covering best recommendation, alternatives, why fallback, empty state",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No mobile UI changes (Now screen already shows best_task)",
                "No 'Ask' action or multi-turn conversation",
                "No feedback collection (TIME-038)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/api/v1/recommendations.py (new)",
                "backend/app/api/v1/__init__.py",
                "backend/app/api/v1/now.py (update to use TaskScorer)",
                "backend/tests/test_recommendations.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/recommendations returns best task with why string",
                "Returns up to 2 alternatives",
                "why falls back gracefully when LLM unavailable",
                "GET /api/v1/now best_task now uses TaskScorer ranking",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_recommendations.py tests/test_now.py -v"),
            divider(),
            h2("Dependencies"),
            p("TIME-034 (UsableTimeCalculator), TIME-035 (TaskScorer), TIME-037 (LLM Gateway — already done)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-038: Feedback Collection"),
        ),
    },

    {
        "summary": "TIME-038: Feedback Collection",
        "labels": ["phase-8", "backend"],
        "description": doc(
            h2("Goal"),
            p("Let users react to a recommendation (Done / Snooze / Not Now) and store that "
              "reaction so the recommendation engine stops re-suggesting a task the user just "
              "dismissed or snoozed. Feedback storage must not require a mobile UI change in "
              "this ticket — it just needs a backend contract the apps can call."),
            divider(),
            h2("Scope"),
            bullet_list([
                "recommendation_feedback table: user_id, task_id, signal (done/snooze/not_now), "
                "snooze_until (nullable), timestamps",
                "POST /api/v1/recommendations/feedback — records a signal for a task",
                "signal=done also marks the task status=done (via TaskRepository.update)",
                "signal=snooze stores snooze_until; signal=not_now stores no expiry",
                "Feedback signal integration into the recommendation flow: GET /api/v1/recommendations "
                "excludes tasks with an active snooze (snooze_until in the future) or a recent "
                "not_now (cooldown window) from candidates, per the 'do not nag' rule in the "
                "recommendation-engine skill",
                "Tests: 8+ covering feedback CRUD, done marks task done, ownership checks, "
                "invalid signal rejection, and suppression of snoozed/not_now tasks in recommendations",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No mobile UI for the feedback buttons (Done/Snooze/Not Now actions) — API only",
                "No feedback-driven scorer weight learning (e.g. adjusting priority weights over time)",
                "No weekly insight generation from feedback (later phase)",
                "No 'Bad Suggestion' / 'Wrong timing' / 'Wrong context' signal types — only done/snooze/not_now",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/models/recommendation_feedback.py (new)",
                "backend/migrations/versions/*_add_recommendation_feedback.py (new)",
                "backend/app/api/v1/recommendations.py (new POST /feedback route)",
                "backend/app/repositories/recommendation_feedback_repository.py (new)",
                "backend/app/services/recommendation_service.py (filter suppressed tasks)",
                "backend/tests/test_feedback.py (new)",
                "backend/tests/test_recommendations.py (suppression tests)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/recommendations/feedback returns 201 with the stored signal",
                "signal=done marks the referenced task status=done",
                "signal=snooze with snooze_until in the future removes that task from "
                "GET /api/v1/recommendations candidates until snooze_until passes",
                "signal=not_now removes that task from candidates for a cooldown window",
                "Feedback for a task owned by another user returns 404",
                "Invalid signal value returns 422",
                "Unauthenticated request returns 401",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_feedback.py tests/test_recommendations.py -v"),
            divider(),
            h2("Dependencies"),
            p("TIME-036 (Recommendation API V1 — GET /api/v1/recommendations and RecommendationService)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-039: Routine Assumptions Model"),
        ),
    },

    {
        "summary": "TIME-039: Routine Assumptions Model",
        "labels": ["phase-9", "backend"],
        "description": doc(
            h2("Goal"),
            p("Store a per-user set of recurring daily routine blocks (sleep, meals, hygiene) that "
              "aren't on the calendar but still consume time, and let the user view/edit them. "
              "Every user gets sensible defaults on first access so the feature works with zero "
              "setup; editing one marks it as customized so future automatic-learning tickets "
              "(commute/sleep detection) know not to silently overwrite a user's explicit choice."),
            divider(),
            h2("Scope"),
            bullet_list([
                "RoutineAssumption model: id, user_id, routine_type (sleep|breakfast|lunch|dinner|"
                "morning_hygiene|evening_hygiene), start_minute/end_minute (0–1439, minutes since local "
                "midnight; end < start means the block wraps past midnight, e.g. sleep), is_customized",
                "Alembic migration for routine_assumptions table",
                "RoutineAssumptionRepository: get_or_seed_defaults(user_id) — returns the user's 6 "
                "routine rows, creating them from DEFAULT_ROUTINES on first call; update_one(user_id, "
                "routine_type, start_minute, end_minute) — marks is_customized=True",
                "GET /api/v1/routines — list the user's routine assumptions (seeds defaults if none exist)",
                "PATCH /api/v1/routines/{routine_type} — update start/end minute for one routine",
                "Tests: 8+ covering default seeding, idempotent seeding, valid update, is_customized "
                "flip, invalid routine_type, invalid minute range, cross-user isolation, auth",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No integration into UsableTimeService yet — routine blocks are not yet subtracted "
                "from usable time. UsableTimeService is not timezone-aware today (it only knows UTC "
                "midnight); wiring routines in properly needs that fixed first, and doing it once "
                "meal/commute/sleep signals also exist (TIME-040–042) avoids three separate partial "
                "integrations. Tracked as a follow-up in known_issues.md.",
                "No automatic learning/detection from user behavior (that's TIME-041 commute "
                "detection and TIME-042 sleep/wake signal ticket-by-ticket, or a later insights phase)",
                "No per-day-of-week customization — one block per routine_type, applies every day",
                "No mobile UI for editing routines — API only",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/models/routine.py (new)",
                "backend/migrations/versions/*_add_routine_assumptions.py (new)",
                "backend/app/repositories/routine_repository.py (new)",
                "backend/app/schemas/routine.py (new)",
                "backend/app/api/v1/routines.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register model)",
                "backend/tests/test_routines.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/routines returns 6 default routine rows on first call for a new user",
                "Calling GET /api/v1/routines twice does not create duplicate rows",
                "PATCH /api/v1/routines/{routine_type} updates start_minute/end_minute and sets "
                "is_customized=True",
                "PATCH with an unknown routine_type returns 404",
                "PATCH with start_minute or end_minute outside 0–1439 returns 422",
                "One user's routines are not visible to another user",
                "Unauthenticated requests return 401",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_routines.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-022 (user profile — user_id FK), TIME-034 (UsableTimeService — future integration target)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-040: Meal Tracking (Lightweight)"),
        ),
    },

    {
        "summary": "TIME-040: Meal Tracking (Lightweight)",
        "labels": ["phase-9", "backend"],
        "description": doc(
            h2("Goal"),
            p("Track whether the user ate, skipped, or worked through breakfast/lunch/dinner — "
              "timing and status only, per the product rule that meal tracking stays lightweight "
              "(no calories, macros, or nutrition). Surface skipped meals to the recommendation "
              "response so the assistant has that context, without changing scoring math."),
            divider(),
            h2("Scope"),
            bullet_list([
                "MealEvent model: id, user_id, meal_type (breakfast|lunch|dinner), "
                "status (eaten|skipped|eating_while_working), occurred_at",
                "Alembic migration for meal_events table",
                "MealRepository: log(user_id, meal_type, status, occurred_at) — create an event; "
                "get_today_status(user_id, now) -> dict[meal_type, status] — returns the latest "
                "logged status for each meal today, or infers 'skipped' once that meal's "
                "RoutineAssumption window (TIME-039) has passed with nothing logged, or 'pending' "
                "if the window hasn't ended yet",
                "POST /api/v1/meals — log a meal event",
                "GET /api/v1/meals/today — today's status for breakfast/lunch/dinner",
                "GET /api/v1/recommendations gains a `skipped_meals: list[str]` field (meal_types "
                "currently inferred or logged as skipped today)",
                "Tests: 10+ covering logging, idempotent status lookup, skip inference once a "
                "routine window passes, pending before the window ends, explicit log overriding "
                "inference, cross-user isolation, invalid meal_type/status, recommendations "
                "surfacing skipped_meals",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No calories, macros, or nutrition tracking (explicit product rule)",
                "No changes to TaskScorer weights or ranking based on meal status — skipped_meals "
                "is exposed as context only, not scored",
                "No synthetic 'eat lunch' task suggestions",
                "No mobile UI for logging meals — API only",
                "Skip inference reuses each meal's UTC minute-of-day RoutineAssumption window "
                "directly (same UTC-only simplification UsableTimeService already uses) — not "
                "blocked on the timezone-awareness follow-up tracked in known_issues.md",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/models/meal.py (new)",
                "backend/migrations/versions/*_add_meal_events.py (new)",
                "backend/app/repositories/meal_repository.py (new)",
                "backend/app/schemas/meal.py (new)",
                "backend/app/api/v1/meals.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register model)",
                "backend/app/api/v1/recommendations.py (add skipped_meals field)",
                "backend/tests/test_meals.py (new)",
                "backend/tests/test_recommendations.py (skipped_meals coverage)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/meals logs an event and returns it",
                "GET /api/v1/meals/today returns 'pending' for a meal whose window hasn't ended "
                "and nothing has been logged",
                "GET /api/v1/meals/today returns 'skipped' once that meal's window has passed with "
                "no log",
                "An explicit log (eaten/skipped/eating_while_working) always wins over inference",
                "GET /api/v1/recommendations includes skipped_meals reflecting the same status",
                "One user's meal events are not visible to another user",
                "Invalid meal_type or status returns 422",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_meals.py tests/test_recommendations.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-039 (Routine Assumption windows for skip inference), TIME-036 (Recommendation API)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-041: Commute Detection"),
        ),
    },

    {
        "summary": "TIME-041: Commute Detection",
        "labels": ["phase-9", "backend", "privacy"],
        "description": doc(
            h2("Goal"),
            p("Detect a likely commute from a batch of location points the mobile app submits, "
              "and require the user to confirm it before it's treated as real signal — never "
              "silently assume. Reuses the existing consent and notification/approval "
              "infrastructure rather than inventing new mechanisms for either."),
            divider(),
            h2("Scope"),
            bullet_list([
                "CommuteEvent model: user_id, direction (to_work|to_home), detected_start, "
                "detected_end, estimated_minutes, status (pending|confirmed|rejected), "
                "notification_id (FK, mirrors ReplanRequest's approval-notification link)",
                "Alembic migration for commute_events table",
                "CommuteService.detect_from_pings(pings) — pure heuristic: haversine displacement "
                "between first/last ping must exceed 500m, elapsed time must be 5–120 minutes; "
                "direction inferred from the first ping's UTC hour (<14 → to_work, else to_home — "
                "same UTC-only simplification already used by UsableTimeService/RoutineAssumption)",
                "CommuteService.propose_commute(user_id, pings) — gates on effective "
                "location_tracking consent (existing consent_records/ConsentRepository, per the "
                "privacy-security-consent skill) raising if not granted; on a detected candidate, "
                "creates a pending CommuteEvent + an approval_needed Notification (same pattern "
                "NotificationService.propose_replan already uses)",
                "CommuteService.confirm/reject(user_id, commute_id) — user must approve or reject; "
                "nothing is ever auto-confirmed",
                "POST /api/v1/commute/detect, GET /api/v1/commute/pending, "
                "POST /api/v1/commute/{id}/confirm, POST /api/v1/commute/{id}/reject",
                "Raw lat/lng points are never persisted — only the derived commute window is "
                "stored, matching the product's raw-sensitive-data-minimization posture",
                "Tests: 12+ covering detection math, consent gate (403 without location_tracking "
                "consent granted), confirm/reject flow, no-op when displacement/time don't qualify, "
                "cross-user isolation, notification creation",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No real calendar-event-location correlation — no CalendarEvent table with "
                "location data exists yet in this codebase; that's a separate future ticket",
                "No mobile location-permission request UI or CoreLocation/FusedLocationProvider "
                "integration — this ticket is the backend contract only, same split TIME-042 uses "
                "for its iOS HealthKit piece",
                "No background/scheduled detection — the mobile app decides when to submit a ping "
                "batch (e.g. after a period of movement); this ticket doesn't add a Celery job",
                "No changes to UsableTimeService/recommendations based on commute — that's follow-up "
                "work once confirmed commute data has accumulated",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/models/commute.py (new)",
                "backend/migrations/versions/*_add_commute_events.py (new)",
                "backend/app/repositories/commute_repository.py (new)",
                "backend/app/schemas/commute.py (new)",
                "backend/app/services/commute_service.py (new)",
                "backend/app/api/v1/commutes.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register model)",
                "backend/tests/test_commutes.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/commute/detect without location_tracking consent granted returns 403",
                "A ping batch with >500m displacement and 5–120 min elapsed time creates a pending "
                "CommuteEvent and an approval_needed Notification",
                "A ping batch with too little displacement or an out-of-range duration detects nothing",
                "POST /api/v1/commute/{id}/confirm sets status=confirmed; reject sets status=rejected",
                "One user cannot see or confirm/reject another user's commute events",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_commutes.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-010 (consent_records / ConsentRepository), TIME-015 (Notification model / approval pattern)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-042: Sleep/Wake Signal Integration"),
        ),
    },

    {
        "summary": "TIME-042: Sleep/Wake Signal Integration",
        "labels": ["phase-9", "backend", "privacy"],
        "description": doc(
            h2("Goal"),
            p("Capture a sleep/wake signal (initially submitted by the mobile app, e.g. from "
              "HealthKit sleep analysis) and, when the user wakes meaningfully later than their "
              "assumed sleep-routine wake time, propose a morning replan for their approval. "
              "Reuses the existing RoutineAssumption 'sleep' block (TIME-039) as the expected-wake "
              "baseline and the existing ReplanRequest/Notification approval flow (TIME-015) — no "
              "new replan mechanism, no auto-applied changes."),
            divider(),
            h2("Scope"),
            bullet_list([
                "SleepWakeEvent model: user_id, wake_time (UTC datetime), sleep_start "
                "(nullable UTC datetime), source (healthkit|manual), replan_request_id "
                "(nullable FK to replan_requests, mirrors CommuteEvent's notification_id link)",
                "Alembic migration for sleep_wake_events table",
                "MorningReplanService.record_wake_event(user_id, wake_time, sleep_start, source) — "
                "gates on effective health_data consent (existing consent_records/ConsentRepository), "
                "raising if not granted; stores the event; compares wake_time's minute-of-day "
                "against the user's 'sleep' RoutineAssumption end_minute (same UTC-only "
                "simplification already used by RoutineAssumption/CommuteService/UsableTimeService, "
                "see known_issues.md) using a late-wake threshold (45 minutes)",
                "On a qualifying late wake with no replan already proposed for that day, calls "
                "NotificationService.propose_replan (existing approval-required flow) and links the "
                "resulting ReplanRequest back onto the SleepWakeEvent",
                "POST /api/v1/sleep/events (ingest one wake signal, returns the event plus whether "
                "a replan was suggested), GET /api/v1/sleep/today",
                "No new approve/reject endpoints — a suggested replan is approved/rejected through "
                "the existing POST /api/v1/notifications/replans/{id}/approve|reject routes",
                "Tests: 10+ covering consent gate (403 without health_data consent), late wake "
                "creates a pending ReplanRequest + notification, on-time wake does not, a second "
                "wake event the same day does not create a second replan, cross-user isolation",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No iOS HealthKit read integration, entitlements, or permission-prompt UI "
                "(ios/.../HealthService.swift) — this ticket is the backend contract only, same "
                "backend/mobile split TIME-041 used for its location-permission piece; HealthKit "
                "wiring needs device testing this environment can't do and is its own decision point",
                "No real user-timezone-aware minute comparison — same UTC-only simplification "
                "already used by RoutineAssumption/UsableTimeService/CommuteService; full timezone "
                "integration is planned as one unified pass after Phase 9's signals all exist",
                "No automatic replan execution — matches the product rule that replans always "
                "require explicit user approval (decision_log.md)",
                "No sleep quality/duration scoring or Insights surfacing — only a wake-time-vs-"
                "assumption comparison for morning replan triggering",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/models/sleep_wake.py (new)",
                "backend/migrations/versions/*_add_sleep_wake_events.py (new)",
                "backend/app/repositories/sleep_wake_repository.py (new)",
                "backend/app/schemas/sleep_wake.py (new)",
                "backend/app/services/morning_replan.py (new)",
                "backend/app/api/v1/sleep.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register model)",
                "backend/tests/test_sleep_wake.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/sleep/events without health_data consent granted returns 403",
                "A wake event >= 45 minutes past the user's sleep-routine assumed wake time creates "
                "a pending ReplanRequest and a replan_request notification",
                "A wake event within the threshold does not trigger a replan suggestion",
                "A second wake event on the same day does not create a second pending replan",
                "One user cannot see or trigger a replan tied to another user's sleep events",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_sleep_wake.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-039 (RoutineAssumption sleep block), TIME-010 (consent_records / "
              "ConsentRepository), TIME-015 (Notification/ReplanRequest approval pattern)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-043: Notification Modes and Learning Prompts"),
        ),
    },

    {
        "summary": "TIME-043: Notification Modes and Learning Prompts",
        "labels": ["phase-10", "backend"],
        "description": doc(
            h2("Goal"),
            p("Give the existing notification_mode preference (gentle|balanced|active_coach, "
              "already stored on UserPreferences but not yet acted on anywhere) real behavior: "
              "a daily morning check-in, an evening check-out, and — for active_coach users still "
              "in their early Learning Mode window — a learning prompt confirming a still-default "
              "routine assumption. Each is a distinct, mode-gated, once-per-day notification, "
              "reusing the existing Notification model/send_notification path with no new "
              "delivery mechanism."),
            divider(),
            h2("Scope"),
            bullet_list([
                "NotificationEvent model: user_id, event_type "
                "(morning_checkin|evening_checkout|learning_prompt), notification_id "
                "(nullable FK to notifications) — an audit trail that also drives once-per-day "
                "dedup, same pattern as SleepWakeEvent/CommuteEvent's own event tables",
                "Alembic migration for notification_events table",
                "NotificationService gains three gated methods: maybe_send_morning_checkin(), "
                "maybe_send_evening_checkout(), maybe_send_routine_learning_prompt() — each checks "
                "the user's notification_mode and NotificationEvent dedup before calling the "
                "existing send_notification()",
                "Mode behavior: gentle -> evening check-out only; balanced -> morning check-in + "
                "evening check-out; active_coach -> both check-ins + learning prompts. This maps "
                "directly onto the product brief's 'Active Coach / Learning Mode' framing rather "
                "than inventing an unrelated fourth concept",
                "Learning prompt is concrete, not a no-op stub: maybe_send_routine_learning_prompt() "
                "checks the user's 'sleep' RoutineAssumption (TIME-039) — if it's still is_customized "
                "= False and the account is within a 14-day learning window (reusing the existing "
                "14-day trial length as a pragmatic placeholder, not a new arbitrary number), it asks "
                "the user to confirm or adjust the assumed sleep block",
                "UserRepository.list_active_ids() — lightweight id-only query for the worker loop",
                "backend/app/workers/notification_tasks.py — three thin Celery tasks "
                "(send_morning_checkins, send_evening_checkouts, send_learning_prompts) that iterate "
                "active users and call the corresponding NotificationService method per user, plus a "
                "celery beat schedule wiring them to morning/evening/mid-morning times",
                "Tests: 12+ covering each mode's on/off behavior for each check-in type, once-per-day "
                "dedup, learning prompt firing only when the routine is still default and within the "
                "learning window, and cross-user isolation — all at the service layer against "
                "db_session, matching this repo's existing pattern for non-HTTP-triggered flows "
                "(see test_notifications.py)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No new user-facing preference API — notification_mode read/write already exists "
                "(PATCH /api/v1/users/me/preferences, from an earlier ticket); this ticket only adds "
                "behavior that acts on it",
                "No real Celery beat/worker execution test — no Redis/Docker available in this "
                "environment (see known_issues.md); tasks are thin wrappers around the tested "
                "service methods, following the same untested-Celery-shim precedent as the existing "
                "app/workers/health_task.py",
                "No data-driven Learning Mode end date — deliberately reuses the 14-day trial length "
                "as a placeholder window rather than building the 'ends based on enough data, not "
                "fixed days' logic from decision_log.md; that remains its own future ticket",
                "No push notification delivery (APNs/FCM) — same as all existing Notification rows, "
                "delivery is a separate integration-provider concern (see integration-provider-pattern "
                "skill) and out of scope here",
                "No additional learning prompts beyond the routine-confirmation one — meal/commute/ "
                "sleep-specific learning prompts are a natural follow-up once this mechanism exists",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/models/notification_event.py (new)",
                "backend/migrations/versions/*_add_notification_events.py (new)",
                "backend/app/repositories/notification_repository.py (add NotificationEventRepository)",
                "backend/app/repositories/user_repository.py (add list_active_ids())",
                "backend/app/services/notification_service.py (add the three gated methods)",
                "backend/app/workers/notification_tasks.py (new)",
                "backend/app/workers/celery_app.py (register new task module + beat schedule)",
                "backend/app/models/__init__.py (register model)",
                "backend/tests/test_notification_orchestration.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "gentle mode: maybe_send_morning_checkin() sends nothing; "
                "maybe_send_evening_checkout() still sends",
                "balanced mode: both check-ins send; maybe_send_routine_learning_prompt() sends nothing",
                "active_coach mode: both check-ins send; learning prompt sends only when the sleep "
                "routine is still uncustomized and the account is within the learning window",
                "Calling the same maybe_send_* method twice in one day only creates one Notification "
                "and one NotificationEvent the second time returns None",
                "One user's notification mode/state never affects another user's check-ins",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_notification_orchestration.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-015 (Notification model / NotificationService), TIME-039 (RoutineAssumption "
              "sleep block), the earlier onboarding/preferences ticket that added "
              "UserPreferences.notification_mode."),
            divider(),
            h2("Next Ticket"),
            p("TIME-044: iOS Widgets"),
        ),
    },

    {
        "summary": "TIME-044: iOS Widgets",
        "labels": ["phase-10", "ios"],
        "description": doc(
            h2("Goal"),
            p("Add a WidgetKit extension to the iOS app with three home-screen widgets: usable "
              "time remaining today, the next scheduled event, and the current best-next-action "
              "task. Widgets read a lightweight snapshot the host app writes to a shared App Group "
              "container after its normal /now and /timeline/today fetches — the extension process "
              "never performs its own network calls or holds its own copy of the Firebase auth "
              "token, avoiding a second parallel auth implementation."),
            divider(),
            h2("Scope"),
            bullet_list([
                "New TimeSenseWidgetExtension target (WidgetKit app-extension, embedded in the "
                "TimeSense host app target, iOS 17.0 deployment target matching the app)",
                "App Group `group.com.timesense.app` + matching .entitlements files added to both "
                "the host app target and the new extension target (Simulator-buildable now; a real "
                "device build additionally needs the App Group registered against a real Apple "
                "Developer Team, which is still an open question per open_questions.md)",
                "WidgetSnapshot: a small Codable struct (usableMinutes, bestTask, nextEvent, "
                "updatedAt) persisted as JSON in the App Group's shared UserDefaults suite — the "
                "single contract between the app and the extension",
                "NowViewModel.load() and TodayViewModel.load() each update the relevant fields of "
                "the shared snapshot after a successful fetch (preserving fields the other call "
                "doesn't know about) and call WidgetCenter.shared.reloadAllTimelines()",
                "Three widgets sharing one TimelineProvider that reads the snapshot: "
                "UsableTimeWidget (systemSmall + accessoryRectangular), NextEventWidget, "
                "BestNextActionWidget — each with a meaningful empty state ('Nothing scheduled', "
                "'All caught up') rather than a blank or error-looking view, per the mobile-ux-"
                "premium skill's 'empty states have meaning' rule",
                "Timeline refresh policy re-requests a reload at the earlier of 30 minutes out or "
                "the next event's start time, using the last-known snapshot in the meantime — no "
                "push-triggered instant refresh in this ticket",
                "Widgets use DesignTokens.Typography/Spacing (pure value constants, safe to share "
                "across targets) but not DesignTokens.Color, since those are named-asset-catalog "
                "colors and no Assets.xcassets exists in this project yet even for the host app; "
                "widgets use system semantic colors (.primary/.secondary/.tint) instead",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No independent network/auth in the widget extension — it only ever reads the "
                "shared snapshot the host app wrote; this is a deliberate simplification, not an "
                "oversight, to avoid duplicating Firebase token-refresh logic into a second process",
                "No APNs-triggered background refresh — the widget's own data goes stale between "
                "app opens/timeline windows exactly like any WidgetKit app without a push pipeline; "
                "background push integration is a separate, later ticket",
                "No interactive widgets (App Intents / button taps that mutate state directly from "
                "the widget) — iOS 17 supports this, but it's extra surface area beyond this "
                "ticket's three read-only display widgets",
                "No lock-screen circular/inline complications — only systemSmall + "
                "accessoryRectangular families for now",
                "No real Apple Developer Team/App Group registration — this environment has no "
                "Apple Developer account configured (open_questions.md); entitlements are wired "
                "correctly for a Simulator build now and are ready to work once a real team exists",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense.xcodeproj/project.pbxproj (new target, entitlements, embed phase)",
                "ios/TimeSense/TimeSense.entitlements (new)",
                "ios/TimeSense/Core/Widgets/WidgetSnapshot.swift (new, shared by both targets)",
                "ios/TimeSenseWidget/TimeSenseWidgetBundle.swift (new)",
                "ios/TimeSenseWidget/UsableTimeWidget.swift (new)",
                "ios/TimeSenseWidget/NextEventWidget.swift (new)",
                "ios/TimeSenseWidget/BestNextActionWidget.swift (new)",
                "ios/TimeSenseWidget/Info.plist (new)",
                "ios/TimeSenseWidget/TimeSenseWidget.entitlements (new)",
                "ios/TimeSense/Features/Now/NowViewModel.swift (write snapshot + reload timelines)",
                "ios/TimeSense/Features/Today/TodayViewModel.swift (write snapshot + reload timelines)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "xcodebuild build succeeds for both the TimeSense scheme and the new widget "
                "extension target on the iphonesimulator SDK",
                "After NowViewModel.load() succeeds, the shared snapshot reflects the latest "
                "usable_minutes/best_task without erasing a previously-written next_event",
                "After TodayViewModel.load() succeeds, the shared snapshot reflects the latest "
                "next event without erasing a previously-written usable_minutes/best_task",
                "Each widget renders a meaningful empty state when its portion of the snapshot is "
                "nil/default rather than a blank view",
                "The widget extension target has no direct dependency on APIClient/AuthService or "
                "any network code",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-sdk iphonesimulator\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj "
                "-scheme TimeSenseWidgetExtension -sdk iphonesimulator"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-018 (iOS App Shell and Navigation), the existing GET /api/v1/now and "
              "GET /api/v1/timeline/today endpoints (no backend changes needed for this ticket)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-045: Android Widgets"),
        ),
    },

    {
        "summary": "TIME-045: Android Widgets",
        "labels": ["phase-10", "android"],
        "description": doc(
            h2("Goal"),
            p("Add two Jetpack Glance home-screen widgets — Usable Time and Next Event — mirroring "
              "TIME-044's iOS widgets. Unlike iOS's WidgetKit extension, Android AppWidgets run in "
              "the same app process, so each widget reads its own dedicated Glance-managed "
              "Preferences state that the relevant existing ViewModel writes after a successful "
              "fetch — no shared cross-widget blob or App-Group-equivalent is needed."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Add androidx.glance:glance-appwidget dependency (Jetpack Compose-for-widgets — "
                "keeps this native to Kotlin/Compose rather than legacy RemoteViews/XML layouts, "
                "per the project's Kotlin+Compose-exclusively rule)",
                "UsableTimeWidget (GlanceAppWidget) + UsableTimeWidgetReceiver "
                "(GlanceAppWidgetReceiver) — renders usable minutes remaining today, with an "
                "'Open TimeSense' empty state before the first sync, matching iOS's copy",
                "NextEventWidget (GlanceAppWidget) + NextEventWidgetReceiver — renders the next "
                "non-done, not-yet-ended scheduled event's title + time, or 'Nothing scheduled'",
                "AppWidgetProviderInfo XML resources for both (home-screen category, no periodic "
                "auto-refresh via updatePeriodMillis — refreshed only when the app itself calls "
                "update, same app-triggered-only policy as TIME-044's iOS widgets)",
                "NowViewModel (converted to AndroidViewModel to get an Application Context) calls "
                "UsableTimeWidget.updateUsableMinutes() + .updateAll() after a successful /now fetch",
                "TodayViewModel (also converted to AndroidViewModel) derives the next upcoming "
                "event via a pure, unit-testable function and calls NextEventWidget.updateNextEvent()"
                "/.clearNextEvent() + .updateAll() after a successful /timeline/today fetch",
                "Unit test for the next-event-selection pure function (JVM test, no Android/"
                "instrumentation dependency) covering: an upcoming event is picked, a past/done "
                "event is excluded, the earliest of several upcoming events wins, empty list "
                "returns null",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No best-next-action widget — this ticket's scope (per "
                "tickets/implementation_sequence.md) is usable-time + next-event only, unlike "
                "iOS's three widgets; a third widget can follow later if wanted for parity",
                "No periodic background refresh (WorkManager-driven polling) — the widget only "
                "updates when the app's own NowViewModel/TodayViewModel successfully fetch, same "
                "as iOS; a push/background-refresh pipeline is separate, later work",
                "No widget configuration activity, no resizing-aware multiple layouts — a single "
                "small-size layout for each widget",
                "No changes to backend endpoints — reuses the existing GET /api/v1/now and "
                "GET /api/v1/timeline/today",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "android/gradle/libs.versions.toml (add glance version/library entry)",
                "android/app/build.gradle.kts (add glance-appwidget dependency)",
                "android/app/src/main/java/com/timesense/app/widgets/UsableTimeWidget.kt (new)",
                "android/app/src/main/java/com/timesense/app/widgets/UsableTimeWidgetReceiver.kt (new)",
                "android/app/src/main/java/com/timesense/app/widgets/NextEventWidget.kt (new)",
                "android/app/src/main/java/com/timesense/app/widgets/NextEventWidgetReceiver.kt (new)",
                "android/app/src/main/res/xml/usable_time_widget_info.xml (new)",
                "android/app/src/main/res/xml/next_event_widget_info.xml (new)",
                "android/app/src/main/res/layout/glance_default_loading_layout.xml (new)",
                "android/app/src/main/AndroidManifest.xml (register both widget receivers)",
                "android/app/src/main/java/com/timesense/app/features/now/NowViewModel.kt "
                "(AndroidViewModel + widget update call)",
                "android/app/src/main/java/com/timesense/app/features/today/TodayViewModel.kt "
                "(AndroidViewModel + next-event derivation + widget update call)",
                "android/app/src/test/java/com/timesense/app/features/today/"
                "NextEventSelectionTest.kt (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "./gradlew assembleDebug succeeds",
                "./gradlew test succeeds, including the new next-event-selection unit test",
                "After NowViewModel's /now call succeeds, UsableTimeWidget's Glance state reflects "
                "the latest usable_minutes",
                "After TodayViewModel's /timeline/today call succeeds, NextEventWidget's Glance "
                "state reflects the next upcoming event, or is cleared when none exists",
                "Both widgets render a meaningful empty state rather than a blank view when their "
                "state is unset",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd android && ./gradlew assembleDebug\n"
                "cd android && ./gradlew test"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-019 (Android App Shell and Navigation), the existing GET /api/v1/now and "
              "GET /api/v1/timeline/today endpoints (no backend changes needed for this ticket), "
              "TIME-044 (iOS Widgets, same product surface on the other platform)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-046: Weekly Insights Generation"),
        ),
    },

    {
        "summary": "TIME-046: Weekly Insights Generation",
        "labels": ["phase-11", "backend", "ios", "android"],
        "description": doc(
            h2("Goal"),
            p("Generate a calm, retrospective weekly summary of the user's most recently "
              "completed week (task completion, meal/sleep/commute signals, recommendation "
              "feedback) and surface it on the Insights tab (Premium-gated) on both iOS and "
              "Android. Reuses the existing LLMGateway explanation pattern (LLM writes the "
              "prose, a template fallback covers LLM failures) rather than inventing a new "
              "generation mechanism."),
            divider(),
            h2("Scope"),
            bullet_list([
                "WeeklyInsight model: user_id, week_start/week_end (the Monday-Sunday range), "
                "tasks_completed, tasks_total, completion_rate, most_skipped_meal, "
                "late_wake_count, commute_confirmed_count, feedback_done_count, "
                "feedback_not_now_count, summary_text; unique on (user_id, week_start)",
                "InsightsService.generate_for_week(user_id, week_start) aggregates from existing "
                "tables only — Task (completed/total via created_at/updated_at in range), "
                "RecommendationFeedback (done/not_now counts in range), MealEvent (skipped counts "
                "by meal_type in range), SleepWakeEvent (count with replan_request_id set in "
                "range), CommuteEvent (confirmed count in range) — then calls LLMGateway for a "
                "2-3 sentence summary, falling back to a templated sentence on LLM failure, "
                "identical fallback pattern to RecommendationService._explain()",
                "GET /api/v1/insights/weekly (Premium-gated via the existing PremiumUser "
                "dependency) — returns the most recently completed week's insight, generating it "
                "on first request if the weekly Celery job hasn't run yet for that week",
                "GET /api/v1/insights/history?limit=8 (also Premium-gated) — past generated weeks",
                "backend/app/workers/insights_tasks.py — one Celery task generating the "
                "just-completed week's insight for every active user, scheduled Monday 5am UTC; "
                "untested in this environment (no Redis/Docker), same precedent as "
                "notification_tasks.py",
                "iOS: InsightsViewModel.swift + real InsightsView.swift content (loading/loaded/"
                "error states) replacing the current static empty-state placeholder, gated behind "
                "the existing isPremium check",
                "Android: InsightsViewModel.kt (new) + real InsightsScreen.kt content, same states, "
                "same premium gate",
                "Tests: 12+ backend tests covering the aggregation math (completion rate, most-"
                "skipped-meal tie-breaking, late-wake/commute counts, date-range boundaries), "
                "premium gate (403), LLM fallback, cross-user isolation, and idempotent "
                "generation (calling generate_for_week twice for the same week doesn't duplicate)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "most_skipped_meal only reflects meals explicitly logged with status=skipped "
                "(via POST /api/v1/meals) during the week — it does not retroactively backfill "
                "inferred-but-never-logged skips from days the user never opened the app, since "
                "that inference (MealRepository.get_today_status) is live/read-time-only, not "
                "persisted historically. This is a known, documented limitation, not a bug to fix",
                "tasks_completed/tasks_total use updated_at/created_at as proxies (Task has no "
                "explicit completed_at field yet) — approximate, not exact, and documented as such",
                "No 'current week so far' view — only fully completed Monday-Sunday weeks are "
                "summarized, avoiding noisy/incomplete mid-week numbers",
                "No trend charts, graphs, or comparisons across multiple weeks beyond the simple "
                "history list — that's a richer Insights v2 concern",
                "TIME-047 (Learned Assumptions Settings) is separate follow-up work, not folded "
                "into this ticket despite both touching Settings/Insights-adjacent surfaces",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/models/insight.py (new)",
                "backend/migrations/versions/*_add_weekly_insights.py (new)",
                "backend/app/repositories/insight_repository.py (new)",
                "backend/app/repositories/task_repository.py (add range-count methods)",
                "backend/app/repositories/recommendation_feedback_repository.py (add range-count)",
                "backend/app/repositories/meal_repository.py (add skipped-count-by-type-in-range)",
                "backend/app/repositories/sleep_wake_repository.py (add late-wake-count-in-range)",
                "backend/app/repositories/commute_repository.py (add confirmed-count-in-range)",
                "backend/app/schemas/insight.py (new)",
                "backend/app/services/insights_service.py (new)",
                "backend/app/api/v1/insights.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register model)",
                "backend/app/workers/insights_tasks.py (new)",
                "backend/app/workers/celery_app.py (register task module + beat schedule)",
                "backend/tests/test_insights.py (new)",
                "ios/TimeSense/Features/Insights/InsightsViewModel.swift (new)",
                "ios/TimeSense/Features/Insights/InsightsView.swift (real content)",
                "android/app/src/main/java/com/timesense/app/features/insights/InsightsViewModel.kt (new)",
                "android/app/src/main/java/com/timesense/app/features/insights/InsightsScreen.kt (real content)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/insights/weekly without Premium returns 403",
                "GET /api/v1/insights/weekly generates and returns the most recently completed "
                "week's insight on first call, and returns the same cached row on a second call",
                "Aggregation numbers (tasks_completed/total, most_skipped_meal, late_wake_count, "
                "commute_confirmed_count, feedback counts) match hand-computed expectations for a "
                "seeded set of tasks/events across a week boundary",
                "GET /api/v1/insights/history returns generated weeks ordered most-recent-first",
                "One user cannot see another user's insights",
                "iOS and Android builds succeed with the new Insights screen wired to the endpoint",
                "All backend tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_insights.py -v\n"
                "cd backend && pytest -q\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -target TimeSense "
                "-sdk iphonesimulator CODE_SIGNING_ALLOWED=NO\n"
                "cd android && ./gradlew assembleDebug && ./gradlew test"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-037 (LLM Gateway), TIME-038 (RecommendationFeedback), TIME-039/040/041/042 "
              "(routine/meal/commute/sleep event tables this ticket aggregates), TIME-018/019 "
              "(iOS/Android app shells with an existing Insights tab placeholder)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-047: Learned Assumptions Settings"),
        ),
    },

    {
        "summary": "TIME-047: Learned Assumptions Settings",
        "labels": ["phase-11", "ios", "android"],
        "description": doc(
            h2("Goal"),
            p("Let users see and edit what TimeSense has learned/assumed about their daily "
              "routine — the sleep/meal/hygiene blocks from TIME-039's RoutineAssumption model — "
              "from a new Settings screen on both iOS and Android. Pure UI work: reuses the "
              "existing GET/PATCH /api/v1/routines endpoints as-is, no backend changes."),
            divider(),
            h2("Scope"),
            bullet_list([
                "iOS: LearnedAssumptionsViewModel.swift (GET /api/v1/routines, PATCH per "
                "routine_type) + LearnedAssumptionsView.swift — a list of the 6 routine types "
                "(sleep, breakfast, lunch, dinner, morning_hygiene, evening_hygiene) each showing "
                "a friendly label, formatted time range (respecting the sleep block's overnight "
                "wraparound), and an 'Edited' badge when is_customized is true; tapping a row "
                "opens a sheet with two time pickers (start/end) and Save/Cancel",
                "Android: LearnedAssumptionsViewModel.kt (same two endpoints) + "
                "LearnedAssumptionsScreen.kt — same list/edit-dialog shape using Material3's "
                "TimePicker in an AlertDialog wrapper",
                "A new 'Learned Assumptions' row added to each platform's Settings screen "
                "(Preferences section) that navigates to the new screen — iOS via the existing "
                "per-tab NavigationStack/NavigationLink, Android by adding one more destination "
                "to the existing single-NavHost tab structure and passing a navigation callback "
                "into SettingsScreen",
                "Loading/error/loaded states on both platforms, per the mobile-ux-premium and "
                "native-android-compose/native-ios-swiftui skills' required states",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No backend changes — GET/PATCH /api/v1/routines already fully supports this "
                "(built in TIME-039); this ticket is UI-only on both platforms",
                "No editing of any other 'learned' data (meal skip patterns, commute times, sleep "
                "signal history) — only the RoutineAssumption blocks, matching the ticket's stated "
                "scope ('Learned assumptions display, edit flow in Settings')",
                "No approval/confirmation flow beyond a normal Save button — RoutineAssumption "
                "edits are a user preference, not a calendar write or a replan, so the product's "
                "calendar/replan-approval rules don't apply here",
                "No validation beyond what the existing PATCH endpoint already enforces "
                "(0-1439 minute-of-day bounds) — no new business rules invented",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Features/Settings/LearnedAssumptionsViewModel.swift (new)",
                "ios/TimeSense/Features/Settings/LearnedAssumptionsView.swift (new)",
                "ios/TimeSense/Features/Settings/SettingsView.swift (add navigation row)",
                "android/.../features/settings/LearnedAssumptionsViewModel.kt (new)",
                "android/.../features/settings/LearnedAssumptionsScreen.kt (new)",
                "android/.../features/settings/SettingsScreen.kt (add navigation row)",
                "android/.../navigation/MainNavHost.kt (register new destination)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Settings shows a 'Learned Assumptions' row on both platforms that opens the new "
                "screen",
                "The screen lists all 6 routine types with a human-readable time range",
                "Editing a routine's start/end time and saving calls PATCH /api/v1/routines/"
                "{routine_type} and reflects the update in the list without a full-screen reload",
                "A routine that has been edited shows an indicator that it's no longer the default",
                "iOS and Android builds succeed",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -target TimeSense "
                "-sdk iphonesimulator CODE_SIGNING_ALLOWED=NO\n"
                "cd android && ./gradlew assembleDebug && ./gradlew test"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-039 (RoutineAssumption model + GET/PATCH /api/v1/routines), TIME-018/019 "
              "(iOS/Android app shells with existing Settings screens)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-048: Admin Dashboard Foundation (Web)"),
        ),
    },

    {
        "summary": "TIME-048: Admin Dashboard Foundation (Web)",
        "labels": ["phase-12", "web", "backend"],
        "description": doc(
            h2("Goal"),
            p("Stand up the web companion app (React/Next.js, the first ticket to touch `web/` — "
              "no scaffold exists yet) and build a role-protected admin dashboard: key metrics, "
              "user search, invite code management, subscription/trial view, feedback review, "
              "and integration status. The ticket sequence's scope line implies the backend "
              "already exposes all of this, but only user-listing and invite-code management "
              "admin endpoints actually exist today — this ticket adds the missing "
              "subscription/feedback/integration/metrics admin endpoints alongside the web UI, "
              "rather than shipping a dashboard with dead ends."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Bootstrap `web/`: Next.js 14 (App Router) + TypeScript + Tailwind, matching "
                "architecture_overview.md's planned `web/app/admin/` layout",
                "Firebase Auth (web SDK) wired the same way as iOS/Android: env-var-driven "
                "config, graceful placeholder gap (no real Firebase project exists yet — "
                "open_questions.md) — login itself can't be exercised end-to-end here, same as "
                "the mobile apps' known gap",
                "`lib/api.ts` (fetch wrapper attaching the Firebase ID token as a Bearer header, "
                "mirroring ApiClient.swift/ApiClient.kt) and `lib/auth.ts` (auth context/hook)",
                "`/admin` route: checks the authenticated user's `role` (from GET /api/v1/users/me) "
                "client-side for UX, but the real security boundary stays server-side via the "
                "existing `AdminUser` FastAPI dependency — client-side gating never substitutes "
                "for it",
                "`/admin/users`: searchable, paginated user list — extends the existing "
                "GET /api/v1/admin/users with a `search` param (email match) and fixes its "
                "`total` field, which was hardcoded to `len(users)` instead of a real count",
                "`/admin/invites`: list/create/disable invite codes and view the waitlist — uses "
                "the existing GET/POST /api/v1/invites/codes, DELETE /api/v1/invites/codes/"
                "{code}, POST /api/v1/invites/waitlist/{id}/invite as-is, no backend changes here",
                "`/admin/subscriptions` (new): GET /api/v1/admin/subscriptions — subscription/"
                "trial status per user (platform, status, plan, trial_end, cancel_at_period_end)",
                "`/admin/feedback` (new): GET /api/v1/admin/feedback — recent "
                "RecommendationFeedback rows across all users (task title, signal, user email, "
                "when)",
                "Dashboard home (new): GET /api/v1/admin/metrics (total users, active/trialing "
                "subscription counts, waitlist size, active invite codes, calendar integrations "
                "connected) and GET /api/v1/admin/integrations (calendar integration counts by "
                "provider/active status)",
                "Tests: 15+ backend tests covering each new/changed admin endpoint's data "
                "correctness, the 403-without-admin-role gate, and cross-user aggregation "
                "correctness (metrics/feedback/subscriptions reflect all users, not just one)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No public-facing web companion (landing page, signup, regular-user /app/* "
                "routes like insights/settings/subscription) — those aren't in the ticket "
                "sequence yet and are out of scope; this ticket is the admin surface only",
                "No real Firebase project — same placeholder-config gap already tracked for iOS/"
                "Android; login can't be exercised end-to-end in this environment",
                "No Stripe checkout or billing-management UI beyond read-only subscription status",
                "No write actions beyond what already existed (invite code create/disable) — "
                "subscriptions/feedback/integrations/metrics are read-only views in this ticket",
                "No automated web test suite — no existing web test infra to extend; verification "
                "is `npm run build` succeeding plus the backend's pytest coverage for the new "
                "endpoints",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "web/package.json, tsconfig.json, next.config.js, tailwind.config.ts, "
                "postcss.config.js (new)",
                "web/app/layout.tsx, web/app/globals.css, web/app/page.tsx (new, minimal)",
                "web/lib/firebase.ts, web/lib/auth.tsx, web/lib/api.ts (new)",
                "web/app/admin/layout.tsx, web/app/admin/page.tsx (new — dashboard home/metrics)",
                "web/app/admin/users/page.tsx (new)",
                "web/app/admin/invites/page.tsx (new)",
                "web/app/admin/subscriptions/page.tsx (new)",
                "web/app/admin/feedback/page.tsx (new)",
                "backend/app/schemas/admin.py (new response schemas)",
                "backend/app/api/v1/admin.py (new routes: subscriptions, feedback, integrations, "
                "metrics; extend users with search)",
                "backend/app/repositories/user_repository.py (search + count_all)",
                "backend/app/repositories/subscription_repository.py (list_all, "
                "count_by_status)",
                "backend/app/repositories/recommendation_feedback_repository.py (list_recent)",
                "backend/app/repositories/calendar_repository.py (count_by_provider)",
                "backend/tests/test_admin.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/admin/users?search=... filters by email substring and returns an "
                "accurate total count",
                "GET /api/v1/admin/subscriptions, /feedback, /integrations, /metrics all return "
                "403 for a non-admin user and correct aggregated data for an admin",
                "The web app's /admin route redirects/blocks non-admin users at the UI layer "
                "(defense in depth; the API remains the real gate)",
                "npm run build succeeds for the web app",
                "All backend tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_admin.py -v\n"
                "cd backend && pytest -q\n"
                "cd web && npm install && npm run build"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-007-010 (core auth/admin foundation), TIME-036/038 (recommendation feedback), "
              "existing invite/waitlist system, existing Subscription/CalendarIntegration models."),
            divider(),
            h2("Next Ticket"),
            p("TIME-049: Slack Integration"),
        ),
    },

    {
        "summary": "TIME-049: Slack Integration",
        "labels": ["phase-13", "backend", "integration"],
        "description": doc(
            h2("Goal"),
            p("Lightweight action-item detection from Slack: read a user's recent Slack messages, "
              "use the LLM to detect which ones are genuine action items for that user, and surface "
              "each as a pending suggestion the user must explicitly approve before it becomes a "
              "Task. Never auto-creates tasks — mirrors the existing calendar-write approval gate "
              "(PendingCalendarAction) exactly, and reuses the LLMGateway + the message-source "
              "provider abstraction rather than hardcoding Slack SDK calls into services."),
            divider(),
            h2("Scope"),
            bullet_list([
                "MessageSourceProvider ABC (backend/app/integrations/message_source_base.py) + "
                "SlackMessageSource impl (slack_source.py) calling Slack's conversations.history "
                "Web API — mirrors the existing calendar_base.py / google_calendar.py flat-file "
                "pattern already in this repo (not the skill's idealized subdirectory layout)",
                "SlackIntegration model (user_id, access_token, team_id, is_active) — token "
                "storage, same shape as CalendarIntegration",
                "SlackActionItem model (user_id, channel, message_ts, source_text, detected_title, "
                "detected_priority, detected_estimated_minutes, status pending|confirmed|rejected, "
                "created_task_id FK) — the approval queue, mirroring PendingCalendarAction",
                "Alembic migration for slack_integrations + slack_action_items tables",
                "SlackDetectionService.detect(message_text) — LLM call via LLMGateway returning "
                "{is_action_item, title, estimated_minutes, priority}; templated no-op fallback "
                "(is_action_item=False) on LLM failure, same graceful-degradation pattern as "
                "CaptureService",
                "SlackService.connect/disconnect (token mgmt), scan_channel (reads messages via "
                "the provider, runs detection, creates pending SlackActionItem rows for detected "
                "items — NEVER tasks), list_pending, confirm (creates a real Task from a pending "
                "item — the approval gate), reject",
                "POST /api/v1/slack/connect, DELETE /api/v1/slack/disconnect, POST /api/v1/slack/"
                "scan (Premium-gated, like calendar reads), GET /api/v1/slack/pending, "
                "POST /api/v1/slack/actions/{id}/confirm, POST /api/v1/slack/actions/{id}/reject",
                "Add 'slack' to TaskSource literal so confirmed items are attributable",
                "Tests: 14+ covering detection (action-item vs not), scan creates pending items "
                "not tasks, confirm creates a Task with source=slack + links created_task_id, "
                "reject, Premium gate (403) on scan, LLM-failure fallback, cross-user isolation",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No real Slack OAuth flow / Slack app — SLACK_CLIENT_ID/SECRET/SIGNING_SECRET are "
                "empty placeholders in .env (no Slack app registered yet), same gap as Firebase/"
                "Stripe/Google. The mobile client does OAuth and POSTs the resulting token to "
                "/slack/connect, exactly like the existing /calendar/connect flow — no server-side "
                "OAuth callback handler in this ticket",
                "No Slack Events API / real-time push (Socket Mode, event subscriptions, request "
                "signature verification) — scanning is user/app-initiated via POST /slack/scan, "
                "not push-triggered; the slack_signing_secret stays unused for now",
                "No writing back to Slack (posting messages, reactions) — read-only, so no "
                "Slack-side approval gate is needed beyond the task-creation approval already built",
                "No token encryption-at-rest beyond how CalendarIntegration already stores tokens "
                "(plain Text column) — matching existing behavior; a cross-integration encryption "
                "pass is separate future work (noted in known_issues.md)",
                "No Free Basic Mode background auto-scan — scanning is explicit and Premium-gated; "
                "there's no Celery job polling Slack in this ticket",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/integrations/message_source_base.py (new)",
                "backend/app/integrations/slack_source.py (new)",
                "backend/app/models/slack.py (new)",
                "backend/migrations/versions/*_add_slack_integration.py (new)",
                "backend/app/repositories/slack_repository.py (new)",
                "backend/app/schemas/slack.py (new)",
                "backend/app/services/slack_service.py (new)",
                "backend/app/api/v1/slack.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register models)",
                "backend/app/schemas/task.py (add 'slack' to TaskSource)",
                "backend/tests/test_slack.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/slack/scan without Premium returns 403",
                "scan on a batch of messages creates pending SlackActionItem rows only for those "
                "the LLM flags as action items, and creates zero Tasks",
                "POST /api/v1/slack/actions/{id}/confirm creates a Task (source=slack) and links "
                "created_task_id on the item; a second confirm on the same item is rejected",
                "POST /api/v1/slack/actions/{id}/reject sets status=rejected and creates no Task",
                "LLM failure during scan degrades to detecting nothing (no crash, no tasks)",
                "One user cannot see or confirm/reject another user's Slack action items",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_slack.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-037 (LLM Gateway), TIME-006/033 (Task model), TIME-015-era "
              "calendar-integration/approval pattern this mirrors, TIME-003 (Premium entitlement "
              "gate)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-050: Microsoft Teams Integration"),
        ),
    },

    {
        "summary": "TIME-050: Microsoft Teams Integration",
        "labels": ["phase-13", "backend", "integration"],
        "description": doc(
            h2("Goal"),
            p("Lightweight action-item detection from Microsoft Teams, mirroring the Slack "
              "integration (TIME-049): read recent Teams chat messages via Microsoft Graph, "
              "LLM-detect which are genuine action items, and surface each as a pending suggestion "
              "the user must explicitly approve before it becomes a Task. Reuses the "
              "MessageSourceProvider abstraction and — as the second message source — extracts the "
              "LLM action-item detection into a shared, source-neutral service so both Slack and "
              "Teams share one copy (rule of three: generalize the detection now, keep the "
              "per-source models/service parallel until a third source justifies unifying them)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Extract SlackDetectionService's LLM logic into a shared source-neutral "
                "ActionItemDetectionService (app/services/action_item_detection.py); Slack keeps a "
                "backward-compatible SlackDetectionService alias so test_slack.py stays green",
                "TeamsMessageSource(MessageSourceProvider) (app/integrations/teams_source.py) "
                "reading Microsoft Graph /chats/{id}/messages; strips the HTML body to plain text",
                "TeamsIntegration model (user_id, access_token, tenant_id, is_active) + "
                "TeamsActionItem model (user_id, conversation_id, message_id, source_text, "
                "detected_title/priority/estimated_minutes, status, created_task_id) — parallel to "
                "the Slack tables, following the repo's per-feature-table precedent",
                "Alembic migration for teams_integrations + teams_action_items",
                "TeamsRepository (integration + action-item repos), schemas, TeamsService "
                "(connect/disconnect/scan/confirm/reject using the shared detection service), and "
                "TeamsNotConnected exception — mirroring SlackService exactly",
                "POST /api/v1/teams/connect (Premium), DELETE /api/v1/teams/disconnect, "
                "POST /api/v1/teams/scan (Premium — reads + detects, creates pending items only), "
                "GET /api/v1/teams/pending, POST /api/v1/teams/actions/{id}/confirm (approval gate "
                "→ Task, source=teams), POST /api/v1/teams/actions/{id}/reject",
                "Add 'teams' to the TaskSource literal",
                "Tests: 12+ mirroring test_slack.py (detection reuse, scan creates pending not "
                "tasks, confirm creates a Task source=teams, reject, Premium gate, isolation)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No real Microsoft OAuth flow / Azure AD app — MICROSOFT_CLIENT_ID/SECRET are empty "
                "placeholders in .env (present since the Phase-6 Outlook calendar scaffold). The "
                "mobile client does OAuth and POSTs the Graph token to /teams/connect, same as "
                "/slack/connect and /calendar/connect — no server-side OAuth callback here",
                "No Teams change-notifications / webhooks (Graph subscriptions) — scanning is "
                "user/app-initiated via POST /teams/scan, not push",
                "No writing back to Teams — read-only, so the only approval gate needed is the "
                "existing task-creation one",
                "No unification of the Slack + Teams tables into a single source-tagged "
                "message-source schema — deferred until/unless a third source (Notion messages, "
                "etc.) makes the duplication clearly worth a refactor migration (rule of three)",
                "No token encryption beyond how CalendarIntegration/SlackIntegration already store "
                "tokens (plain Text) — same cross-integration deferral noted in known_issues.md",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/action_item_detection.py (new, shared)",
                "backend/app/services/slack_service.py (use shared detection; keep alias)",
                "backend/app/integrations/teams_source.py (new)",
                "backend/app/models/teams.py (new)",
                "backend/migrations/versions/*_add_teams_integration.py (new)",
                "backend/app/repositories/teams_repository.py (new)",
                "backend/app/schemas/teams.py (new)",
                "backend/app/services/teams_service.py (new)",
                "backend/app/api/v1/teams.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register models)",
                "backend/app/schemas/task.py (add 'teams' to TaskSource)",
                "backend/tests/test_teams.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/teams/scan without Premium returns 403",
                "scan creates pending TeamsActionItem rows only for LLM-flagged action items, and "
                "creates zero Tasks",
                "POST /api/v1/teams/actions/{id}/confirm creates a Task (source=teams) and links "
                "created_task_id; a second confirm is rejected",
                "reject sets status=rejected and creates no Task",
                "LLM failure during scan degrades to detecting nothing",
                "One user cannot see or confirm/reject another user's Teams action items",
                "Slack tests still pass after the shared-detection extraction",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_teams.py tests/test_slack.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-049 (Slack integration + MessageSourceProvider abstraction this reuses), "
              "TIME-037 (LLM Gateway), TIME-006/033 (Task model), TIME-003 (Premium gate)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-051: Notion Integration"),
        ),
    },

    {
        "summary": "TIME-051: Notion Integration",
        "labels": ["phase-13", "backend", "integration"],
        "description": doc(
            h2("Goal"),
            p("Lightweight task/context extraction from Notion: read the pages of a Notion database "
              "the user connects, present each as a candidate task (title + optional due date "
              "pulled from the page's structured properties), and let the user import selected ones "
              "as Tasks. Deliberately gets its OWN abstraction — a TaskSourceProvider, distinct from "
              "the chat-oriented MessageSourceProvider (Slack/Teams) — because Notion is a source of "
              "already-structured task-like items, not a noisy message stream, so no LLM "
              "'is-this-an-action-item?' detection gate is needed; structured property extraction "
              "does the work. The user still explicitly imports (approval gate) — nothing is "
              "auto-created."),
            divider(),
            h2("Scope"),
            bullet_list([
                "TaskSourceProvider ABC (backend/app/integrations/task_source_base.py) + SourceTask "
                "dataclass (external_id, title, notes, due) — a read-only external-task source, "
                "parallel to but separate from MessageSourceProvider",
                "NotionTaskSource(TaskSourceProvider) (backend/app/integrations/notion_source.py) "
                "querying the Notion API POST /v1/databases/{id}/query; extracts each page's title "
                "from its title-type property and a due date from the first date-type property "
                "(structured extraction, no LLM)",
                "NotionIntegration model (user_id, access_token, workspace_id, is_active) + "
                "NotionImportItem model (user_id, database_id, page_id, title, notes, due_at, "
                "status pending|imported|dismissed, created_task_id FK)",
                "Alembic migration for notion_integrations + notion_import_items",
                "NotionRepository (integration + import-item repos), schemas, NotionService "
                "(connect/disconnect/scan_database/list_pending/import_item/dismiss) + "
                "NotionNotConnected — the framing is import/dismiss (not detect/confirm) to reflect "
                "the different abstraction",
                "POST /api/v1/notion/connect (Premium), DELETE /api/v1/notion/disconnect, "
                "POST /api/v1/notion/scan (Premium — reads a database, creates pending import items "
                "only, never Tasks), GET /api/v1/notion/pending, "
                "POST /api/v1/notion/items/{id}/import (approval gate → Task, source=notion, due_at "
                "carried over), POST /api/v1/notion/items/{id}/dismiss",
                "notion_client_id/secret/version settings in config.py",
                "Add 'notion' to the TaskSource literal",
                "Tests: 12+ — structured extraction (title + due from Notion property shapes), scan "
                "creates pending items not tasks, import creates a Task source=notion carrying "
                "due_at, dismiss, dedup on page_id, Premium gate (403), cross-user isolation",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No LLM action-item detection — Notion database rows are already discrete task-like "
                "items; the value is structured title/due extraction + user-chosen import, not "
                "sifting chat noise. This is the core reason Notion gets its own abstraction rather "
                "than reusing MessageSourceProvider/ActionItemDetectionService",
                "No real Notion OAuth app — NOTION_CLIENT_ID/SECRET are empty placeholders in .env; "
                "the mobile client does OAuth and POSTs the token to /notion/connect, same pattern "
                "as Slack/Teams/calendar — no server-side OAuth callback here",
                "No writing back to Notion (creating/updating Notion pages) — read-only; the only "
                "approval gate needed is the Task-import one",
                "No arbitrary property mapping / custom-schema config — extract the title property "
                "and the first date property only; richer per-database field mapping is future work",
                "No syncing Notion page edits back into already-imported Tasks — import is a "
                "one-time copy; no ongoing sync",
                "No token encryption beyond how the other integrations store tokens (plain Text) — "
                "same cross-integration deferral (known_issues.md)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/integrations/task_source_base.py (new)",
                "backend/app/integrations/notion_source.py (new)",
                "backend/app/models/notion.py (new)",
                "backend/migrations/versions/*_add_notion_integration.py (new)",
                "backend/app/repositories/notion_repository.py (new)",
                "backend/app/schemas/notion.py (new)",
                "backend/app/services/notion_service.py (new)",
                "backend/app/api/v1/notion.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/app/models/__init__.py (register models)",
                "backend/app/core/config.py (notion settings)",
                "backend/app/schemas/task.py (add 'notion' to TaskSource)",
                "backend/tests/test_notion.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "NotionTaskSource extracts a page's title from its title-type property and a due "
                "date from its first date-type property, for representative Notion API page shapes",
                "POST /api/v1/notion/scan without Premium returns 403",
                "scan creates pending NotionImportItem rows and zero Tasks",
                "POST /api/v1/notion/items/{id}/import creates a Task (source=notion) carrying the "
                "extracted due_at and links created_task_id; a second import is rejected",
                "dismiss sets status=dismissed and creates no Task",
                "scanning the same database twice does not duplicate an item for the same page_id",
                "One user cannot see or import/dismiss another user's Notion items",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_notion.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-006/033 (Task model), TIME-003 (Premium gate), the integration-provider-pattern "
              "established by the calendar/Slack/Teams integrations (this adds a sibling "
              "TaskSourceProvider abstraction)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-052: Siri Shortcuts / App Intents"),
        ),
    },

    {
        "summary": "TIME-052: Siri Shortcuts / App Intents",
        "labels": ["phase-13", "ios"],
        "description": doc(
            h2("Goal"),
            p("Expose core TimeSense actions to Siri and the Shortcuts app via the App Intents "
              "framework (iOS 16+), so users can run them by voice or as Shortcuts. Read-only and "
              "simple-write actions run headless; anything needing UI or approval (replan) opens "
              "the app, preserving the product's approval rules."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Five AppIntents under ios/TimeSense/Intents/: WhatToDoNext (GET /api/v1/now → "
                "spoken best task + usable minutes), LogLunch (POST /api/v1/meals lunch/eaten), "
                "MarkDone (GET /now → PATCH /api/v1/tasks/{bestTaskId} status=done), StartFocus "
                "(GET /now → 'Focus on {task}'), ReplanDay (opens the app — replans require "
                "approval, so it can't run headless)",
                "AppShortcutsProvider exposing each intent with natural Siri phrases "
                "(\\(.applicationName)-prefixed), so they appear in Shortcuts and are Siri-invokable",
                "Intents call the existing APIClient.shared (the one network path); reuse the "
                "existing NowContext/NowTask decodables; define minimal inline request/response "
                "types where needed. No new networking layer",
                "ReplanDay uses openAppWhenRun so the replan is reviewed/approved in-app, never "
                "auto-applied",
                "Wire the new Intents group into the Xcode project via the xcodeproj gem (same "
                "tooling as the widget/insights tickets); build against the now-available iOS "
                "Simulator and boot it to confirm the shortcuts register",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No Siri *voice* end-to-end verification — Siri isn't in the Simulator; voice "
                "invocation is a real-device follow-up. Shortcuts-app registration IS verifiable in "
                "the Simulator and is the acceptance bar here",
                "No true backend round-trip verification — real Firebase Auth isn't configured "
                "(standing placeholder gap across iOS/Android/web), so a headless intent's API call "
                "would 401. Intents are written to attach the token via APIClient and surface an "
                "auth error gracefully; the build + Shortcuts registration are what's verified",
                "No new backend endpoints — reuses /now, /meals, /tasks/{id}. No 'focus session' or "
                "'auto-replan' backend concept is invented (StartFocus just surfaces the best task; "
                "ReplanDay opens the app)",
                "No Google Assistant (that's TIME-053), no widgets/interactive-widget intents "
                "(TIME-044/045 already shipped read-only widgets)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Intents/TimeSenseAppIntents.swift (the 5 intents) (new)",
                "ios/TimeSense/Intents/TimeSenseShortcuts.swift (AppShortcutsProvider) (new)",
                "ios/TimeSense.xcodeproj/project.pbxproj (register the Intents group)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "xcodebuild -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' "
                "succeeds",
                "The five App Intents compile and are exposed via an AppShortcutsProvider with Siri "
                "phrases",
                "Read/write intents call the existing APIClient; ReplanDay opens the app rather "
                "than applying a replan headlessly",
                "Booting a Simulator and installing the app shows the shortcuts available (manual "
                "verification note in the PR)",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-018 (iOS App Shell), TIME-030/031/032 (Now/Capture screens + the /now, /meals, "
              "/tasks endpoints these intents reuse). Requires an iOS Simulator runtime (now "
              "installed)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-053: Google Assistant Integration"),
        ),
    },

    {
        "summary": "TIME-059: iOS Real Apple Signing Configuration",
        "labels": ["ios", "signing"],
        "description": doc(
            h2("Goal"),
            p("Point the iOS project at the real Apple Developer account now that it's available "
              "(Team WB5NV894N5, registered App ID com.aetheranalytics.timesense). Set the "
              "development team and align every bundle identifier + App Group from the placeholder "
              "com.timesense.app to the registered com.aetheranalytics.timesense, so the app and "
              "its widget extension can code-sign and provision against the real account — the "
              "prerequisite for on-device runs and for entitlements like HealthKit (TIME-060)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Set DEVELOPMENT_TEAM = WB5NV894N5 on the TimeSense app + TimeSenseWidgetExtension "
                "targets (CODE_SIGN_STYLE stays Automatic)",
                "Rename PRODUCT_BUNDLE_IDENTIFIER: app com.timesense.app → com.aetheranalytics."
                "timesense; widget com.timesense.app.TimeSenseWidget → com.aetheranalytics."
                "timesense.TimeSenseWidget (both Debug + Release configs)",
                "Rename the shared App Group group.com.timesense.app → group.com.aetheranalytics."
                "timesense in both entitlements files (TimeSense.entitlements, "
                "TimeSenseWidget.entitlements) AND the WidgetSnapshot.appGroupID Swift constant — "
                "all three must match or the widget can't read the app's snapshot",
                "Verify: Simulator build still succeeds; attempt a signed 'Any iOS Device' build "
                "using the App Store Connect API key (from .env) with -allowProvisioningUpdates to "
                "confirm the real account provisions the app + widget (best-effort — see Non-Goals)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No changes to the Android applicationId (com.timesense.app) — that's a separate "
                "Google Play registration, untouched by this iOS-only ticket",
                "No on-device install/run — there's no physical device attached to this "
                "environment; that's the user's step once the project is configured",
                "No guarantee the headless signed-device build fully succeeds — it depends on a "
                "signing certificate being creatable/available in this Mac's keychain, which is "
                "environment state, not project config. If it can't sign here, the project is still "
                "correctly configured for the user to sign from their own Xcode; document the "
                "outcome either way",
                "No Firebase / GoogleService-Info.plist changes (still placeholder); no App Store "
                "Connect upload / TestFlight",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense.xcodeproj/project.pbxproj (DEVELOPMENT_TEAM + 4 bundle-id lines)",
                "ios/TimeSense/TimeSense.entitlements (App Group)",
                "ios/TimeSenseWidget/TimeSenseWidget.entitlements (App Group)",
                "ios/TimeSense/Core/Widgets/WidgetSnapshot.swift (appGroupID constant)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Both targets' PRODUCT_BUNDLE_IDENTIFIER use com.aetheranalytics.timesense[.Widget]",
                "DEVELOPMENT_TEAM = WB5NV894N5 on both targets",
                "The App Group string is identical (group.com.aetheranalytics.timesense) across "
                "both entitlements files and WidgetSnapshot.appGroupID",
                "Simulator build succeeds (xcodebuild -scheme TimeSense -destination 'platform=iOS "
                "Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO)",
                "Signed-device-build attempt is run and its outcome documented in the PR",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO\n"
                "# signed device build (best-effort, App Store Connect API key):\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'generic/platform=iOS' -allowProvisioningUpdates "
                "-authenticationKeyID <id> -authenticationKeyIssuerID <issuer> "
                "-authenticationKeyPath <p8>"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-018 (iOS shell), TIME-044 (widget + App Group), a real Apple Developer account "
              "(now provided in .env: APPLE_TEAM_ID, APPLE_BUNDLE_ID, App Store Connect API key)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-060: iOS HealthKit Sleep/Wake Read Integration"),
        ),
    },

    {
        "summary": "TIME-060: iOS HealthKit Sleep/Wake Read Integration",
        "labels": ["ios", "healthkit"],
        "description": doc(
            h2("Goal"),
            p("Build the iOS-side HealthKit read integration deferred from TIME-042: request "
              "HealthKit authorization for sleep analysis, read the user's most recent sleep/wake "
              "samples, and POST them to the existing POST /api/v1/sleep/events endpoint (which "
              "already gates on health_data consent and triggers a morning replan on a late wake). "
              "Completes the sleep/wake feature's mobile half."),
            divider(),
            h2("Scope"),
            bullet_list([
                "ios/TimeSense/Core/Health/HealthService.swift — wraps HKHealthStore behind an "
                "`#if canImport(HealthKit)` guard (mirrors the AuthService Firebase-stub pattern so "
                "CLI/Simulator builds without the capability still compile): requestAuthorization() "
                "for HKCategoryType sleepAnalysis, readMostRecentWake() computing the latest "
                "wake_time from sleep samples, and syncToBackend() POSTing to /api/v1/sleep/events "
                "via APIClient",
                "HealthKit capability + com.apple.developer.healthkit entitlement on the app target",
                "Info.plist NSHealthShareUsageDescription (read-only; no NSHealthUpdate — TimeSense "
                "only reads sleep)",
                "A minimal Settings hook or onboarding affordance to trigger the auth request "
                "(reuse existing Settings/consent surfaces; do not build a new consent system — the "
                "backend health_data consent already exists)",
                "SleepWakeSyncRequest Codable matching the backend SleepWakeEventIn (wake_time, "
                "sleep_start, source='healthkit')",
                "Verify on the Simulator (HealthKit runs there; inject a sleep sample to exercise "
                "the read path) + build",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No background/scheduled sync (HKObserverQuery + background delivery) — this ticket "
                "does an app-foreground read+sync; background delivery is a follow-up",
                "No writing to HealthKit — read-only sleep analysis",
                "No on-device end-to-end run in this environment (no physical device) — Simulator "
                "verification + a real signed build (enabled by TIME-059) are the bar; the user runs "
                "on a device. Real Health data + the live authorization prompt are inherently "
                "device/Simulator-interactive",
                "No change to the backend — POST /api/v1/sleep/events (TIME-042) already exists and "
                "is unchanged",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Core/Health/HealthService.swift (new)",
                "ios/TimeSense.xcodeproj/project.pbxproj (HealthKit capability/entitlement, register "
                "file)",
                "ios/TimeSense/TimeSense.entitlements (com.apple.developer.healthkit)",
                "ios/TimeSense Info.plist keys (NSHealthShareUsageDescription — via "
                "INFOPLIST_KEY_* build settings, since the project uses GENERATE_INFOPLIST_FILE)",
                "ios/TimeSense/Features/Settings/SettingsView.swift (a 'Connect Apple Health' row)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "HealthService requests read authorization for sleepAnalysis and reads the latest "
                "wake time from returned samples",
                "syncToBackend() POSTs wake_time/sleep_start/source=healthkit to "
                "/api/v1/sleep/events via APIClient",
                "Code compiles behind the HealthKit availability guard; Simulator build succeeds",
                "HealthKit entitlement + NSHealthShareUsageDescription present so a device build "
                "(TIME-059 signing) can provision",
                "Settings exposes a way to trigger Health authorization",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-042 (backend sleep/wake contract + POST /api/v1/sleep/events), TIME-059 (real "
              "Apple signing so the HealthKit entitlement provisions on device), an iOS Simulator "
              "runtime (installed)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-053: Google Assistant Integration"),
        ),
    },

    {
        "summary": "TIME-061: Backend Real Firebase Token Verification",
        "labels": ["backend", "auth"],
        "description": doc(
            h2("Goal"),
            p("Make the FastAPI backend actually verify real Firebase ID tokens using the real "
              "service account now provided in .env (project timesense-eb7ec). init_firebase() "
              "already runs at startup and get_current_user already calls "
              "firebase_admin.auth.verify_id_token — but the service-account credential fails to "
              "parse, so real auth was never actually exercised. Fix the parse so the Admin SDK "
              "initializes against the real project; real client tokens then verify end-to-end "
              "(once a client is configured — see Non-Goals)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Robustly parse FIREBASE_SERVICE_ACCOUNT_JSON in app/core/firebase.py: the .env "
                "stores it single-line with all newlines flattened to literal \\n (pretty-printed "
                "JSON mangled), so plain json.loads() fails and a blanket \\n→newline replace also "
                "fails (real newlines inside the private_key string are invalid strict JSON). The "
                "working parse is json.loads(raw.replace('\\\\n','\\n'), strict=False) — verified to "
                "yield a valid service account with a well-formed PEM private_key",
                "Extract a `_load_service_account(raw) -> dict | None` helper: try compact json.loads "
                "first (for correctly-stored compact JSON), fall back to the replace+strict=False "
                "form, return None on empty/unparseable so the existing ADC/projectId fallback still "
                "applies; log which path was used",
                "Confirmed locally: with this parse, credentials.Certificate(sa) + "
                "firebase_admin.initialize_app(cred) succeed for project timesense-eb7ec (no code "
                "change needed to security.py — it already calls verify_id_token)",
                "Unit tests for _load_service_account: compact JSON parses; a fabricated "
                "pretty-printed-then-flattened service-account string parses (using a FAKE key, "
                "never the real one); empty string returns None",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No client-side Firebase config — the .env has only the backend service account. "
                "Real end-to-end sign-in additionally needs per-app client config NOT in .env: iOS "
                "GoogleService-Info.plist, Android google-services.json, and web "
                "NEXT_PUBLIC_FIREBASE_API_KEY/APP_ID/AUTH_DOMAIN, each downloaded/registered in the "
                "Firebase console for project timesense-eb7ec. Those are separate follow-ups",
                "No change to the test suite's auth mocking — tests patch verify_id_token and don't "
                "run the app lifespan, so they neither need nor exercise real init; this ticket "
                "keeps them green",
                "No live token round-trip test — there's no real client token to verify here, and "
                "verify_id_token requires network to Google's public keys; the parse + successful "
                "SDK init is the verifiable bar",
                "No secret committed — the real service account stays only in .env (gitignored)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/core/firebase.py (robust _load_service_account parse)",
                "backend/tests/test_firebase_init.py (new — parse helper unit tests)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "_load_service_account parses both compact JSON and the flattened-literal-\\n form; "
                "returns None for empty",
                "With the real .env value, init_firebase() initializes the Admin SDK for "
                "timesense-eb7ec without the previous parse warning (verified out-of-band, not in "
                "the committed test which uses a fake key)",
                "Full backend test suite still passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_firebase_init.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-002-era auth/security foundation (get_current_user, init_firebase), a real "
              "Firebase service account (now in .env: FIREBASE_PROJECT_ID=timesense-eb7ec, "
              "FIREBASE_SERVICE_ACCOUNT_JSON)."),
            divider(),
            h2("Next Ticket"),
            p("Client Firebase config (iOS GoogleService-Info.plist / Android google-services.json / "
              "web apiKey) — separate, needs console downloads."),
        ),
    },

    {
        "summary": "TIME-053: Google Assistant Integration",
        "labels": ["phase-13", "backend", "integration"],
        "description": doc(
            h2("Goal"),
            p("Expose the same core TimeSense voice actions as the iOS App Intents (TIME-052) to "
              "Google Assistant, via a backend Dialogflow fulfillment webhook. A Dialogflow agent "
              "(configured out-of-band) maps spoken phrases to intents and calls the webhook; the "
              "webhook dispatches each intent to the matching TimeSense action and returns spoken "
              "fulfillment text. Backend-only, mirroring the ticket's stated file "
              "backend/app/integrations/google_assistant.py."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/app/integrations/google_assistant.py — parse a Dialogflow ES WebhookRequest "
                "(queryResult.intent.displayName), a GoogleAssistantService that dispatches 5 "
                "intents to actions, and a fulfillment_response(text) building the Dialogflow "
                "WebhookResponse ({fulfillmentText, fulfillmentMessages})",
                "Five intents mirroring TIME-052: WhatToDoNext (best task + usable minutes), "
                "LogLunch (log lunch eaten via MealRepository), StartFocus (best task focus), "
                "MarkDone (mark the best task done via TaskRepository), ReplanDay (spoken 'open the "
                "app to approve' — replans require in-app approval, never headless)",
                "Best-task selection reuses the same logic as GET /now (TaskRepository +"
                " UsableTimeService + TaskScorer)",
                "POST /api/v1/assistant/webhook — the fulfillment endpoint, gated on the existing "
                "Firebase CurrentUser (representing the Actions-on-Google account-linked identity); "
                "returns the Dialogflow fulfillment JSON. Intent name matching is case/space-"
                "insensitive",
                "Register the router; tests covering each intent's fulfillment text + side effects "
                "(lunch logged, best task marked done), unknown-intent fallback, and the "
                "no-tasks-to-do case",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No Dialogflow agent / Actions-on-Google project setup — that's console "
                "configuration done out-of-band; and note Google shut down conversational Actions "
                "on Google Assistant in June 2023, so this is the Dialogflow-webhook contract "
                "(request/response shapes + intent→action mapping), verifiable by unit tests, not a "
                "live end-to-end Assistant call",
                "No account-linking / OAuth implementation — the webhook is gated on the existing "
                "Firebase token as the account-linked identity stand-in; wiring real Actions-on-"
                "Google account linking (which would supply that token) is out of scope",
                "No new backend actions invented — reuses /now best-task logic, MealRepository, "
                "TaskRepository. ReplanDay does not headlessly replan (approval rule)",
                "No Android App Actions / shortcuts.xml — the on-device shortcut surface is the iOS "
                "App Intents work (TIME-052); this ticket is the Assistant/Dialogflow backend, per "
                "the ticket's stated file path",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/integrations/google_assistant.py (new)",
                "backend/app/api/v1/assistant.py (new)",
                "backend/app/api/v1/__init__.py (register router)",
                "backend/tests/test_google_assistant.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /api/v1/assistant/webhook with a Dialogflow payload for each of the 5 intents "
                "returns fulfillmentText and the correct side effect (LogLunch logs a lunch meal; "
                "MarkDone sets the best task's status to done)",
                "WhatToDoNext with no active tasks returns an 'all caught up' style message",
                "An unknown intent returns a graceful fallback fulfillment (no 500)",
                "The webhook without auth returns 401",
                "All tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_google_assistant.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-030/031 (Now best-task logic, /now), TIME-040 (meal logging), TIME-006/033 "
              "(Task model), TIME-002 (auth). Parallels TIME-052 (same five actions, iOS side)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-054: Notion Integration (or next Phase 13 item)."),
        ),
    },

    {
        "summary": "TIME-062: Client Firebase Config (iOS + Android)",
        "labels": ["ios", "android", "auth"],
        "description": doc(
            h2("Goal"),
            p("Wire the real Firebase project (timesense-eb7ec) into the iOS and Android clients so "
              "they can actually sign in against the now-real backend (TIME-061). The app auth code "
              "already exists behind `#if canImport(FirebaseAuth)` (iOS) / Firebase deps (Android); "
              "this ticket adds the SDK linkage + the per-app config the Firebase console generates."),
            divider(),
            h2("Scope"),
            bullet_list([
                "iOS: add the firebase-ios-sdk Swift Package (pinned to 11.x — Firebase 12.x needs "
                "Swift tools 6.1, newer than this Xcode 16.0 / Swift 6.0) and link FirebaseAuth + "
                "FirebaseCore to the TimeSense target; also add the GoogleSignIn-iOS package (8.x) "
                "since AuthService uses GoogleSignIn for Google sign-in",
                "iOS: add GoogleService-Info.plist to the app target (gitignored — stays local, not "
                "committed)",
                "Android: replace the placeholder app/google-services.json with the real one "
                "(project timesense-eb7ec, package com.timesense.app) — the com.google.gms.google-"
                "services plugin + firebase-auth deps are already wired",
                "Commit the reproducible bits: project.pbxproj (package refs + product links + plist "
                "file ref) and Package.resolved (pins Firebase 11.15.0 et al.); add depth-agnostic "
                ".gitignore rules for xcuserdata/ and .swiftpm/",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Web client config — pending the user's web apiKey/appId; separate follow-up "
                "(web/.env.local)",
                "No sign-in provider enablement in the Firebase console (Apple/Google/email) — that "
                "console toggle is the user's step",
                "No on-device run — verified on the Simulator (build + launch); real interactive "
                "sign-in needs a device/console providers",
                "GoogleService-Info.plist is NOT committed (gitignored, per repo convention) — each "
                "dev supplies their own from the console",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense.xcodeproj/project.pbxproj (SPM package refs + product links + plist ref)",
                "ios/TimeSense.xcodeproj/.../swiftpm/Package.resolved (version pins)",
                "android/app/google-services.json (real config)",
                ".gitignore (xcuserdata/ + .swiftpm/)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "iOS Simulator build succeeds with FirebaseAuth/FirebaseCore/GoogleSignIn linked "
                "(the real `#if canImport(FirebaseAuth)` AuthService compiles)",
                "iOS app launches on the Simulator with FirebaseApp.configure() running against the "
                "real plist (no crash)",
                "android/app/google-services.json is the real timesense-eb7ec config",
                "No Xcode user-data / temp scripts / the plist itself get committed",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild -resolvePackageDependencies -project ios/TimeSense.xcodeproj -scheme TimeSense\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-061 (backend real Firebase verification), TIME-059 (iOS bundle id "
              "com.aetheranalytics.timesense matching the registered iOS app), a real Firebase "
              "project (timesense-eb7ec) with iOS/Android apps registered by the user."),
            divider(),
            h2("Next Ticket"),
            p("Web Firebase config (web/.env.local) once the web apiKey/appId are provided."),
        ),
    },

    {
        "summary": "TIME-063: Fix Alembic migration ordering (tasks before recommendation_feedback)",
        "labels": ["backend", "bug", "migrations"],
        "description": doc(
            h2("Goal"),
            p("Fix a migration-ordering bug that breaks any fresh Postgres `alembic upgrade head`: "
              "the recommendation_feedback migration has a FK to tasks.id, but its migration "
              "(g7h8i9j0k1l2) and the tasks migration (a1b2c3d4e5f7) are *parallel sibling branches* "
              "off the same parent (f6a7b8c9d0e1). Alembic can linearize the siblings with feedback "
              "before tasks, failing with `relation \"tasks\" does not exist`. Discovered while "
              "bringing up a real local Postgres for the app; masked from the test suite because "
              "tests build the schema from models via create_all, not migrations."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Repoint g7h8i9j0k1l2 (add_recommendation_feedback) down_revision from f6a7b8c9d0e1 "
                "to a1b2c3d4e5f7 (tasks), so tasks is guaranteed to exist before the FK is added",
                "Update the merge migration e55970716568's down_revision tuple to drop a1b2c3d4e5f7 "
                "(no longer a head — g7h8i9j0k1l2 now descends from it): "
                "('a7b8c9d0e1f2','b8c9d0e1f2a3','g7h8i9j0k1l2')",
                "Verify a fresh Postgres `alembic upgrade head` completes end-to-end and reaches the "
                "single head p6q7r8s9t0u1",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No schema/model changes — only migration dependency pointers",
                "No change to the test suite (it uses create_all; unaffected). Safe because no DB "
                "ever successfully migrated from scratch in the old order, so there's no "
                "already-migrated DB whose alembic_version graph could be disrupted",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/migrations/versions/g7h8i9j0k1l2_add_recommendation_feedback.py (down_revision)",
                "backend/migrations/versions/e55970716568_merge_parallel_migration_heads.py (merge tuple)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "`alembic heads` shows the single head p6q7r8s9t0u1",
                "`alembic upgrade head` on an empty Postgres DB completes with no "
                "'relation tasks does not exist' error",
                "Full backend test suite still passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic heads\n"
                "# against a fresh DB:\n"
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("The TIME-030/033/036-era migrations + the earlier head-merge (e55970716568) that "
              "introduced the sibling branches."),
            divider(),
            h2("Next Ticket"),
            p("Web Firebase config (web/.env.local)."),
        ),
    },

    {
        "summary": "TIME-064: Load .env from repo root regardless of working directory",
        "labels": ["backend", "config"],
        "description": doc(
            h2("Goal"),
            p("Make the backend load the repo-root .env no matter what directory it's launched from. "
              "config.py uses env_file='.env' (relative to CWD), so the documented "
              "`cd backend && uvicorn app.main:app` looks for backend/.env, which doesn't exist — "
              "the real .env is at the repo root. That silently loaded NO env (falling back to "
              "defaults), which broke real Firebase auth at runtime (empty project id → "
              "'A project ID is required'). Discovered while running the full stack locally."),
            divider(),
            h2("Scope"),
            bullet_list([
                "config.py: resolve env_file to an absolute repo-root .env path computed from "
                "__file__ (Path(__file__).resolve().parents[3] / '.env'), so it's found from any CWD",
                "Keep a CWD-relative '.env' in the env_file tuple as an override for anyone who "
                "keeps a local backend/.env",
                "Remove the temporary backend/.env symlink workaround added during local bring-up",
                "Verify the backend loads real settings (firebase_project_id, service account) when "
                "started from backend/, and the full test suite still passes",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No change to how Docker injects env (it sets env vars directly; a missing absolute "
                "env_file path in the container is simply ignored, and os.environ still wins)",
                "No secrets committed — .env stays gitignored",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/core/config.py (env_file path resolution)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "From backend/, `python -c 'from app.core.config import settings; "
                "print(settings.firebase_project_id)'` prints the real project id (timesense-eb7ec) "
                "with no symlink present",
                "Backend boots and verifies real Firebase tokens when run via `cd backend && uvicorn`",
                "Full test suite still passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && python -c \"from app.core.config import settings; "
                "print(settings.firebase_project_id)\"\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-061 (real Firebase backend verification, which this makes actually load at "
              "runtime)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-065: Sync DB user role from the Firebase token claim."),
        ),
    },

    {
        "summary": "TIME-065: Sync DB user role from the Firebase token claim",
        "labels": ["backend", "auth"],
        "description": doc(
            h2("Goal"),
            p("Make the Firebase custom-claim role the single source of truth for authorization. "
              "Today the backend admin endpoints gate on the token claim (require_admin) while "
              "GET /users/me returns the DB user.role, and the web dashboard gates on that — so "
              "they're set independently and granting admin took two steps (set claim AND update "
              "the DB row). Sync the DB role from the token claim so one action (the claim) is "
              "enough and /users/me reflects it."),
            divider(),
            h2("Scope"),
            bullet_list([
                "get_or_create_user gains an optional role param; when provided and it differs from "
                "the stored role, update + persist it (the token claim is authoritative — a cache "
                "refresh, including downgrades if the claim is removed)",
                "GET /users/me passes current_user.role into get_or_create_user so the DB role "
                "mirrors the claim on every call the web makes",
                "Tests: a user whose token claim is admin gets role=admin back from /users/me even "
                "if the DB row was created as 'user'; a plain user stays 'user'; removing the claim "
                "downgrades",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No change to require_admin (still reads the token claim — now the DB just mirrors "
                "it)",
                "No admin-management UI/endpoint for granting roles (claims are still set out-of-"
                "band via the Admin SDK); this only removes the DB/claim divergence",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/user_service.py (get_or_create_user role sync)",
                "backend/app/repositories/user_repository.py (if role update helper needed)",
                "backend/app/api/v1/users.py (pass token role into get_or_create_user in /me)",
                "backend/tests/test_users.py or test_auth.py (role-sync tests)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /users/me returns role matching the token claim (admin claim → role=admin), "
                "even for a freshly-created DB row",
                "A user with no admin claim returns role=user",
                "Removing the claim and calling /users/me downgrades the DB role to user",
                "require_admin behavior unchanged; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_users.py -q\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-061 (real token verification), the existing require_admin / get_current_user "
              "and users/me endpoint."),
            divider(),
            h2("Next Ticket"),
            p("Web Firebase config follow-ups / next feature ticket."),
        ),
    },

    {
        "summary": "TIME-054: Error Monitoring and Analytics (backend)",
        "labels": ["phase-14", "backend", "observability"],
        "description": doc(
            h2("Goal"),
            p("Add backend error monitoring (Sentry-optional) and a privacy-respecting analytics "
              "event pipeline, so production errors are visible and key product events are captured "
              "— gated on the existing 'analytics' consent. First ticket of Phase 14 (Beta "
              "Hardening & Launch Readiness). Client-side (iOS/Android) analytics is a follow-up."),
            divider(),
            h2("Scope"),
            bullet_list([
                "app/core/monitoring.py — init_monitoring() initializes Sentry only when SENTRY_DSN "
                "is set AND sentry-sdk is importable, else a clean no-op (same graceful pattern as "
                "Firebase/LLM); capture_exception(exc, context) delegates or no-ops. Wired into the "
                "lifespan startup and the existing error handlers (add_error_handlers) so unhandled "
                "500s are captured. send_default_pii=False",
                "config: sentry_dsn (default ''); add sentry-sdk to requirements (optional import "
                "so tests run without it)",
                "AnalyticsEvent model (user_id nullable FK, event_name, properties JSON, created_at)"
                " + Alembic migration",
                "AnalyticsService.track(event_name, user_id=None, properties=None): for a "
                "user-attributed event, record ONLY if that user granted the 'analytics' consent "
                "(ConsentRepository.get_effective); system events (user_id None) record without a "
                "consent check. Returns None when skipped",
                "Emit a representative key event: 'task_captured' from POST /api/v1/capture after the "
                "task is created",
                "GET /api/v1/admin/analytics — admin-gated event counts grouped by event_name "
                "(ties into the admin dashboard)",
                "Tests: monitoring no-op without DSN + safe capture; analytics records with consent, "
                "skips without, records system events; capture emits task_captured (consented); "
                "admin analytics counts + 403 without admin",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No client-side analytics (iOS Analytics.swift / Android analytics/) — deferred to a "
                "follow-up ticket; this establishes the backend pipeline + event schema first",
                "No real Sentry project/DSN wired (SENTRY_DSN empty by default → no-op); no "
                "performance tracing (traces_sample_rate=0)",
                "No PII in events — properties are product signals, not personal data; "
                "send_default_pii=False. No raw request bodies captured",
                "No analytics on every endpoint — one representative emission (task_captured) plus "
                "the reusable service; broader instrumentation is incremental follow-up",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/core/monitoring.py (new)",
                "backend/app/core/errors.py (capture 500s), backend/app/main.py (init in lifespan)",
                "backend/app/core/config.py (sentry_dsn), backend/requirements.txt (sentry-sdk)",
                "backend/app/models/analytics_event.py (new), migration, app/models/__init__.py",
                "backend/app/services/analytics_service.py (new), app/repositories/"
                "analytics_repository.py (new)",
                "backend/app/api/v1/capture.py (emit event), app/api/v1/admin.py (+ schemas) "
                "(analytics endpoint)",
                "backend/tests/test_monitoring_analytics.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "init_monitoring() is a no-op with no DSN (is_enabled() False); capture_exception is "
                "safe to call when disabled",
                "AnalyticsService.track records a user event only when the user granted 'analytics' "
                "consent; skips otherwise; records system (user_id None) events",
                "POST /api/v1/capture emits a task_captured event for a consented user",
                "GET /api/v1/admin/analytics returns per-event counts (admin only; 403 otherwise)",
                "Full backend test suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head\n"
                "cd backend && pytest tests/test_monitoring_analytics.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-002 (auth/admin), the existing consent system (analytics consent type), "
              "TIME-031 (capture endpoint), the admin dashboard (TIME-048)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-055: Privacy Review and Data Export (or client analytics follow-up)."),
        ),
    },

    {
        "summary": "TIME-055: Privacy Review and Data Export",
        "labels": ["phase-14", "backend", "privacy"],
        "description": doc(
            h2("Goal"),
            p("Self-service privacy: let an authenticated user export all of their data as a "
              "portable JSON bundle and permanently delete their account and all associated data. "
              "GDPR/CCPA-style data portability + erasure. Backend endpoints under "
              "backend/app/api/v1/privacy.py."),
            divider(),
            h2("Scope"),
            bullet_list([
                "PrivacyService.export_data(user_id) — gathers the user's rows across every "
                "user-owned table into a JSON bundle (user + profile/preferences/onboarding, tasks, "
                "meals, sleep, commute, routines, consent, subscriptions, notifications, "
                "recommendation feedback, insights, all integrations, analytics, referrals). OAuth "
                "tokens (access_token/refresh_token) are redacted",
                "PrivacyService.delete_account(user_id) — deletes the user row (DB-level ON DELETE "
                "CASCADE erases all user_id-owned rows — self-maintaining), explicitly purges "
                "analytics_events (SET NULL would only anonymize), and deletes the Firebase Auth "
                "user best-effort",
                "GET /api/v1/privacy/export (authed) → the JSON bundle",
                "DELETE /api/v1/privacy/account?confirm=true (authed) → 204; requires confirm=true "
                "so a stray call can't wipe data; irreversible",
                "Enable SQLite foreign-key enforcement in the test conftest (PRAGMA foreign_keys=ON) "
                "so cascade deletion is exercised like Postgres — verified the full suite still "
                "passes with it on",
                "Tests: export includes data + redacts tokens; delete erases user + cascades; "
                "requires confirm; only affects own data; both require auth",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No per-consent-type revocation cleanup (e.g. revoking health_data auto-purging "
                "sleep data) — noted in the consent ticket; a separate follow-up. This ticket does "
                "full-account export + deletion",
                "No admin-initiated deletion/export of other users — self-service only (the "
                "authenticated user's own data)",
                "No async/emailed export job — synchronous JSON response (fine at current data "
                "volumes)",
                "No soft-delete/grace-period/undo — deletion is immediate and irreversible (guarded "
                "by confirm=true)",
                "No new tables/migrations — operates over existing schema",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/privacy_service.py (new)",
                "backend/app/api/v1/privacy.py (new), app/api/v1/__init__.py (register)",
                "backend/tests/conftest.py (SQLite FK enforcement)",
                "backend/tests/test_privacy.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/privacy/export returns the user's data with OAuth tokens redacted",
                "DELETE /api/v1/privacy/account?confirm=true erases the user and cascades to all "
                "owned rows; without confirm returns 400 and deletes nothing",
                "Deletion affects only the caller's data, not other users'",
                "Both endpoints require authentication (401 otherwise)",
                "Full backend test suite passes with FK enforcement enabled",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_privacy.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-002 (auth), the full data model (all user-owned tables), TIME-061 (real Firebase "
              "so the Auth user can be deleted). Starts alongside TIME-054 in Phase 14."),
            divider(),
            h2("Next Ticket"),
            p("TIME-056: Security Review and Hardening."),
        ),
    },

    {
        "summary": "TIME-056: Security Review and Hardening",
        "labels": ["phase-14", "backend", "security"],
        "description": doc(
            h2("Goal"),
            p("Security review of auth, token storage, admin access, rate limiting, and webhook "
              "security, and implement the top hardening findings: (1) encrypt integration OAuth "
              "tokens at rest, (2) response security headers, (3) rate limiting on abuse-prone "
              "endpoints. Audits confirm existing controls stay documented."),
            divider(),
            h2("Audit findings (already secure — documented, no change)"),
            bullet_list([
                "Auth: get_current_user verifies real Firebase ID tokens (check_revoked=True); "
                "require_admin gates on the token claim; /users/me mirrors it to the DB (TIME-065)",
                "Stripe webhook: already verifies the signature (stripe.Webhook.construct_event), "
                "400 on bad signature, 503 when unconfigured — no change needed",
                "Admin: all /admin routes require the AdminUser dependency (403 otherwise)",
                "Privacy deletion requires confirm=true; export redacts tokens (TIME-055)",
            ]),
            divider(),
            h2("Scope (new hardening)"),
            bullet_list([
                "app/core/crypto.py — Fernet-based encrypt_token/decrypt_token + an EncryptedString "
                "SQLAlchemy TypeDecorator (impl=Text, so NO migration). Key from settings "
                "token_encryption_key, or derived deterministically from secret_key when unset "
                "(works in dev, overridable in prod). decrypt tolerates legacy plaintext (returns "
                "as-is on InvalidToken) for forward-safety",
                "Apply EncryptedString to the access_token/refresh_token columns of "
                "CalendarIntegration, SlackIntegration, TeamsIntegration, NotionIntegration — "
                "transparent encrypt-on-write / decrypt-on-read; closes the logged 'tokens stored "
                "as plain Text' known issue",
                "SecurityHeadersMiddleware — X-Content-Type-Options: nosniff, X-Frame-Options: DENY, "
                "Referrer-Policy: no-referrer, X-XSS-Protection off, and HSTS in production",
                "A lightweight in-process RateLimiter dependency (fixed-window per client+route); "
                "applied to abuse-prone endpoints (POST /capture, DELETE /privacy/account). Returns "
                "429 with Retry-After when exceeded. Noted: single-instance in-memory (Redis for "
                "multi-instance is a follow-up)",
                "config: token_encryption_key (default ''), rate-limit knobs",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No distributed (Redis) rate limiting — in-process fixed-window is enough for the "
                "current single-instance deploy; Redis-backed is a follow-up",
                "No re-encryption migration of existing tokens (none stored yet; EncryptedString "
                "tolerates any legacy plaintext by returning it as-is)",
                "No changes to the Stripe/Apple/Google webhook handlers beyond documenting that "
                "Stripe already verifies signatures",
                "No secret rotation tooling / KMS integration — the key comes from settings",
                "No new auth mechanism; require_admin/token verification unchanged",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/core/crypto.py (new), app/core/config.py (token_encryption_key + rate "
                "knobs)",
                "backend/app/core/middleware.py (new — security headers), app/main.py (add "
                "middleware)",
                "backend/app/core/rate_limit.py (new — RateLimiter dependency)",
                "backend/app/models/calendar.py, slack.py, teams.py, notion.py (EncryptedString)",
                "backend/app/api/v1/capture.py, privacy.py (apply rate limiter)",
                "backend/tests/test_security.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "encrypt_token/decrypt_token round-trips; ciphertext != plaintext; decrypt tolerates "
                "plaintext",
                "An integration token written via the service is stored as ciphertext at rest (raw "
                "column select) but reads back as plaintext through the ORM",
                "Every response carries the security headers",
                "Exceeding the rate limit on a limited endpoint returns 429",
                "Full backend test suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_security.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-015-era calendar + TIME-049/050/051 integrations (token columns), TIME-002 "
              "(auth), the cryptography lib (already present via python-jose[cryptography])."),
            divider(),
            h2("Next Ticket"),
            p("TIME-057: App Store and Play Store Prep."),
        ),
    },

    {
        "summary": "TIME-057: App Store and Play Store Prep",
        "labels": ["phase-14", "launch", "docs"],
        "description": doc(
            h2("Goal"),
            p("Produce the store-submission prep for both stores: a real privacy policy, App Store + "
              "Play Store listing metadata, the App Privacy / Data Safety label answers (grounded in "
              "what the app actually collects), App Store review notes, and a required-assets "
              "checklist. Documentation deliverable — the actual screenshots/binaries/console entry "
              "are the user's step."),
            divider(),
            h2("Scope"),
            bullet_list([
                "docs/launch/privacy_policy.md — a complete privacy policy reflecting real practices: "
                "Firebase auth; data collected (tasks/meals/sleep/commute/routines); consent types "
                "(audio_storage, audio_training, location_tracking, health_data, calendar_details, "
                "analytics); integrations (Google Calendar/Slack/Teams/Notion, tokens encrypted at "
                "rest); LLM/OpenAI processing of capture text; Stripe/StoreKit/Play billing; raw "
                "audio explicit opt-in; data export + deletion (TIME-055); retention; children; "
                "contact",
                "docs/launch/app_store_listing.md — iOS name/subtitle/promo text/description/keywords/"
                "what's-new + App Store review notes (demo account, how to reach premium, integration "
                "test steps) + App Privacy 'nutrition label' answers per data type",
                "docs/launch/play_store_listing.md — Android title/short+full description/category + "
                "Play Data Safety form answers (collected/shared/encrypted-in-transit-and-at-rest/"
                "deletion) + content rating notes",
                "docs/launch/store_assets_checklist.md — the assets the USER must produce: icon "
                "sizes, screenshot dimensions + counts per device class, feature graphic, preview "
                "video (optional), plus submission prerequisites",
                "docs/launch/README.md — index + submission runbook",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No actual screenshots / app icons / feature graphics / preview videos — those are "
                "design assets the user produces (the checklist specifies exact sizes/counts)",
                "No App Store Connect / Play Console data entry, no binary upload/submission — this "
                "is the copy + answers the user pastes in",
                "No legal review — the privacy policy is a thorough, accurate draft grounded in the "
                "codebase; the user should have it reviewed before publishing",
                "No code changes",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "docs/launch/privacy_policy.md, app_store_listing.md, play_store_listing.md, "
                "store_assets_checklist.md, README.md (all new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Privacy policy covers every consent type, integration, the LLM/OpenAI processing, "
                "billing, raw-audio opt-in, and the export/deletion rights — consistent with the "
                "code",
                "Both store listings have complete metadata within store character limits",
                "App Privacy + Play Data Safety answers are filled per data type and match the "
                "privacy policy",
                "Assets checklist lists exact required sizes/counts",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "# docs-only; no tests. Review the 5 files under docs/launch/ for completeness and\n"
                "# consistency with the codebase's actual data practices."
            ),
            divider(),
            h2("Dependencies"),
            p("The full product (all features + data practices), TIME-055 (export/deletion rights in "
              "the policy), TIME-056 (encryption-at-rest claim), the product brief (pricing/tagline)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-066: Fix iOS missing color assets (invisible UI)",
        "labels": ["ios", "bug", "ui"],
        "description": doc(
            h2("Goal"),
            p("Fix an iOS bug where almost the entire UI was invisible. DesignTokens.Color reference "
              "named asset-catalog colors (Color(\"TextPrimary\"), \"Surface\", \"Background\", "
              "\"Accent\", etc.), but the project had NO asset catalog at all — so every token color "
              "resolved to an invisible fallback. Only hardcoded-black elements (the Apple sign-in "
              "button) were visible; the brand header, Google button, 'Continue with Email' link, "
              "and effectively all text/surfaces across the app rendered white-on-white."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Create ios/TimeSense/Assets.xcassets with colorsets for every DesignTokens color "
                "(AccentColor, Background, Surface, TextPrimary, TextSecondary, Destructive, "
                "Success), each with light + dark (luminosity) variants",
                "Add an empty AppIcon.appiconset (actool requires the app-icon set named in "
                "ASSETCATALOG_COMPILER_APPICON_NAME)",
                "Register Assets.xcassets in the TimeSense target's resources (via the xcodeproj gem)",
                "Verify: Simulator build succeeds and the sign-in screen renders the full UI (brand "
                "header + all sign-in options visible)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No real app icon artwork (empty AppIcon set; the icon is a launch-assets task — see "
                "docs/launch/store_assets_checklist.md)",
                "No redesign — colors match the intended neutral/indigo palette the tokens implied",
                "No changes to the widget extension's separate WidgetColors",
            ]),
            divider(),
            h2("Root cause / lesson"),
            p("Earlier iOS 'verification' (BUILD SUCCEEDED + app launches to its sign-in screen) did "
              "not catch this because the one visible element (the black Apple button) looked "
              "plausible in a screenshot. Visual verification must confirm the intended UI renders, "
              "not just that the app launches. Recorded in known_issues.md."),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Assets.xcassets/** (new — 7 colorsets + AppIcon + root Contents.json)",
                "ios/TimeSense.xcodeproj/project.pbxproj (register the catalog)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "All 7 named DesignTokens colors exist as colorsets with light + dark values",
                "Simulator build succeeds (was failing on the missing AppIcon once a catalog was added)",
                "The sign-in screen shows the brand header, Apple, Google, and Continue-with-Email "
                "(verified by screenshot)",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO\n"
                "# then simctl install/launch + screenshot the sign-in screen"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-018 (iOS shell + DesignTokens), the now-available iOS Simulator, TIME-062 "
              "(Firebase-linked build)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-067: Fix day-view task visibility (Today 404 + Now ignores captured tasks)",
        "labels": ["ios", "backend", "bug"],
        "description": doc(
            h2("Goal"),
            p("Two bugs found while using the app: the Today tab shows 'Couldn't load today — 404', "
              "and a task added via Capture never appears on the Now tab. Fix both."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Today 404 (iOS): APIClient built the URL with URL.appending(path:), which "
                "percent-encodes the WHOLE string as one path component — so any '?query' (Today "
                "sends '?date=YYYY-MM-DD') became '%3Fdate=...', producing a non-existent path → 404. "
                "This broke EVERY query-param endpoint (insights history, admin search, etc.), not "
                "just Today. Fix: build the URL as baseURL.absoluteString + path so the query "
                "survives.",
                "Now ignores captured tasks (backend): GET /now's candidate set was only "
                "scheduled-today + overdue tasks. A freshly captured task has no scheduled_start and "
                "no due_at, so it was neither → never surfaced. Fix: also include unscheduled pending "
                "tasks as 'do it whenever' candidates.",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No change to the timeline/today endpoint itself (it correctly returns scheduled "
                "tasks; the 404 was purely the client URL bug)",
                "No new scheduling UI — unscheduled tasks simply become eligible for Now",
                "No iOS unit-test harness added (verified by build + the backend Now test); the "
                "APIClient fix is a one-line URL-construction change",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Core/API/APIClient.swift (URL construction preserves query)",
                "backend/app/api/v1/now.py (include unscheduled pending tasks)",
                "backend/tests/test_now.py (unscheduled-task test)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /api/v1/now returns a just-captured (unscheduled, no-due) pending task as "
                "best_task",
                "iOS query-param requests (e.g. /timeline/today?date=...) hit the right route (no "
                "404 from encoding)",
                "iOS build succeeds; backend suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py -v\n"
                "cd backend && pytest -q\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-030/031 (capture + Now/Today), TIME-066 (visible UI so the screens can be used)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-068: Refresh Now/Today when returning to the tab (+ pull-to-refresh)",
        "labels": ["ios", "bug", "ui"],
        "description": doc(
            h2("Goal"),
            p("The Now and Today screens didn't update after capturing a task: they load once via "
              "SwiftUI `.task { }`, but TabView keeps tab views mounted, so `.task` doesn't re-run "
              "when you switch back to the tab. Reload on tab re-entry and add pull-to-refresh."),
            divider(),
            h2("Scope"),
            bullet_list([
                "NowView + TodayView: add `.onChange(of: appState.selectedTab)` to reload the "
                "view-model whenever the user returns to that tab (appState.selectedTab drives the "
                "TabView selection) — so a task captured on the Capture tab shows on Now/Today on "
                "return",
                "Add `.refreshable { load() }` to both loaded scroll views for manual pull-to-refresh",
                "Keep the initial `.task { load() }` for first appearance",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No push/live updates or a shared task-changed event bus — reload-on-tab-entry + "
                "pull-to-refresh is sufficient and simple",
                "No auto-switch to Now after a capture (leaves the user on Capture to add more)",
                "No backend changes",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Features/Now/NowView.swift",
                "ios/TimeSense/Features/Today/TodayView.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Capturing a task then switching to Now shows it as best_task without a manual reload",
                "Pull-to-refresh reloads Now and Today",
                "iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-067 (Now now includes captured tasks server-side), TIME-066 (visible UI), "
              "TIME-030/031 (Now/Today/Capture screens)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-069: Dual-stack dev server launcher (fix iOS Simulator localhost)",
        "labels": ["backend", "devx", "docs"],
        "description": doc(
            h2("Goal"),
            p("The documented `uvicorn app.main:app` binds IPv4 (127.0.0.1) only, but macOS resolves "
              "`localhost` to IPv6 `::1` first — so the iOS Simulator (which calls localhost:8000) "
              "fails to connect (nw_endpoint_flow_failed [::1.8000]). Add a committed dev launcher "
              "that binds a DUAL-STACK socket so both `::1` and `127.0.0.1` work, and document it."),
            divider(),
            h2("Scope"),
            bullet_list([
                "backend/run_dev.py — creates an AF_INET6 socket with IPV6_V6ONLY=0 (accepts IPv4-"
                "mapped too), binds ::, and serves app.main:app on it via uvicorn.Server. PORT env "
                "override; clear docstring explaining the IPv4/IPv6 localhost issue",
                "Document it: note in CLAUDE.md's Commands (use `python run_dev.py` for Simulator "
                "dev, or `uvicorn --host ::`) and a one-liner in the backend area",
                "Verify both loopbacks return 200 (curl [::1]:8000 and 127.0.0.1:8000)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No hot-reload in run_dev.py (uvicorn reload + a pre-bound socket don't compose "
                "cleanly; use plain `uvicorn --reload` for IPv4-only reload workflows)",
                "No change to the Dockerfile / production serving (containers bind 0.0.0.0 and sit "
                "behind a proxy; this is a local-dev convenience only)",
                "No app-side change (the app correctly uses localhost; the server just needs to "
                "listen on both families)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/run_dev.py (new)",
                "CLAUDE.md (Commands note)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "`cd backend && python run_dev.py` serves the app on both ::1:8000 and 127.0.0.1:8000 "
                "(both return 200)",
                "CLAUDE.md documents the Simulator-friendly dev command",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && python run_dev.py &\n"
                "curl -s -o /dev/null -w '%{http_code}' http://[::1]:8000/api/v1/health\n"
                "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/health"
            ),
            divider(),
            h2("Dependencies"),
            p("The iOS Simulator dev loop (TIME-062/066/067/068), the FastAPI app entrypoint."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-070: iOS — recover from 401 (refresh token; sign out to sign-in on invalid session)",
        "labels": ["ios", "bug", "auth"],
        "description": doc(
            h2("Goal"),
            p("On launch the app showed 'Session expired. Please sign in again.' as a dead-end error "
              "with no way back to the sign-in screen; switching tabs then worked. Fix the underlying "
              "401 handling so the app recovers automatically and, when it can't, routes to sign-in."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Root cause: AppState.isAuthenticated flips true the moment Firebase restores the "
                "user, so tabs render and fire API calls BEFORE AuthService's async getIDToken sets "
                "the token on APIClient — the first request 401s ('session expired'); later tab "
                "loads work because the token has arrived. And a 401 was surfaced as an in-view "
                "error, never routing back to sign-in.",
                "APIClient: add a tokenProvider closure and, on a 401, refresh the token once and "
                "retry the request (fixes the launch race + expired tokens). If it's STILL 401, post "
                "a .apiUnauthorized notification and throw.",
                "AuthService: set the tokenProvider (Firebase getIDToken(forcingRefresh:true)); "
                "observe .apiUnauthorized and signOut() so currentUser → nil → ContentView shows "
                "SignInView (the user can sign in again).",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No proactive token-refresh timer — refresh-on-401 covers hourly Firebase token "
                "expiry",
                "No change to gating isAuthenticated on the token being ready (retry-on-401 is "
                "simpler and also covers expiry); could revisit if races persist",
                "No backend change",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Core/API/APIClient.swift (tokenProvider + refresh-and-retry + "
                ".apiUnauthorized)",
                "ios/TimeSense/Core/Auth/AuthService.swift (provide token; sign out on persistent 401)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "A first request that 401s (token not yet set) refreshes + retries and succeeds — no "
                "'session expired' on a valid session",
                "A genuinely invalid session (401 after refresh) signs out and shows the sign-in "
                "screen",
                "iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-062 (real Firebase in the app), TIME-066/067/068 (usable UI + data), the auth "
              "flow (AuthService/AppState/ContentView)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-071: Today shows untimed pending tasks (your full to-do list)",
        "labels": ["backend", "ux"],
        "description": doc(
            h2("Goal"),
            p("Captured tasks have no scheduled time, so the Today tab (which showed only scheduled "
              "blocks) looked empty even with many tasks — the user had no place to see their list "
              "(Now intentionally shows just the single best next action). Make GET /timeline/today "
              "also include untimed pending tasks when viewing today, so the user sees their full "
              "to-do list."),
            divider(),
            h2("Scope"),
            bullet_list([
                "GET /api/v1/timeline/today: when for_date == today, append the user's untimed "
                "pending tasks (scheduled_start is None) to the scheduled-today set; keep the "
                "scheduled_start-ascending sort (untimed sort last). For a specific non-today date, "
                "behaviour is unchanged (scheduled-for-that-date only)",
                "Test: an unscheduled pending (captured) task appears in /timeline/today",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No new 'all tasks' screen — Today becomes the list home; a dedicated task-list view "
                "is possible follow-up",
                "No change to Now (still the single best next action by design)",
                "No change to task scoring — better day-prioritization comes from the LLM extracting "
                "due dates on capture (now that the OpenAI key is valid), not from a scorer tweak",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/api/v1/timeline.py",
                "backend/tests/test_timeline.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "A captured (unscheduled, pending) task appears in GET /api/v1/timeline/today",
                "Scheduled tasks still appear and sort by time; untimed sort last",
                "Non-today dates unchanged; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_timeline.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-030/031 (Today/Capture), TIME-067 (same treatment for Now), a valid OpenAI key "
              "for due-date extraction on new captures."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-072: Rule-based date fallback for capture (works without the LLM)",
        "labels": ["backend", "capture"],
        "description": doc(
            h2("Goal"),
            p("Captured tasks weren't getting due dates — the LLM parse was failing (OpenAI 429 / "
              "quota) and the fallback just stored the raw text with no date. With no dates, every "
              "task ties at priority 3 and Now's 'best task' never changes when you add tasks. Add "
              "a rule-based date/time extractor so captures still get a due date (and a cleaner "
              "title) when the LLM is unavailable, making prioritization work."),
            divider(),
            h2("Scope"),
            bullet_list([
                "app/services/capture_date_parser.py: parse_datetime(raw, tz) extracting today/"
                "tonight/tomorrow, weekday names (next occurrence), 'Month Dayth', and 'at 5pm' / "
                "'9:30am' — returns a UTC due_at (default 5pm local when only a date is given) + a "
                "lightly cleaned, capitalized title with the scheduling phrase stripped",
                "CaptureService: on LLM failure, use the rule-based fallback (due_at + cleaned "
                "title) instead of the bare raw title",
                "Tests for the parser + updated capture fallback assertions (title now cleaned/"
                "capitalized)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Not a full NL date library — covers the common phrasings; the LLM remains the "
                "primary parser when available (and gives smarter titles/estimates)",
                "No backfill of existing undated tasks (only new captures get dates); no scorer "
                "change (it already prioritizes by due date)",
                "Doesn't fix the user's OpenAI quota — that's account billing; this makes the app "
                "degrade gracefully without it",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/capture_date_parser.py (new)",
                "backend/app/services/capture_service.py (use fallback)",
                "backend/tests/test_capture_date_parser.py (new), tests/test_capture.py (assertions)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "'Buy new pants today' → due_at = today (5pm local), title 'Buy new pants'",
                "'... today at 5pm' → due_at today 5pm; 'tomorrow' / weekday / 'July 5th' handled",
                "No date phrase → due_at None, title still cleaned/capitalized",
                "Capture works end-to-end even while OpenAI returns 429; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_capture_date_parser.py tests/test_capture.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-031 (capture), TIME-071 (Today list), the TaskScorer deadline weighting."),
            divider(),
            h2("Next Ticket"),
            p("TIME-073: 'Why this?' explanation on Now."),
        ),
    },

    {
        "summary": "TIME-073: Premium visual redesign (calm / minimal, Apple-like)",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("User feedback: 'the app looks cheap; it was supposed to look expensive.' Chosen "
              "direction: calm & minimal, Apple-like — white cards floating on a soft-gray canvas, "
              "a single refined indigo accent, quiet SF Pro typography, generous spacing, soft "
              "diffuse shadows. Elevate the design system (which every screen inherits) and the Now "
              "hero."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Palette (Assets.xcassets): white Surface (#FFFFFF) on soft-gray Background "
                "(#F4F4F6) so cards pop; deeper indigo accent (#4F46E5); refined neutrals; softer "
                "destructive/success. Light + dark variants",
                "DesignTokens: SF Pro (default face, not rounded) with a tighter heading scale + "
                "Tracking tokens; softer, more diffuse shadow tokens",
                "CardModifier: continuous-corner rounded surface (Radius.xl) with a hairline stroke "
                "and soft shadow; refined section-header style (wider tracking, caption size)",
                "Now hero: large tracked greeting header (not boxed), a spacious 'Do this next' hero "
                "card with the task/priority/estimate + quick actions, and a warmer empty state",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No new screens or navigation changes; no logic/data changes",
                "'Why this?' reasoning is the next ticket (plugs into the new hero card)",
                "Per-screen bespoke layouts beyond Now — other screens inherit the token/card "
                "upgrades; deeper per-screen polish can follow",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Assets.xcassets/*.colorset",
                "ios/TimeSense/Core/Design/DesignTokens.swift, Core/Design/ViewModifiers.swift",
                "ios/TimeSense/Features/Now/NowView.swift, Components/EmptyStateView.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "White cards on a soft-gray canvas with soft shadows; deep indigo accent; SF Pro "
                "hierarchy",
                "Now shows a large calm greeting + a spacious hero card",
                "iOS build succeeds; sign-in + Now render cleanly in light and dark",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO\n"
                "# + Simulator screenshot review of sign-in / Now"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-066 (asset catalog), the DesignTokens system, Now/Today/Capture screens."),
            divider(),
            h2("Next Ticket"),
            p("TIME-074: 'Why this?' reasoning on the Now hero card."),
        ),
    },

    {
        "summary": "TIME-074: Fix Now quick actions — wire Snooze/Not-now + stop label wrapping",
        "labels": ["ios", "backend", "bug"],
        "description": doc(
            h2("Goal"),
            p("On Now, the 'Not now' (and Snooze) buttons did nothing — empty actions — and the "
              "'Snooze' label wrapped to two lines. Wire them to recommendation feedback so they "
              "actually change the best task, filter suppressed tasks out of /now, and fix the "
              "action-row layout."),
            divider(),
            h2("Scope"),
            bullet_list([
                "iOS NowViewModel: add snooze(taskId) and notNow(taskId) → POST /recommendations/"
                "feedback ({task_id, signal: snooze|not_now, snooze_until}); reload after",
                "iOS QuickActionRow: wire onSnooze/onNotNow; full-width primary Done + two compact "
                "secondary pills with lineLimit(1)+fixedSize so labels never wrap",
                "Backend /now: exclude tasks from get_suppressed_task_ids (active snooze / not_now "
                "cooldown) so the actions actually surface a different best task",
                "Backend test: a not_now feedback suppresses that task from /now",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No snooze-duration picker (fixed ~3h default); no undo UI",
                "No change to Today/Insights actions",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
                "backend/app/api/v1/now.py, backend/tests/test_now.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Not now / Snooze change the best task (suppressed task no longer surfaces)",
                "Action labels fit on one line",
                "iOS build succeeds; backend suite passes (incl. new suppression test)",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-073 (Now hero redesign), the recommendations feedback endpoint + "
              "get_suppressed_task_ids."),
            divider(),
            h2("Next Ticket"),
            p("TIME-075: 'Why this?' reasoning on the Now hero card."),
        ),
    },

    {
        "summary": "TIME-075: 'Why this?' reasoning on the Now hero card",
        "labels": ["ios", "backend", "ux"],
        "description": doc(
            h2("Goal"),
            p("User asked why the recommended task is the best one. Per the premium-UX spec, Now "
              "should have a 'Why this?' explanation, hidden by default and revealed on tap. Add a "
              "deterministic reason to /now and an expandable 'Why this?' on the hero card."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend /now: add reason: str|None built from the chosen task — overdue / due "
                "today / due <weekday>, high priority, and 'fits your N free minutes'; a calm "
                "fallback when nothing stands out. Deterministic, no LLM",
                "iOS NowContext: decode reason; BestTaskCard shows a 'Why this?' button (sparkles + "
                "chevron) that expands to the reason text, hidden by default",
                "Backend test: /now returns a reason for the recommended task",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No LLM-generated rationale here (the recommendations endpoint already has an LLM "
                "'why'; Now stays fast + deterministic)",
                "No per-factor scoring breakdown UI",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/api/v1/now.py, backend/tests/test_now.py",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "/now returns a human reason (e.g. 'Recommended because it's due today and it fits "
                "your 240 free minutes.')",
                "Now shows a tappable 'Why this?' that expands to the reason; collapsed by default",
                "iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-073 (hero card), TIME-074 (Now actions), the TaskScorer."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-076: Make Settings rows functional (+ Sign Out, Delete My Data)",
        "labels": ["ios", "settings"],
        "description": doc(
            h2("Goal"),
            p("Most Settings rows were dead placeholders (chevron, no action), and there was no Sign "
              "Out. Wire every row to a real screen/action backed by existing endpoints, and add "
              "Sign Out + a working Delete My Data."),
            divider(),
            h2("Scope"),
            bullet_list([
                "New screens (SettingsScreens.swift): Profile (email + editable display_name via "
                "PATCH /users/me/profile), Subscription (read-only status from /subscriptions/me), "
                "Notifications (notification_mode picker → PATCH /users/me/preferences), Appearance "
                "(System/Light/Dark → @AppStorage applied at app root + PATCH preferences.theme), "
                "Privacy & Consent (summary), Calendar (honest status), About",
                "SettingsView: NavigationLinks to all of the above; Delete My Data → confirm alert "
                "→ DELETE /privacy/account?confirm=true → signOut; a Sign Out section → "
                "authService.signOut()",
                "App root applies the stored theme via .preferredColorScheme",
                "Register SettingsScreens.swift in the Xcode target",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No in-app StoreKit purchase / trial start (billing via the App Store); Subscription "
                "is read-only status",
                "No in-app calendar OAuth yet (Calendar screen states web-managed for now)",
                "No in-app data-export download yet (Privacy screen summarizes; delete is wired)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Features/Settings/SettingsView.swift, SettingsScreens.swift (new)",
                "ios/TimeSense/App/TimeSenseApp.swift (theme), TimeSense.xcodeproj (add file)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Every Settings row navigates to a working screen or performs its action",
                "Sign Out returns to the sign-in screen; Delete My Data confirms then erases + signs "
                "out",
                "Appearance changes the app theme immediately; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-055 (privacy export/delete), users preferences/profile endpoints, "
              "/subscriptions/me, AuthService.signOut, TIME-073 (design tokens)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-077: Now shows alternatives + richer LLM 'Why this?'",
        "labels": ["ios", "backend", "recommendations"],
        "description": doc(
            h2("Goal"),
            p("The 'Why this?' just said 'best move right now'. Show two alternative options on Now "
              "and make the reason a real explanation of why the best beats them — weighing the "
              "other options, time of day, likely energy, free time before the next commitment, and "
              "deadlines (LLM, with a deterministic fallback)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "RecommendationService: enrich the explain prompt to include the alternatives, "
                "time-of-day + energy heuristic (from the user's timezone), free time, and "
                "deadlines; public explain_choice(); richer deterministic fallback. Pass "
                "user_timezone through recommend()",
                "/now: return alternatives (runner-up ranked[1:3]) and use "
                "RecommendationService.explain_choice for the reason; pass the user's timezone",
                "/recommendations: pass user timezone to recommend()",
                "iOS: NowContext decodes alternatives; Now shows an 'Or consider' list of compact "
                "AlternativeRow cards (tap the circle to complete); the hero 'Why this?' shows the "
                "richer reason",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No explicit energy tracking — time-of-day is used as the energy proxy",
                "Reason is generated on each Now load (eager); lazy-on-tap fetch is a possible "
                "follow-up if latency matters",
                "No reordering/pinning of alternatives beyond the scorer ranking",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/recommendation_service.py, app/api/v1/now.py, "
                "app/api/v1/recommendations.py",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "/now returns up to 2 alternatives + a reason that references time of day / free "
                "time / deadlines vs the alternatives",
                "Now shows the best hero + an 'Or consider' list; 'Why this?' shows the richer text",
                "LLM used when available, deterministic fallback otherwise; iOS build + suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py tests/test_recommendations.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-075 ('Why this?'), the RecommendationService + TaskScorer, /recommendations."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-078: Lazy-load 'Why this?' on tap (keep Now instant)",
        "labels": ["ios", "backend", "performance"],
        "description": doc(
            h2("Goal"),
            p("TIME-077 generated the LLM reason on every /now load (~1-2s latency + a cost per "
              "load, even though 'Why this?' is collapsed by default). Make /now fast again (no LLM) "
              "and fetch the explanation lazily only when the user taps 'Why this?'."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: extract shared _ranked_candidates(); /now returns best + alternatives + "
                "usable_minutes with NO LLM call (reason stays null); new GET /now/why?task_id= "
                "recomputes the ranking, finds the task + its alternatives, and returns the "
                "explain_choice reason (404 if the task isn't currently recommended)",
                "iOS: WhyThis self-loads — on first expand it calls the loader (GET /now/why), shows "
                "a 'Thinking…' spinner, caches the result; BestTaskCard passes a loadWhy closure; "
                "NowViewModel.fetchWhy(taskId)",
                "Tests: /now has null reason + /now/why returns a reason; unknown task → 404",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No caching of the reason server-side (recomputed per tap; cheap enough and always "
                "current)",
                "No prefetch — the call happens on tap only",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/api/v1/now.py, backend/tests/test_now.py",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "/now makes no LLM call (fast); reason is null",
                "Tapping 'Why this?' fetches + shows the reason with a brief 'Thinking…' state; "
                "collapsing/re-expanding doesn't refetch",
                "iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-077 (alternatives + LLM why), RecommendationService.explain_choice."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-079: 'Why this?' must justify the pick (not argue for resting)",
        "labels": ["backend", "recommendations", "bug"],
        "description": doc(
            h2("Goal"),
            p("The 'Why this?' contradicted the recommendation — for a Home Depot task it said "
              "'consider resting now… plan your trip when more energized', i.e. it argued against "
              "doing the recommended task. Constrain the LLM to justify the fixed pick and reframe "
              "the energy hints so they never suggest resting/waiting/a different task."),
            divider(),
            h2("Scope"),
            bullet_list([
                "recommendation_service _EXPLAIN_SYSTEM: state the task is ALREADY chosen and fixed; "
                "the model's only job is to justify why it's a good use of this moment; explicitly "
                "forbid suggesting rest, waiting, doing it later, or a different task",
                "Reframe _part_of_day energy hints to be descriptive framing (e.g. evening: "
                "'energy is winding down, so finishing a manageable task feels satisfying') instead "
                "of prescriptive avoidance ('better to wrap up than start heavy work')",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Not adding non-task suggestions like 'take a break' — recommendations still come "
                "only from the user's tasks; an energy-aware break/rest suggestion would be a "
                "separate product feature",
                "No scorer change; no iOS change (backend prompt only)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend/app/services/recommendation_service.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "The reason justifies doing the recommended task now and never suggests resting / "
                "waiting / a different task",
                "Time-of-day/energy still inform the framing; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest -q"),
            divider(),
            h2("Dependencies"),
            p("TIME-077/078 (Now why + lazy load)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-080: Local-time-aware Now (correct greeting + wind-down moment)",
        "labels": ["ios", "backend", "recommendations"],
        "description": doc(
            h2("Goal"),
            p("Make Now grounded in the user's LOCAL time (always known) rather than assumed energy. "
              "Fix the greeting (was UTC-based) and add a time-aware 'moment' that gently suggests "
              "winding down when it's late locally and nothing is urgent — so the assistant isn't "
              "pushing a task at 11pm."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Bug: _greeting used UTC hour → wrong for the user's timezone. Now derived from the "
                "user's profile timezone (adds a 'You're up late' band before 5am)",
                "New NowResponse.moment (str|None): deterministic, local-time-aware. When local hour "
                "≥ 21 or < 5 AND no urgent task (overdue / due ≤ 3h / priority 1), returns a gentle "
                "wind-down nudge; else null. No LLM (instant, reliable)",
                "iOS: NowContext decodes moment; NowView shows a calm MomentCard (moon icon) above "
                "the best task when present — the top task is still offered",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Recommendations still come only from the user's tasks — the moment is a framing "
                "nudge, not a new 'rest' task",
                "No energy tracking (local time is the reliable signal per user guidance)",
                "Only a wind-down moment for v1; other time-of-day moments (e.g. morning kickoff) "
                "can follow",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/api/v1/now.py, backend/tests/test_now.py",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Greeting matches the user's local time (not UTC)",
                "Late local time + nothing urgent → a wind-down moment shown above the best task; "
                "urgent task present → no moment",
                "iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-079 (why justifies pick), user profile timezone, TaskScorer."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-081: Usable-time 'time left today' cap uses local midnight",
        "labels": ["backend", "bug", "recommendations"],
        "description": doc(
            h2("Goal"),
            p("UsableTimeService capped 'time left today' at UTC midnight, so the 'usable minutes' "
              "shown on Now was wrong for anyone not on UTC (over- or under-reported, especially in "
              "the evening). Use the user's local midnight instead — consistent with the local-time "
              "greeting/moment work (TIME-080)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "UsableTimeService.calculate takes user_timezone; the end-of-day cap is the user's "
                "next LOCAL midnight converted to UTC (bad tz string falls back to UTC)",
                "Callers pass the timezone: /now (_ranked_candidates via user.profile.timezone) and "
                "RecommendationService.recommend (already has user_timezone). Google Assistant "
                "webhook keeps the UTC default",
                "Test: local-midnight cap (UTC+11 late-local → ~60 min vs UTC → 240)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No change to the free-gap / block-merging logic or the 4h/5min caps",
                "No iOS change (display already shows whatever the API returns)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/usable_time_service.py, app/api/v1/now.py, "
                "app/services/recommendation_service.py, tests/test_usable_time.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "'time left today' is measured to the user's local midnight, not UTC",
                "Backward compatible (defaults to UTC); full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_usable_time.py tests/test_now.py -v"),
            divider(),
            h2("Dependencies"),
            p("TIME-080 (local-time Now), user profile timezone."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-082: Task duration brain — seed lookup table + per-user learned estimates",
        "labels": ["backend", "recommendations", "brain"],
        "description": doc(
            h2("Goal"),
            p("Foundation of the scheduling 'brain': every task gets a realistic time estimate. "
              "Start from a seed lookup table (category → minutes) so estimates work even without "
              "the LLM, and add a per-user learned table the assistant refines from real durations "
              "over time. This underpins later best-time scheduling and feasibility warnings."),
            divider(),
            h2("Scope"),
            bullet_list([
                "app/services/task_duration.py: DEFAULT_DURATIONS seed table + keyword-based "
                "infer_category(title) (appointment/meeting/call/email/shopping/errand/chore/"
                "exercise/cooking/writing/reading/admin/travel/general)",
                "Model + migration: task_duration_estimates (user_id, category, estimated_minutes, "
                "sample_count; unique per user+category) — the personal table the AI edits",
                "TaskDurationRepository.record_actual: EMA (alpha 0.3) folds a real observed "
                "duration into the learned estimate; TaskDurationEstimator.estimate returns the "
                "learned value when present else the seed",
                "Capture: fill estimated_minutes from the estimator when the LLM didn't provide one "
                "— so every task has a sensible duration",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "This ticket does NOT schedule tasks to a time or check feasibility (follow-ups) — "
                "it just makes durations reliable + learnable",
                "No UI to capture 'how long did it take?' yet (the learning trigger is a follow-up); "
                "record_actual is ready for it",
                "Category inference is keyword-based for reliability; an LLM categoriser can refine "
                "later",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/task_duration.py, task_duration_service.py (new)",
                "backend/app/models/task_duration.py + migration + models/__init__.py",
                "backend/app/repositories/task_duration_repository.py (new)",
                "backend/app/api/v1/capture.py; backend/tests/test_task_duration.py (new)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "infer_category maps common titles correctly (dentist→appointment, Home Depot→"
                "shopping, etc.)",
                "A captured task with no LLM estimate still gets the seed duration",
                "record_actual moves the learned estimate toward observed durations; later estimates "
                "use it; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head && pytest tests/test_task_duration.py -v\n"
                "cd backend && pytest -q"
            ),
            divider(),
            h2("Dependencies"),
            p("Capture (TIME-031/072), Task model."),
            divider(),
            h2("Next Ticket"),
            p("TIME-083: learn actual durations on completion; TIME-084: feasibility warnings; "
              "TIME-085: best-time scheduling."),
        ),
    },

    {
        "summary": "TIME-083: Learn actual durations — 'How long did that take?' during learning",
        "labels": ["ios", "backend", "brain"],
        "description": doc(
            h2("Goal"),
            p("Feed the duration brain real data: when a task is completed, ask a one-tap 'How long "
              "did that take?' (chips ~15/30/60m) — but only while the assistant is still learning "
              "that category (so it fades away and never becomes a chore)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Repo: LEARNING_SAMPLE_TARGET (5) + learning_active(user, category) = sample_count < "
                "target; estimator.should_ask(user, title)",
                "Endpoints: GET /tasks/{id}/duration-prompt → {ask, category} (ask only during "
                "learning); POST /tasks/{id}/duration-feedback {actual_minutes} → record_actual "
                "(EMA) and return the updated learned {category, estimated_minutes}",
                "iOS: after markDone, call duration-prompt; if ask, present a confirmationDialog "
                "('~15 min / ~30 min / ~1 hour / Skip'); the chip POSTs feedback. markDone now "
                "takes the title (hero + alternatives)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No manual duration entry beyond the three chips (keep it one-tap); no editing past "
                "observations",
                "No feasibility/scheduling yet (TIME-084/085)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/repositories/task_duration_repository.py, "
                "app/services/task_duration_service.py, app/api/v1/tasks.py, tests/test_task_duration.py",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Completing a task in a still-learning category prompts once; a chip records the "
                "actual and moves the learned estimate",
                "After the sample target is reached, the prompt stops appearing for that category",
                "iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_task_duration.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-082 (duration brain), the tasks router, Now markDone flow."),
            divider(),
            h2("Next Ticket"),
            p("TIME-084: feasibility warnings; TIME-085: best-time scheduling."),
        ),
    },

    {
        "summary": "TIME-084: Feasibility — warn when the best task won't fit, suggest a slot",
        "labels": ["ios", "backend", "brain"],
        "description": doc(
            h2("Goal"),
            p("Warn the user when a task can't realistically be finished before it's due, and point "
              "to the next open slot — using the task's estimated duration, the working-hours window "
              "(default 8am–9pm local), and existing scheduled blocks."),
            divider(),
            h2("Scope"),
            bullet_list([
                "SchedulingService (shared core): find_slot(now, duration, scheduled, tz, "
                "not_before) → earliest fitting start today within the working window and around "
                "busy blocks; free_minutes_before(deadline, ...) → free minutes before a deadline",
                "/now: for the best task, if it has a due_at in the future today and "
                "free_minutes_before(due) < estimated_minutes → return a feasibility warning "
                "{fits:false, message, suggested_slot} with the next realistic slot (or 'no slot "
                "left today')",
                "iOS: NowContext decodes feasibility; a gentle FeasibilityCard (warning tint) under "
                "the best task when fits==false",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Working hours are a hardcoded default (8–21) for v1 — a Settings preference is a "
                "follow-up",
                "Feasibility only for the best task (not every task) for v1",
                "No auto-scheduling here (TIME-085)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/scheduling_service.py (new), app/api/v1/now.py, "
                "tests/test_scheduling.py (new)",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "find_slot respects the working window + busy blocks; free_minutes_before excludes "
                "scheduled time",
                "Best task due soon with too little free time → Now shows a warning + next slot",
                "iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_scheduling.py tests/test_now.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-082 (durations), TIME-080/081 (local-time Now), user profile timezone."),
            divider(),
            h2("Next Ticket"),
            p("TIME-085: best-time auto-scheduling with undo."),
        ),
    },

    {
        "summary": "TIME-085: Best-time auto-scheduling with easy Undo",
        "labels": ["ios", "backend", "brain"],
        "description": doc(
            h2("Goal"),
            p("Complete the scheduling brain: when a task is captured, auto-place it into the next "
              "open slot in the day (using its estimate + working hours + existing blocks), and let "
              "the user Undo the placement on Today with one tap."),
            divider(),
            h2("Scope"),
            bullet_list([
                "tasks.auto_scheduled boolean (migration) + on Task model + TaskResponse",
                "Capture: if the task is untimed and due today/undated, SchedulingService.find_slot "
                "assigns scheduled_start/end and marks auto_scheduled=True (skips when no slot fits "
                "today)",
                "POST /tasks/{id}/unschedule → clears the slot + auto_scheduled (returns the task)",
                "iOS: TimelineTask decodes auto_scheduled; Today's TimelineCard shows 'Scheduled by "
                "TimeSense · Undo' for auto-placed tasks; Undo calls unschedule + reloads",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No rescheduling/optimisation of already-placed tasks; no drag-and-drop (product "
                "rule)",
                "Only auto-places today (not future days); working hours still the 8–21 default",
                "Auto-placement isn't a calendar write (internal scheduling only; calendar writes "
                "still require approval)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend: models/task.py + migration, schemas/task.py, services/task_service.py, "
                "api/v1/capture.py, api/v1/tasks.py, tests/test_autoschedule.py",
                "ios: Features/Today/TodayViewModel.swift, TimelineCard.swift, TodayView.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "A captured today/undated task is placed into the next open slot within working "
                "hours (when one exists) with auto_scheduled=true",
                "Undo on Today clears the time (scheduled_start null, auto_scheduled false)",
                "iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head && pytest tests/test_autoschedule.py -v\n"
                "cd backend && pytest -q\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-084 (SchedulingService), TIME-082 (durations), capture + Today timeline."),
            divider(),
            h2("Next Ticket"),
            p("Working-hours preference in Settings; feasibility for all tasks; TIME-058 beta "
              "checklist."),
        ),
    },

    {
        "summary": "TIME-086: Configurable working hours (Settings) drive scheduling",
        "labels": ["ios", "backend", "settings"],
        "description": doc(
            h2("Goal"),
            p("Replace the hardcoded 8am–9pm scheduling window with a per-user preference so "
              "auto-scheduling and feasibility match the user's real day."),
            divider(),
            h2("Scope"),
            bullet_list([
                "user_preferences.work_start_hour / work_end_hour (migration; defaults 8/21) on the "
                "model, UserPreferencesResponse, and UserPreferencesUpdate (validated 0–22 / 1–23, "
                "end > start)",
                "Repo update_preferences accepts the new fields; PATCH /users/me/preferences already "
                "routes them",
                "Capture auto-schedule and /now feasibility build SchedulingService from the user's "
                "hours (fallback 8/21)",
                "iOS: Settings ▸ Working Hours screen (start/end hour pickers, 12-hour labels, save "
                "→ PATCH); disabled when end ≤ start",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No per-day-of-week hours or multiple windows (single daily window for v1)",
                "End hour capped at 23 (avoids midnight-rollover edge in the window math)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend: models/user.py + migration, schemas/user.py, repositories/user_repository.py, "
                "api/v1/capture.py, api/v1/now.py, tests/test_task_duration.py",
                "ios: Features/Settings/SettingsScreens.swift, SettingsView.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "GET /users/me returns work_start_hour/work_end_hour (default 8/21); PATCH updates "
                "them; end ≤ start → 422",
                "Auto-scheduling + feasibility respect the configured hours",
                "Settings ▸ Working Hours edits and saves; iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head && pytest -q\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-084/085 (scheduling), TIME-076 (Settings screens), preferences endpoints."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-087: On-device dev — reach the Mac backend over the LAN (fix 'cannot connect')",
        "labels": ["ios", "devx", "bug"],
        "description": doc(
            h2("Goal"),
            p("Demoing on a physical iPhone failed with 'cannot connect to the server': on a device "
              "'localhost' is the phone, not the Mac. Point device debug builds at the Mac's backend "
              "over the LAN and allow the plain-HTTP local connection."),
            divider(),
            h2("Scope"),
            bullet_list([
                "APIClient.resolveBaseURL(): API_BASE_URL env still wins; simulator → localhost; "
                "physical device DEBUG → the Mac's Bonjour .local name (stable across IP changes); "
                "release → production URL placeholder",
                "Info.plist (new, merged with GENERATE_INFOPLIST_FILE=YES): "
                "NSAppTransportSecurity.NSAllowsLocalNetworking=true + NSLocalNetworkUsageDescription "
                "so cleartext HTTP to the LAN/.local is permitted and the device prompts for local-"
                "network access",
                "Set INFOPLIST_FILE for the app target (both configs); verified the built plist has "
                "both the ATS key and the generated keys (launch screen, bundle id)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Not a production networking change — Release keeps the (placeholder) HTTPS API URL",
                "No TLS/tunnel; relies on same-Wi-Fi + Bonjour for local dev",
                "The .local name is this Mac's; overridable via the API_BASE_URL scheme env var",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Core/API/APIClient.swift",
                "ios/TimeSense/Info.plist (new) + TimeSense.xcodeproj (INFOPLIST_FILE)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Device debug build connects to the Mac backend over Wi-Fi (backend already binds all "
                "interfaces via run_dev.py)",
                "Built Info.plist contains NSAllowsLocalNetworking AND the generated keys; iOS build "
                "succeeds",
                "Simulator still uses localhost",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO\n"
                "# on device: same Wi-Fi, run_dev.py running, tap Allow on the local-network prompt"
            ),
            divider(),
            h2("Dependencies"),
            p("run_dev.py (binds all interfaces, TIME-069), the app's networking layer."),
            divider(),
            h2("Next Ticket"),
            p("TIME-058: Beta Smoke Test and Release Checklist."),
        ),
    },

    {
        "summary": "TIME-058: Beta Smoke Test & Release Checklist (v1 close-out)",
        "labels": ["release", "docs", "qa"],
        "description": doc(
            h2("Goal"),
            p("Close out the v1 build: a repeatable smoke test, a manual beta test checklist, and a "
              "go/no-go release checklist — so any build can be validated before it ships."),
            divider(),
            h2("Scope"),
            bullet_list([
                "scripts/smoke_test.py: liveness + auth-gate checks against a running backend "
                "(health 200; protected routes 401) — fast 'is it alive and sane?' check",
                "docs/launch/beta_smoke_test.md: ~10-min manual device checklist covering the full "
                "loop (auth, capture→brain, Now, Today, Settings, web)",
                "docs/launch/release_checklist.md: go/no-go across engineering, infra, auth/data, "
                "store prep, legal, and post-v1 follow-ups",
                "Verify + record the stack state (backend suite, iOS/web builds, live smoke); mark "
                "v1 feature-complete in project memory",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Not the actual store submission or production deploy (gated items in the checklist)",
                "No automated device UI tests (manual checklist for now)",
                "Post-v1 feature work is captured as follow-ups, not built here",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "scripts/smoke_test.py (new)",
                "docs/launch/beta_smoke_test.md, docs/launch/release_checklist.md (new)",
                "docs/project_memory/* (v1 close-out)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "smoke_test.py passes against the running backend",
                "Beta + release checklists exist and reflect the true build state (honest about "
                "unverified items, e.g. Android build needs a JDK)",
                "Project memory marks v1 feature-complete with the post-v1 follow-up list",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "python scripts/smoke_test.py\n"
                "cd backend && pytest -q\n"
                "cd web && npm run build"
            ),
            divider(),
            h2("Dependencies"),
            p("The whole v1 build (Phases 0–14) + the brain (TIME-082–087)."),
            divider(),
            h2("Next Ticket"),
            p("Post-v1: production deploy + store submission; per-weekday working hours; feasibility "
              "for all tasks; in-app calendar/subscription/export."),
        ),
    },

    {
        "summary": "TIME-088: Rename Now 'Why this?' link to 'Why This Recommendation?'",
        "labels": ["ios", "copy", "ux"],
        "description": doc(
            h2("Goal"),
            p("Clarify the recommendation-explanation affordance on the Now page: rename the "
              "'Why this?' link to 'Why This Recommendation?'."),
            divider(),
            h2("Scope"),
            bullet_list([
                "NowView WhyThis: change the button label 'Why this?' → 'Why This Recommendation?'",
                "No behavior change — still collapsed by default, lazily fetches the reason on tap",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No change to the reason content, the lazy-load, or the backend /now/why endpoint",
                "No other copy changes",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Now/NowView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "The Now best-task card shows 'Why This Recommendation?' instead of 'Why this?'",
                "Tapping it still expands and loads the explanation; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-075/078 ('Why this?' + lazy load)."),
            divider(),
            h2("Next Ticket"),
            p("Post-v1 backlog."),
        ),
    },

    {
        "summary": "TIME-089: Rich structured 'Why This Recommendation?' explanation + pipeline",
        "labels": ["ios", "backend", "recommendations", "brain"],
        "description": doc(
            h2("Goal"),
            p("Replace the one-line 'Why This Recommendation?' with a full, structured explanation "
              "(recommended action, the context used, decision factors, alternatives considered, a "
              "confidence score, and a summary), backed by a real recommendation-explanation "
              "pipeline that stores an audit event. Signals are included only when we actually have "
              "them — no fabricated context."),
            divider(),
            h2("Scope"),
            bullet_list([
                "recommendation_explainer.build_explanation: normalizes live context (calendar free "
                "time + next event, time-of-day/focus, health/energy from today's sleep signal if "
                "present, location from a recent commute if present, task data), computes "
                "deterministic decision_factors (Priority/Time fit/Energy match/Location fit/"
                "Urgency) + a heuristic confidence, deterministic alternative reasons, and an LLM "
                "summary (deterministic fallback)",
                "GET /now/why returns the structured WhyResponse (recommended_action, confidence, "
                "context_used, decision_factors, alternatives_considered, summary; keeps a "
                "backward-compatible `reason`) and stores a recommendation_events audit row",
                "recommendation_events table (JSONB on Postgres / JSON on SQLite; migration)",
                "iOS: RecommendationExplanation model; 'Why This Recommendation?' now fetches lazily "
                "then presents a sheet with sections (Recommended action, Confidence, Context used, "
                "Decision factors, Other options considered, Summary)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No live GPS place-type ('at home') — location is only commute-derived; energy is "
                "sleep-derived; both omitted honestly when absent",
                "Not a separate /recommendation/next-action route — the same pipeline runs behind "
                "the lazy /now/why (the recommendation itself is already on /now)",
                "No per-factor numeric weights exposed; confidence is a documented heuristic",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend: services/recommendation_explainer.py (new), models/recommendation_event.py "
                "(new) + migration + __init__, api/v1/now.py, tests/test_now.py",
                "ios: Features/Now/NowView.swift (sheet), NowViewModel.swift (model + fetch)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "/now/why returns recommended_action + confidence (0.5–0.95) + context_used + "
                "decision_factors + alternatives_considered + summary",
                "Only available signals appear (health/location omitted when absent); an audit row "
                "is written",
                "Tapping 'Why This Recommendation?' opens the structured sheet; iOS build + suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && alembic upgrade head && pytest tests/test_now.py -v\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-077/078 (why + lazy load), TIME-082 (durations), TIME-084 (scheduling context), "
              "sleep/commute signals."),
            divider(),
            h2("Next Ticket"),
            p("Post-v1 backlog."),
        ),
    },

    {
        "summary": "TIME-090: Redesign the Now page to the approved mockup",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("Rebuild the Now page to match the approved mockup: an analysis banner, context chips, "
              "a richer Best Next Action card with an inline confidence bar, and an 'Other good "
              "options' list."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: expose `confidence` (0–1) on /now for the best task, computed by a shared "
                "compute_confidence() (extracted from the explainer) so the card and the "
                "explanation sheet agree",
                "iOS NowView: inline 'Now' title + sparkles; AnalysisBanner ('TimeSense analyzed "
                "your day · Re-evaluated N min ago' from lastLoaded); ContextChipsRow (Calendar/"
                "Routine/Location/Time/Tasks); BestNextActionCard (header + 'AI Recommended' badge, "
                "category icon, title + 'for N minutes', meta line, inline Confidence bar, divider, "
                "'Why this recommendation?' → sheet, plus Done/Snooze/Not-now); OtherOptionsSection "
                "list (category icon, title, 'N min · descriptor', chevron → the task's explanation)",
                "Client-side taskCategoryStyle(title) → icon/colour/descriptor for the task tiles",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "The center '+' FAB tab bar in the mockup is a separate navigation change (follow-up), "
                "not in this ticket",
                "Category styling is client-side keyword inference (no backend category field on the "
                "task response)",
                "Kept Done/Snooze/Not-now on the card (essential for the learning loop) though the "
                "mockup omits them",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/recommendation_explainer.py, app/api/v1/now.py",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "/now returns confidence matching the explanation sheet",
                "Now shows the analysis banner, context chips, the redesigned best-action card with "
                "an inline confidence bar, and 'Other good options'",
                "iOS build + backend suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest -q\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-089 (structured why + confidence), TIME-077 (alternatives), the design tokens."),
            divider(),
            h2("Next Ticket"),
            p("Center '+' FAB tab bar; post-v1 backlog."),
        ),
    },

    {
        "summary": "TIME-091: Context chips fit on one row (no horizontal scroll)",
        "labels": ["ios", "ux"],
        "description": doc(
            h2("Goal"),
            p("The Now context chips (Calendar · Routine · Location · Time · Tasks) were in a "
              "horizontal ScrollView; they should all be visible at once, no scrolling."),
            divider(),
            h2("Scope"),
            bullet_list([
                "ContextChipsRow: drop the horizontal ScrollView; lay the five chips in an HStack "
                "where each takes an equal share (frame maxWidth .infinity), with lineLimit(1) + "
                "minimumScaleFactor so labels never truncate on narrow screens",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Chips remain non-interactive (decorative signal labels) for now",
                "No change to any other Now element",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Now/NowView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "All five chips are visible simultaneously on iPhone widths with no horizontal scroll",
                "Labels don't truncate; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-090 (Now redesign)."),
            divider(),
            h2("Next Ticket"),
            p("Post-v1 backlog."),
        ),
    },

    {
        "summary": "TIME-092: Redesign the Today page to the approved mockup",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("Rebuild the Today page to match the approved mockup: a date + progress header, an 'AI "
              "Recommended Now' card (the same best-next-action as Now), and a 'Smart Plan' grouped "
              "into Morning / Afternoon / Evening (and Anytime)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "TodayViewModel: also fetch /now for the recommendation card; add fetchExplanation "
                "and markDone(taskId)",
                "iOS NowTask: decode due_at (for 'before 6:00 PM'); TaskCategoryStyle gains "
                "locationAware (Errand/Appointment) for the 'Location-aware' tag",
                "TodayView: DateSummaryRow ('July 6, 2026' + 'N of M complete' + calendar icon); "
                "'AI Recommended Now' card (category icon, title + 'before <due>', meta line, 'Why "
                "this recommendation?' → shared sheet); 'Smart Plan' card grouping tasks by "
                "Morning/Afternoon/Evening/Anytime with tap-to-complete rows (category icon, title, "
                "'time · duration')",
                "Reuse the shared WhyThis / RecommendationExplanationSheet / taskCategoryStyle "
                "(made internal) from the Now redesign",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Tab bar unchanged (per prior instruction — no '+' FAB)",
                "Dropped the visible 'Scheduled by TimeSense · Undo' on the row for the clean mockup "
                "look (unschedule still exists in the VM) — can re-add as a swipe/subtle control",
                "No timeline connector thread between rows (possible refinement); completion on "
                "Today doesn't trigger the duration-learning prompt yet",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Features/Today/TodayView.swift, TodayViewModel.swift",
                "ios/TimeSense/Features/Now/NowView.swift (shared helpers internal), NowViewModel.swift (NowTask due_at)",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Today shows the date + 'N of M complete', an AI Recommended card when there's a "
                "best task, and the Smart Plan grouped by time of day",
                "Tapping a plan row marks it done; 'Why this recommendation?' opens the explanation "
                "sheet; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-090/089 (Now redesign + explanation), TIME-071/085 (Today tasks + scheduling)."),
            divider(),
            h2("Next Ticket"),
            p("Post-v1 backlog."),
        ),
    },

    {
        "summary": "TIME-093: 'Why this recommendation' screen — Signals analyzed + confidence ring",
        "labels": ["ios", "backend", "design", "recommendations"],
        "description": doc(
            h2("Goal"),
            p("Redesign the recommendation-explanation screen (the key recruiter-facing view) to the "
              "approved mockup: a Recommended-action + confidence-ring header, a 'Signals analyzed' "
              "list (Calendar / Time of day / Location / Priority / Energy, each with a green check "
              "when available), and 'Alternatives considered'."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: build_explanation returns structured `signals` (name/detail/available) for "
                "Calendar, Time of day, Location, Priority, Energy — available=False (no check) when "
                "a signal isn't connected (Location/Energy); WhyResponse gains `signals`",
                "iOS: RecommendationExplanation decodes signals; RecommendationExplanationSheet "
                "rebuilt — RecommendedActionHeaderCard (icon + title + 'for N minutes' | Confidence "
                "ring), SignalsCard (icon + name + detail + check), AlternativesCard (icon + title + "
                "reason + chevron), plain-English Summary, and an 'Evaluated just now' timestamp",
                "New ConfidenceRing component (circular %)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Signals stay honest — Location/Energy show 'not connected yet' (no green check) "
                "until those integrations exist",
                "Alternative rows' chevron is presentational (no nested navigation yet)",
                "Timestamp is client-side ('just now' on fetch)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/recommendation_explainer.py, app/api/v1/now.py",
                "ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "/now/why returns signals (Calendar/Time of day/Location/Priority/Energy) with "
                "availability",
                "The sheet shows the confidence ring, Signals analyzed with checks, Alternatives, and "
                "a summary; iOS build + suite pass",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "cd backend && pytest tests/test_now.py -q\n"
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-089 (structured explanation), TIME-090 (Now redesign)."),
            divider(),
            h2("Next Ticket"),
            p("Capture / Insights / Learned Patterns / Working Hours / Calendar / Privacy / "
              "Subscription / Settings redesigns (screens 3,5-12)."),
        ),
    },

    {
        "summary": "TIME-094: Redesign the Capture screen (AI-native)",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("Make Capture feel AI-native per the approved mockup — a hero capture icon, clearer "
              "AI copy, quick type chips, a voice affordance, and a 'TimeSense can detect' row."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Hero: large indigo circle with a waveform icon; title 'What's on your mind?'; copy "
                "'Speak or type naturally. TimeSense uses AI to turn it into tasks, reminders, and "
                "plans.'",
                "Input box with a mic button (voice = 'coming soon' alert stub for now)",
                "Quick chips (Task/Reminder/Schedule/Errand/Idea) — selectable hints",
                "Full-width Capture button; 'TimeSense can detect' row (Time / Priority / Task type / "
                "Schedule fit); sparkles nav icon",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Voice-to-text not implemented yet (mic shows a coming-soon alert) — real Speech "
                "framework is a follow-up feature ticket",
                "Chips are visual hints (not yet wired to the parse); capture behavior unchanged",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Capture/CaptureView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Capture matches the mockup (hero, copy, input+mic, chips, button, detect row)",
                "Capturing still creates a task; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("Capture flow (TIME-031), the design tokens."),
            divider(),
            h2("Next Ticket"),
            p("TIME-095: Insights redesign."),
        ),
    },

    {
        "summary": "TIME-095: Redesign Insights locked state (preview cards)",
        "labels": ["ios", "design", "premium"],
        "description": doc(
            h2("Goal"),
            p("Replace the bare Insights paywall with a preview of the AI value per the mockup: a "
              "'Your AI Insights' lock banner + sample preview cards + upgrade CTA."),
            divider(),
            h2("Scope"),
            bullet_list([
                "InsightsPremiumGate rebuilt: indigo lock banner (better copy); preview cards (Best "
                "focus window / Pattern detected / Schedule balance / Routine consistency) with "
                "small illustrative charts (line/bars/ring) under a subtle locked veil; 'Upgrade to "
                "Premium' button + 'See all features'; crown nav icon",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Preview values are illustrative samples (not the user's real data); StoreKit "
                "purchase is still a follow-up",
                "Premium (unlocked) Insights body is unchanged",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Insights/InsightsView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Non-premium Insights shows preview cards + upgrade CTA; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("Insights (TIME-046), subscription gating."),
            divider(),
            h2("Next Ticket"),
            p("TIME-096: Learned Patterns rename + redesign."),
        ),
    },

    {
        "summary": "TIME-096: Rename Learned Assumptions to Learned Patterns + redesign",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("Rename 'Learned Assumptions' to 'Learned Patterns' and redesign to the mockup: an "
              "explainer banner + icon rows with confidence/source + an add button."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Rename the screen title + the Settings row to 'Learned Patterns'",
                "Banner: 'TimeSense learns from your behavior to make smarter recommendations. You "
                "can edit or delete any pattern.'",
                "Rows: routine icon (Sleep moon / Breakfast cup / Lunch fork.knife / Morning sun / "
                "Evening moon.stars) + name + time range + confidence line + chevron (tap to edit)",
                "Confidence derived honestly client-side: customized -> 'High - Set by you', else "
                "'Medium - Default pattern' (no fabricated day counts)",
                "'Add manual pattern' button (coming-soon stub — backend routines are a fixed set)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No real confidence/observation-count backend field yet (routines are seeded + "
                "user-edited)",
                "Manual pattern creation not supported yet (stub)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Features/Settings/LearnedAssumptionsView.swift, SettingsView.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Title + Settings row read 'Learned Patterns'; rows show icon/time/confidence; edit "
                "still works; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("Routines (TIME-039/047)."),
            divider(),
            h2("Next Ticket"),
            p("TIME-097: Working Hours explainer."),
        ),
    },

    {
        "summary": "TIME-097: Working Hours redesign (explainer + repeat days)",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("Explain why working hours matter and match the mockup: an explainer banner, Start/End "
              "rows, a Repeat day selector, and a Save button."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Explainer banner: 'TimeSense uses your working hours to decide when tasks are "
                "appropriate and to protect your personal time.'",
                "Card with Start/End menu-picker rows + a Repeat day-of-week selector (Mon-Fri "
                "default) + Save button; end<=start validation retained",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Per-day hours not persisted yet — the Repeat selector is visual (single window "
                "still applies); a future premium feature",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Settings/SettingsScreens.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Banner + Start/End + Repeat + Save render; saving still works; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-086 (working hours pref)."),
            divider(),
            h2("Next Ticket"), p("TIME-098: Calendar screen redesign."),
        ),
    },

    {
        "summary": "TIME-098: Calendar screen redesign (hero + Connect CTA)",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("Make calendar connection feel central to the AI per the mockup, instead of an "
              "unfinished 'connect on web' note."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Large calendar hero; 'Connect your calendar'; copy 'Let TimeSense avoid conflicts, "
                "find open focus blocks, and recommend the right task at the right time.'",
                "'Connect Calendar' button; 'Supported providers' card (Google / Apple rows); "
                "'Learn more about calendar privacy' link; connect actions = coming-soon alert with "
                "the privacy note",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["In-app calendar OAuth not implemented (coming-soon stub); removed the 'connect on web' text"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Settings/SettingsScreens.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Calendar screen matches the mockup; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-076 (Settings screens)."),
            divider(),
            h2("Next Ticket"), p("TIME-099: Privacy & Consent redesign."),
        ),
    },

    {
        "summary": "TIME-099: Privacy & Consent redesign (signal rows + data controls)",
        "labels": ["ios", "design", "privacy"],
        "description": doc(
            h2("Goal"),
            p("Turn the static bullets into settings-style rows with status labels per the mockup, "
              "making trust and permissions clear."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Banner: 'TimeSense only uses the data needed to plan your day. You're in control.'",
                "'Connected signals' card: Calendar / Health / Location / Audio rows (icon + name + "
                "subtitle + status). Statuses shown honestly as Off/Disabled until integrations exist",
                "'Data controls' card: Delete my data (wired to DELETE /privacy/account + sign out) "
                "and Export my data (coming-soon stub)",
                "Encrypted/never-sold footer note",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Signal statuses are not yet live consent toggles (shown Off/Disabled honestly); "
                "in-app data export is a stub",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Settings/SettingsScreens.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Signal rows + data controls render; Delete works; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-055 (privacy delete/export), TIME-076 (Settings)."),
            divider(),
            h2("Next Ticket"), p("TIME-100: Subscription redesign."),
        ),
    },

    {
        "summary": "TIME-100: Subscription redesign (Basic/Premium tiers)",
        "labels": ["ios", "design", "premium"],
        "description": doc(
            h2("Goal"),
            p("Make the subscription feel like a real product tier per the mockup, not a placeholder."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Current Plan card (Basic (Free) / Premium + icon); 'Basic includes' checklist; "
                "indigo 'Premium unlocks' card (AI best-next-action, integrations, weekly insights, "
                "proactive notifications, unlimited integrations); 'Upgrade to Premium' button; "
                "'Plans managed in the App Store'",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["StoreKit purchase still a follow-up (Upgrade is a placeholder action)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Settings/SettingsScreens.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Tiers render; is_premium reflected; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("Subscription status (TIME-076)."),
            divider(),
            h2("Next Ticket"), p("TIME-101: Settings home grouping."),
        ),
    },

    {
        "summary": "TIME-101: Settings home grouping (AI Planning / Integrations / Privacy / Account)",
        "labels": ["ios", "design", "ux"],
        "description": doc(
            h2("Goal"),
            p("Regroup the Settings home into structured, mature sections per the notes."),
            divider(),
            h2("Scope"),
            bullet_list([
                "AI Planning: Learned Patterns, Working Hours, Notification Timing",
                "Integrations: Calendar, Health (Apple Health connect)",
                "Privacy: Privacy & Consent, Delete My Data",
                "Account: Profile, Subscription, Appearance, About, Version",
                "Sign Out stays at the bottom",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Skipped rows for screens that don't exist yet (Recommendation Preferences, Notion, "
                "Location, separate Export) to avoid dead stubs",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Settings/SettingsView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Settings shows the four grouped sections; all rows work; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-076 (Settings screens)."),
            divider(),
            h2("Next Ticket"), p("TIME-102: Visual polish (contrast, chips, section headers)."),
        ),
    },

    {
        "summary": "TIME-102: Visual polish — light-mode contrast",
        "labels": ["ios", "design", "accessibility"],
        "description": doc(
            h2("Goal"),
            p("Improve light-mode contrast per the notes — some gray helper text was too washed "
              "out. (Card hierarchy, chips, and section headers were already addressed across the "
              "screen redesigns TIME-090-101.)"),
            divider(),
            h2("Scope"),
            bullet_list([
                "Darkened the TextSecondary token in light mode (#8A8A8E -> #5E5E66) for legible "
                "helper text; slightly brighter in dark mode (#98989D -> #A0A0A8). Global via the "
                "asset catalog",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Chips / card hierarchy / section-header wording were delivered in the per-screen "
                "redesigns (Now/Capture/Privacy/etc.)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Assets.xcassets/TextSecondary.colorset"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Secondary text is more legible in light mode; iOS build succeeds; verified via sign-in screenshot"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-073 (design tokens)."),
            divider(),
            h2("Next Ticket"), p("Screen redesign pass complete; back to the post-v1 backlog."),
        ),
    },

    {
        "summary": "TIME-103: Location-aware background arrival notifications",
        "labels": ["ios", "location", "notifications", "feature"],
        "description": doc(
            h2("Goal"),
            p("Make TimeSense location-aware: with 'Always' location it monitors geofences around "
              "the user's saved places and, when they arrive or leave, wakes in the background, "
              "fetches the best next task, and fires a local notification."),
            divider(),
            h2("Scope"),
            bullet_list([
                "LocationService (CoreLocation): permission step-up (WhenInUse -> Always), region "
                "monitoring of saved places, on enter/exit -> GET /now -> local notification; "
                "one-time fix for saving places",
                "AppDelegate (@UIApplicationDelegateAdaptor): Firebase configure + LocationService "
                "init on launch so geofence events are handled after background relaunch",
                "Info.plist: NSLocationWhenInUse / AlwaysAndWhenInUse usage strings + UIBackgroundModes "
                "location",
                "PlacesSettingsView (Settings -> Integrations -> Location & Places): enable location, "
                "save current location as Home/Work, list/remove places, shows real auth status",
                "Notification permission request; Privacy & Consent Location row reflects the real "
                "permission (While Using / Always / Off)",
                "Privacy: only user-chosen place centers are persisted (UserDefaults) — never a raw "
                "location track",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "The recommendation itself isn't yet location-informed server-side (arrival "
                "notification surfaces the current best task); sending place/commute signals to the "
                "backend is a follow-up",
                "No remote push / APNs (local notifications only); no home-location learning (user "
                "sets places)",
                "NEEDS ON-DEVICE TESTING — permissions, background wake, and geofencing can't be "
                "verified in the simulator/headless",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Core/Location/LocationService.swift (new), App/AppDelegate.swift (new), "
                "Features/Settings/PlacesSettingsView.swift (new)",
                "ios/TimeSense/App/TimeSenseApp.swift, Info.plist, Features/Settings/SettingsView.swift, "
                "SettingsScreens.swift; TimeSense.xcodeproj",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Location & Places screen requests permission and saves Home/Work geofences",
                "On geofence enter/exit the app fires a local notification with the best next task",
                "Privacy Location status reflects the real permission; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block(
                "xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense "
                "-destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"
            ),
            divider(),
            h2("Dependencies"),
            p("TIME-087 (Info.plist/device), the /now endpoint, AuthService background token."),
            divider(),
            h2("Next Ticket"),
            p("Send place/commute signals to the backend so the recommendation is location-informed; "
              "APNs remote push; home-location learning."),
        ),
    },

    {
        "summary": "TIME-104: Deep-link to iOS Settings for Always location",
        "labels": ["ios", "location", "ux", "bug"],
        "description": doc(
            h2("Goal"),
            p("Tapping 'Allow Always' did nothing because iOS silently no-ops requestAlwaysAuthorization "
              "(it only shows the upgrade prompt once and usually defers it). Guide the user to iOS "
              "Settings, where Always is reliably selectable."),
            divider(),
            h2("Scope"),
            bullet_list([
                "LocationService.openAppSettings() opens UIApplication.openSettingsURLString",
                "PlacesSettingsView permission card is state-based: notDetermined -> 'Enable "
                "location'; WhenInUse -> copy ('iOS won't prompt in-app') + 'Open iOS Settings'; "
                "denied -> 'Open iOS Settings'; always -> 'all set'",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Can't force the iOS Always prompt (Apple limitation); Settings deep-link is the reliable path"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Location/LocationService.swift, Features/Settings/PlacesSettingsView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["WhenInUse state shows an Open-iOS-Settings button + explainer; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-103 (location subsystem)."),
            divider(),
            h2("Next Ticket"), p("Location-informed recommendation server-side."),
        ),
    },

    {
        "summary": "TIME-105: Reliable geofence notifications (verify state, dedup stale events)",
        "labels": ["ios", "location", "bug"],
        "description": doc(
            h2("Goal"),
            p("Fix wrong/late arrival notifications (e.g. 'you left home' shown on arrival). iOS "
              "geofence events are laggy and arrive stale/out-of-order; trust the authoritative "
              "current state instead."),
            divider(),
            h2("Scope"),
            bullet_list([
                "On didEnter/didExit, call manager.requestState(for:) and act on didDetermineState "
                "(authoritative inside/outside), not the raw event",
                "Track lastRegionState per region and notify only on a real change (dedups a late "
                "'exit' that arrives while you're actually back inside)",
                "Seed state when a place is saved (no spurious alert), but NOT on relaunch (so a "
                "background-relaunch event still fires once)",
                "Radius 130 -> 150 m for a bit more reliability",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Can't remove iOS's inherent exit-detection latency (minutes; requires moving well "
                "beyond the boundary) — but events are now correct when they arrive",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Location/LocationService.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Arrival fires 'You are at X'; departure fires 'You left X'; stale/contradictory "
                "events are suppressed; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-103/104 (location subsystem)."),
            divider(),
            h2("Next Ticket"), p("Location-informed recommendation server-side."),
        ),
    },

    {
        "summary": "TIME-106: Geofence radius 150 -> 100m for sooner exit detection",
        "labels": ["ios", "location", "tuning"],
        "description": doc(
            h2("Goal"),
            p("A smaller radius crosses the exit boundary after less travel, so departures fire "
              "sooner. 100m is the practical reliability floor (iOS location accuracy ~50-150m); "
              "below that, jitter/false triggers appear. TIME-105's state-verification dedups any "
              "wobble."),
            divider(),
            h2("Scope"),
            bullet_list(["SavedPlace geofence radius 150 -> 100 m"]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["iOS exit hysteresis (~150-200m beyond the boundary) is inherent — radius only helps at the margin"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Location/LocationService.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["New places use a 100m geofence; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-103/105 (location)."),
            divider(),
            h2("Next Ticket"), p("Location-informed recommendation server-side."),
        ),
    },

    {
        "summary": "TIME-107: Save any number of named places (not just Home/Work)",
        "labels": ["ios", "location", "ux"],
        "description": doc(
            h2("Goal"),
            p("Let the user save arbitrary named places, not only the two fixed Home/Work buttons."),
            divider(),
            h2("Scope"),
            bullet_list([
                "PlacesSettingsView 'Add this location': a name text field + 'Save here' button, plus "
                "quick-pick chips (Home/Work/Gym/School/Errands) that prefill the name",
                "Name-aware icons on saved rows; save disabled until a name + a location fix exist",
                "Cap at iOS's 20-region limit (UI note + service guard); trims/validates the name",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No map picker (saves the current location); no per-place radius editing"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Settings/PlacesSettingsView.swift, Core/Location/LocationService.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["User can save multiple custom-named places; each gets a geofence; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-103 (location subsystem)."),
            divider(),
            h2("Next Ticket"), p("Location-informed recommendation server-side."),
        ),
    },

    {
        "summary": "TIME-108: Location shapes the recommendation (backend)",
        "labels": ["ios", "backend", "location", "recommendations", "brain"],
        "description": doc(
            h2("Goal"),
            p("Make the user's current place actually change the recommendation and show up as a live "
              "signal — not just drive notifications."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: user_location_states table (place_name nullable, is_home; one per user; "
                "migration) storing only the derived place NAME — never raw coordinates; "
                "UserLocationRepository (get_current with 6h staleness, upsert)",
                "POST /api/v1/location/place {place_name|null, is_home} upserts the current place",
                "Recommendation: /now (and /now/why) rerank — when out/away, errand/shopping/"
                "appointment/travel tasks surface; when home, they drop (you'd have to leave). "
                "Scorer order is the tiebreak",
                "Explainer: the Location signal + context now reflect the real place ('You're "
                "currently at Home' / 'out and about') instead of 'not connected'",
                "iOS: LocationService posts the place on each geofence transition (place on enter, "
                "null on exit) before fetching the best task",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No raw-coordinate storage (only the place name); no proximity-to-specific-errand "
                "matching yet (category-based nudge)",
                "Rerank is a deterministic +/-2 position nudge, not a full scorer rewrite",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend: models/user_location_state.py + migration + __init__, "
                "repositories/user_location_repository.py, api/v1/location.py + __init__, "
                "services/recommendation_explainer.py, api/v1/now.py, tests/test_location.py",
                "ios: Core/Location/LocationService.swift",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "POST /location/place stores the place; /now/why Location signal reflects it "
                "(available=true)",
                "Out and about -> an errand can outrank a focus task; at home it doesn't; full suite "
                "passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && alembic upgrade head && pytest tests/test_location.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-103 (location/geofences), TIME-089 (explanation signals), the scorer."),
            divider(),
            h2("Next Ticket"), p("Proximity-to-errand matching; commute-window signals; APNs remote push."),
        ),
    },

    {
        "summary": "TIME-109: Delete tasks from Today (long-press menu)",
        "labels": ["ios", "tasks", "ux"],
        "description": doc(
            h2("Goal"),
            p("Let the user remove tasks that are completed or no longer viable."),
            divider(),
            h2("Scope"),
            bullet_list([
                "TodayViewModel.deleteTask -> DELETE /api/v1/tasks/{id} (existing soft-delete) -> reload",
                "Smart Plan rows get a long-press context menu: 'Mark done' (if pending) + 'Delete task'",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Delete affordance only on Today for now (Now cards could get it later); soft-delete (recoverable server-side), no undo UI"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Today/TodayView.swift, TodayViewModel.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Long-pressing a Today task offers Delete; deleting removes it and reloads; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("DELETE /tasks/{id} (existing), TIME-092 (Today Smart Plan)."),
            divider(),
            h2("Next Ticket"), p("Delete on Now cards; swipe-to-delete; undo."),
        ),
    },

    {
        "summary": "TIME-110: Location always factored — errands never lead while home",
        "labels": ["backend", "ios", "location", "recommendations", "bug"],
        "description": doc(
            h2("Goal"),
            p("Bug: at home at 5pm, the app recommended 'Go to Walmart' (an errand you cannot do "
              "from home). Two causes: the app never told the backend it was home (no enter event "
              "fires when you're already there), and the at-home errand demotion was too soft."),
            divider(),
            h2("Scope"),
            bullet_list([
                "iOS: post the current place on EVERY geofence state determination (incl. seed/sync "
                "on save + relaunch), so the backend knows you're home even without leaving/returning; "
                "seeds never touch lastRegionState so they can't dedup a real event",
                "Backend: at home, errands sink below every non-errand (delta n+1) — they can never be "
                "the top pick while home; when out, errands still surface",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No true travel-time/geo-distance modelling yet (heuristic: at home => errands aren't "
                "doable now); if ALL tasks are errands, one still leads (nothing else to do)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "ios/TimeSense/Core/Location/LocationService.swift",
                "backend: api/v1/now.py, tests/test_location.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "A due-now high-priority errand does NOT lead while home (sinks below a home-doable "
                "task); still surfaces when out; suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_location.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-108 (location shapes recommendation)."),
            divider(),
            h2("Next Ticket"), p("TIME-111 swipe-to-delete; later: real travel-time modelling."),
        ),
    },

    {
        "summary": "TIME-111: Swipe-to-reveal Done + Delete on Today tasks",
        "labels": ["ios", "tasks", "ux"],
        "description": doc(
            h2("Goal"),
            p("Replace the long-press menu with a Mail-style left-swipe that reveals Done + Delete "
              "buttons on each Today task."),
            divider(),
            h2("Scope"),
            bullet_list([
                "SwipeableRow: custom drag gesture (Smart Plan is a card, not a List, so "
                ".swipeActions isn't available) revealing green Done (hidden if already done) + red "
                "Delete; snaps open/closed; tapping a button runs the action and closes",
                "Wired to markDone / deleteTask",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No full-swipe-to-commit; no undo toast; Today only"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Today/TodayView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Swiping a Today task left reveals Done + Delete; each works; vertical scroll still works; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-109 (delete), TIME-092 (Today)."),
            divider(),
            h2("Next Ticket"), p("Undo toast; swipe on Now cards."),
        ),
    },

    {
        "summary": "TIME-112: Deterministic recommendation engine — foundation (types + services)",
        "labels": ["backend", "recommendations", "brain", "architecture"],
        "description": doc(
            h2("Goal"),
            p("Rebuild the recommendation engine as a deterministic, scored decision system per "
              "recommendation-engine-build-spec.md. This ticket is phases 1-6 (foundation): types, "
              "time service, location service, maps skill wrapper, travel feasibility, context "
              "normalization. The LLM is NOT involved in selection (explanation comes later)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "app/services/recommendation/ package (Python port of the TS spec; no Any — full type hints)",
                "types.py: ActionType/ReasonCode/domains + Coordinates/TimeSnapshot/Place/TaskItem/"
                "CalendarEvent/HealthContext/UserContext/CandidateAction/Recommendation dataclasses",
                "time_service.get_time_snapshot(timezone, now=None) — tz-aware, testable",
                "location_service.get_user_location_snapshot(db, user) — from UserLocationState; safe when missing",
                "maps/: MapsProvider Protocol + NullMapsProvider (no API key) + MapsSkillService wrapper "
                "(geocode/search/resolve/travel) — returns None -> low-confidence, never invents",
                "travel_feasibility_service.calculate_travel_feasibility(...) with the spec formula + buffers",
                "normalize_context.normalize_context(raw) -> UserContext",
                "tests for each service + normalization",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No candidate generation/scoring/selection yet (TIME-113); no LLM; no real maps "
                "provider or coordinate storage (NullMapsProvider only); not wired into /now yet",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend/app/services/recommendation/** (new), backend/tests/test_recommendation_engine_foundation.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "get_time_snapshot returns tz-aware part-of-day/work-hours/weekend; deterministic with injected now",
                "NullMapsProvider yields None and the wrapper degrades gracefully (no invented distances)",
                "travel feasibility applies totalRequired = travel+onsite+after+buffer and fitsInFreeBlock",
                "normalize_context builds a typed UserContext from raw inputs; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_recommendation_engine_foundation.py -v"),
            divider(),
            h2("Dependencies"), p("Reuses usable_time/scheduling/task_duration/feedback/location repos."),
            divider(),
            h2("Next Ticket"), p("TIME-113: candidate generation + scoring + ranking/selection + tests."),
        ),
    },

    {
        "summary": "TIME-113: Recommendation engine — candidates, scoring, ranking/selection",
        "labels": ["backend", "recommendations", "brain", "architecture"],
        "description": doc(
            h2("Goal"),
            p("Phases 7-10 of the deterministic engine: generate candidate actions across domains, "
              "score them with the spec formula + penalties + hard rules, rank, select the best, and "
              "compute push eligibility. No LLM in selection."),
            divider(),
            h2("Scope"),
            bullet_list([
                "candidates/: calendar, task, location (maps+feasibility), health, routine, planning, "
                "context_switch, fallback generators + generate_candidate_actions(context, maps)",
                "scoring/: score_candidate (weighted formula, clamp 0-100), penalties (hard rules: "
                "meeting-soon vs deep work, short/long free block, poor sleep, night errands, "
                "trip-doesn't-fit, maps/location missing)",
                "selection/: rank_candidates, notification_policy (score>=75 & conf>=0.75), "
                "select_recommendation (best + alternatives + reason codes + confidence)",
                "feedback/apply_feedback_adjustments (accept/reject summary, pure); engine.run_engine orchestrator",
                "tests mapping the spec's required scenarios",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Not wired into /now yet (TIME-114); no LLM text; real maps provider still absent "
                "(location candidates stay low-confidence via NullMapsProvider)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend/app/services/recommendation/{candidates,scoring,selection,feedback}/**, engine.py; tests/test_recommendation_engine_selection.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Multi-domain candidates; deterministic scores; consistent ranking; graceful missing data",
                "Meeting-soon suppresses deep work; short block avoids deep work; long block + high-priority picks deep work",
                "Poor sleep favors recovery; night favors wind-down; errand that can't be confirmed feasible never leads",
                "Every recommendation has reason codes + confidence; push eligibility computed; tests pass",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_recommendation_engine_selection.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-112 (foundation)."),
            divider(),
            h2("Next Ticket"), p("TIME-114: wire the engine into /now (deterministic); then the LLM explanation layer."),
        ),
    },

    {
        "summary": "TIME-114: Integrate the deterministic engine into /now",
        "labels": ["backend", "recommendations", "brain", "integration"],
        "description": doc(
            h2("Goal"),
            p("Make the deterministic engine drive /now: build a real UserContext from the DB, run "
              "generate -> score -> rank -> select, and use the engine's ordering for best_task + "
              "alternatives. Replaces TaskScorer + _location_rerank."),
            divider(),
            h2("Scope"),
            bullet_list([
                "context_builder.build_user_context(db, user, tasks, now, usable) -> (UserContext, "
                "task_map): maps DB Task->TaskItem (priority/status/estimate/due + location-intent "
                "detection), time snapshot (work hours), location snapshot, health from latest "
                "sleep, prefs; free block from UsableTimeService",
                "maps factory get_maps_provider() -> NullMapsProvider (real provider in TIME-115)",
                "now.py _ranked_candidates now runs the engine and maps ranked task/location "
                "candidates back to Tasks (order preserved; safety-appends any unsurfaced task)",
                "Keep suppression (snooze/not-now), done-exclusion, wind-down moment, feasibility, "
                "greeting; /now/why unchanged (LLM explanation layer is the last phase)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No real maps provider yet (TIME-115); calendar events not wired (no integration) so "
                "meeting candidates stay dormant; /now/why still uses the existing explainer",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/recommendation/context_builder.py + maps/factory.py (new), "
                "app/api/v1/now.py; tests/test_now_engine.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Existing /now tests still pass (highest priority, overdue, done-excluded, "
                "unscheduled surfaces, not-now excluded, wind-down)",
                "best_task ordering now comes from the engine; an at-home errand with no travel data "
                "doesn't outrank a doable task; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_now.py tests/test_now_engine.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-112/113 (engine)."),
            divider(),
            h2("Next Ticket"), p("TIME-115: real maps provider + coordinate plumbing; then LLM explanation."),
        ),
    },

    {
        "summary": "TIME-115: Real maps provider + coordinate plumbing (light up location)",
        "labels": ["backend", "recommendations", "location", "maps"],
        "description": doc(
            h2("Goal"),
            p("Make the engine's location features real (not dormant): a Google maps provider behind "
              "the factory (gated by API key), and privacy-clean coordinate plumbing so travel "
              "feasibility can actually be computed."),
            divider(),
            h2("Scope"),
            bullet_list([
                "user_places table (name/place_type/lat/lng/is_preferred; per user) + repo + "
                "GET/PUT /api/v1/places to sync the app's saved places WITH coordinates — these are "
                "deliberate, user-named places (not a location trail)",
                "GoogleMapsProvider (httpx async: geocode, nearby search, distance/travel), gated by "
                "settings.google_maps_api_key; never raises; factory returns it when a key is set, "
                "else NullMapsProvider",
                "context_builder: preferred_places from user_places; travel ORIGIN = the saved "
                "place's coordinates when the user is currently at one (no live-coordinate storage)",
                "tests: places sync; context plumbing; engine end-to-end with a stub provider "
                "(preferred errand resolves + feasibility + leads when it fits / rejected when not)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No live raw-GPS storage (origin comes from a saved place); iOS place-sync is TIME-116; "
                "real Google calls need a key (tests use a stub); LLM explanation still later",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend: models/user_place.py + migration + __init__, repositories/user_place_repository.py, "
                "api/v1/places.py + __init__, services/recommendation/maps/google_provider.py + factory.py, "
                "context_builder.py, core/config.py; tests/test_places.py, test_maps_provider.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "PUT /places stores places w/ coords; GET returns them; context_builder exposes them "
                "as preferred_places + sets origin from the current saved place",
                "With a (stub) provider, a preferred errand that fits the free block leads; one that "
                "doesn't is rejected; no key → NullMapsProvider (unchanged behavior); suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && alembic upgrade head && pytest tests/test_places.py tests/test_maps_provider.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-112/113/114 (engine + integration)."),
            divider(),
            h2("Next Ticket"), p("TIME-116: iOS syncs saved places (with coords) to /places; then LLM explanation."),
        ),
    },

    {
        "summary": "TIME-116: iOS syncs saved places (with coordinates) to the backend",
        "labels": ["ios", "location", "maps"],
        "description": doc(
            h2("Goal"),
            p("Populate the backend user_places so the engine's location features actually work on "
              "device — the last piece before only an API key is needed."),
            divider(),
            h2("Scope"),
            bullet_list([
                "APIClient.put helper",
                "LocationService.syncPlaces() PUTs saved places (name, inferred place_type, lat/lng, "
                "is_preferred) to /api/v1/places; called after save/remove and on launch",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Real driving-time still needs a GOOGLE_MAPS_API_KEY on the backend; LLM explanation later"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/API/APIClient.swift, Core/Location/LocationService.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Saving/removing a place syncs the full set to /places; launch re-syncs; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-115 (/places + provider)."),
            divider(),
            h2("Next Ticket"), p("LLM explanation layer (final phase)."),
        ),
    },

    {
        "summary": "TIME-117: LLM explanation layer for the recommendation engine",
        "labels": ["backend", "recommendations", "llm"],
        "description": doc(
            h2("Goal"),
            p("Final engine phase: use the LLM ONLY to turn the already-selected recommendation into "
              "friendly text. The LLM never chooses a recommendation and never invents facts; on any "
              "failure we use deterministic fallback text. Also document GOOGLE_MAPS_API_KEY."),
            divider(),
            h2("Scope"),
            bullet_list([
                ".env.example + release_checklist: GOOGLE_MAPS_API_KEY",
                "llm/fallback_recommendation_text.py: deterministic LLMRecommendationText from the rec",
                "llm/generate_recommendation_text.py: strict prompt (context summary + reason codes + "
                "travel/place if present + tone) -> JSON {notification_title, notification_body, "
                "explanation}; parse; fallback on any error. Cannot change the action (returns text only)",
                "run_engine gains an optional gateway -> populates the recommendation's message/"
                "explanation via the LLM (deterministic without a gateway)",
                "tests: fallback shape; LLM parse success; LLM failure/garbage -> fallback; action "
                "unchanged regardless of LLM output",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "LLM does not select/rank; /now stays LLM-free (fast); /now/why keeps its existing "
                "structured explainer",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend/app/services/recommendation/llm/** (new), engine.py; backend/.env.example, "
                "docs/launch/release_checklist.md; tests/test_recommendation_engine_llm.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "generate_recommendation_text returns parsed text with a working gateway and falls "
                "back deterministically on failure; the selected action_type is never changed by the LLM",
                "run_engine(gateway=...) sets human text; full suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_recommendation_engine_llm.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-112/113 (engine), the LLM gateway."),
            divider(),
            h2("Next Ticket"), p("Optional: expose a full-engine /now/recommendation endpoint; adopt LLM text for push."),
        ),
    },

    {
        "summary": "TIME-118: /now/recommendation — full engine recommendation endpoint",
        "labels": ["backend", "recommendations", "api"],
        "description": doc(
            h2("Goal"),
            p("Expose the complete engine decision (any domain — not just the best task) with LLM "
              "text, so the app can surface cross-domain actions like prep-for-meeting / wind-down."),
            divider(),
            h2("Scope"),
            bullet_list([
                "GET /api/v1/now/recommendation: gather candidate tasks -> build_user_context -> "
                "run_engine (maps provider + LLM gateway) -> typed Recommendation response",
                "Recommendation carries related_entity_ids so a task-backed action exposes related_task_id",
                "Response: action_type/domain/title/message/explanation/confidence/score/urgency/"
                "estimated_minutes/reason_codes/eligible_for_push + destination_place/travel_estimate "
                "(when present) + alternatives + related_task_id",
                "Extract _gather_candidate_tasks shared with /now; store a RecommendationEvent audit",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No iOS adoption yet; /now unchanged (fast, task-centric); no push wiring"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend/app/api/v1/now.py, services/recommendation/{types.py,selection/select.py}; tests/test_now_recommendation.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "Endpoint returns a full recommendation with reason codes + confidence + push "
                "eligibility; a task-backed pick includes related_task_id; a non-task pick (e.g. "
                "wind_down at night) is returned with no task id; suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_now_recommendation.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-112..117 (engine + LLM layer)."),
            divider(),
            h2("Next Ticket"), p("iOS adoption of /now/recommendation; LLM text for push."),
        ),
    },

    {
        "summary": "TIME-119: iOS surfaces the cross-domain engine recommendation on Now",
        "labels": ["ios", "recommendations", "ux"],
        "description": doc(
            h2("Goal"),
            p("Adopt /now/recommendation in the app so users see the engine's full cross-domain "
              "decision (wind-down, prep-for-meeting, nearby errand…), not just the best task."),
            divider(),
            h2("Scope"),
            bullet_list([
                "NowViewModel: EngineRecommendation model + lazy fetch of /now/recommendation after "
                "the fast /now payload; suggestion published",
                "NowView: SuggestionCard (domain icon, 'TimeSense suggests', title, LLM message, "
                "confidence %, travel line when present) shown for a cross-domain action "
                "(related_task_id == nil); it supersedes the plain wind-down MomentCard",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Task-backed picks keep the existing best-action card (no duplicate); no push wiring; "
                "no actions on the suggestion card yet (informational)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Now/NowViewModel.swift, Features/Now/NowView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["A cross-domain recommendation renders as a SuggestionCard on Now; task picks unaffected; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-118 (/now/recommendation)."),
            divider(),
            h2("Next Ticket"), p("Actions on the suggestion card; LLM text for push notifications."),
        ),
    },

    {
        "summary": "TIME-120: LLM-phrased text for arrival push notifications",
        "labels": ["ios", "notifications", "recommendations", "llm"],
        "description": doc(
            h2("Goal"),
            p("Use the engine's LLM-phrased recommendation text for geofence arrival/departure "
              "notifications instead of the plain 'Best next: X' string — the concrete push surface "
              "that reaches users today (APNs not wired yet)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "LocationService.notifyBestTask now calls /now/recommendation (LLM title/body, "
                "deterministic fallback baked in) after posting the current place",
                "Real recommendation (domain != fallback) -> notification title = LLM title, body = "
                "LLM message; otherwise a light 'You're at <place>' acknowledgement (no task-nagging)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "No backend APNs remote push yet; backend scheduled check-ins unchanged; no new endpoint "
                "(reuses /now/recommendation)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Location/LocationService.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "On geofence enter/exit the local notification uses the engine's LLM text; when there's "
                "nothing worthwhile it shows a light acknowledgement; iOS build succeeds",
            ]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-117 (LLM layer), TIME-118 (/now/recommendation), TIME-103/105 (geofence notifications)."),
            divider(),
            h2("Next Ticket"), p("Backend APNs remote push using eligible_for_push + LLM text."),
        ),
    },

    {
        "summary": "TIME-121: APNs remote push — backend (device tokens, sender, decision service)",
        "labels": ["backend", "notifications", "push", "recommendations", "infra"],
        "description": doc(
            h2("Goal"),
            p("Backend for proactive push: store device tokens, send via APNs (token/JWT auth, "
              "gated by credentials), and a decision service that pushes the engine's LLM text only "
              "when eligible_for_push and outside cooldown. iOS registration is TIME-122."),
            divider(),
            h2("Scope"),
            bullet_list([
                "config: apns_key_id/team_id/private_key(.p8)/bundle_id/use_sandbox (empty → disabled)",
                "models: device_tokens (user_id, token unique, platform) + push_notifications "
                "(action_type, title, body, sent_at — cooldown + audit) + migration",
                "repos + PUT/DELETE /api/v1/devices to register/unregister a token",
                "push sender: PushSender Protocol + NullPushSender + ApnsPushSender (ES256 JWT, "
                "HTTP/2, gated on creds + h2) + factory",
                "ProactivePushService.push_for_user: engine (with gateway) → require eligible_for_push "
                "→ 45-min cooldown (same action_type suppressed; high-urgency override) → send LLM "
                "title/body to each device → record",
                "Celery task scan_and_push over users with device tokens + beat schedule; add h2 dep",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "iOS registration/entitlement is TIME-122; real sending needs Apple creds + a valid "
                "token (tests use a stub sender); no rich payloads/actions yet",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend: core/config.py; models/{device_token,push_notification}.py + migration + "
                "__init__; repositories/*; api/v1/devices.py + __init__; services/push/**; "
                "workers/push_tasks.py + celery_app.py; requirements; tests/test_push*.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "PUT /devices stores a token; push service sends via a stub sender ONLY when "
                "eligible_for_push and not in cooldown; same-type within 45 min suppressed; "
                "high-urgency overrides; no creds → NullPushSender (no-op); suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && alembic upgrade head && pytest tests/test_devices.py tests/test_push_service.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-112..118 (engine + /now/recommendation), TIME-117 (LLM text)."),
            divider(),
            h2("Next Ticket"), p("TIME-122: iOS registers for remote push + sends the device token."),
        ),
    },

    {
        "summary": "TIME-122: iOS registers for APNs remote push + sends device token",
        "labels": ["ios", "notifications", "push"],
        "description": doc(
            h2("Goal"),
            p("Wire the app for remote push so the TIME-121 backend can reach it: register, receive "
              "the APNs device token, and sync it to /api/v1/devices."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Info.plist: add 'remote-notification' to UIBackgroundModes",
                "Push Notifications entitlement (aps-environment) + CODE_SIGN_ENTITLEMENTS",
                "AppDelegate: registerForRemoteNotifications on launch; "
                "didRegisterForRemoteNotificationsWithDeviceToken -> hex token -> PUT /api/v1/devices; "
                "didFailToRegister logs",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Real delivery needs the backend APNs creds (TIME-121) + a push-enabled provisioning "
                "profile; can't be verified in the simulator",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/App/AppDelegate.swift, Info.plist, TimeSense.entitlements (new); TimeSense.xcodeproj"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["App registers for remote notifications and PUTs the hex token to /devices on receipt; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-121 (/devices + push backend)."),
            divider(),
            h2("Next Ticket"), p("End-to-end push test on device once Apple creds are set."),
        ),
    },

    {
        "summary": "TIME-123: Celery beat service + 'send test push now' endpoint",
        "labels": ["backend", "notifications", "push", "devx"],
        "description": doc(
            h2("Goal"),
            p("Make the proactive-push chain runnable and verifiable: a docker-compose beat service "
              "(the scheduler) and an authenticated endpoint that pushes to the caller's own devices "
              "immediately, bypassing the eligibility/cooldown gates."),
            divider(),
            h2("Scope"),
            bullet_list([
                "docker-compose: add a 'beat' service (celery ... beat) alongside the worker",
                "ProactivePushService.send_test: send to the user's device tokens NOW — engine text "
                "or a canned {title, body} override — bypassing eligible_for_push + cooldown; record it",
                "POST /api/v1/devices/test-push (current user): returns apns_available + delivered + "
                "the title/body sent (or reason=no_device)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Still needs real APNs creds + a device token to actually deliver; test-push only "
                "targets the caller's own devices (no cross-user)",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["docker-compose.yml; backend: services/push/push_service.py, api/v1/devices.py; tests/test_push_service.py, test_devices.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "beat service defined; send_test delivers via a stub sender even for a non-eligible "
                "recommendation and honors title/body override; endpoint returns apns_available/"
                "delivered; no device → reason; suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_push_service.py tests/test_devices.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-121/122 (push backend + iOS registration)."),
            divider(),
            h2("Next Ticket"), p("End-to-end on-device verification once APNS_* + a push provisioning profile are set."),
        ),
    },

    {
        "summary": "TIME-124: Capture keyboard can't be dismissed (traps the user)",
        "labels": ["ios", "bug", "capture", "ux"],
        "description": doc(
            h2("Goal"),
            p("Fix a trap on Capture: the multi-line TextField (axis: .vertical) makes Return insert "
              "a newline, and there was no Done button / tap / swipe to dismiss — so the keyboard "
              "covered the Capture button and tab bar with no way out."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Keyboard toolbar 'Done' button (sets isInputFocused=false)",
                "ScrollView.scrollDismissesKeyboard(.interactively) so swiping down dismisses it",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Keep the multi-line field (Return stays a newline); no submit-on-return change"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Capture/CaptureView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["The keyboard can be dismissed via Done or a downward swipe; Capture button + tabs reachable again; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-094 (Capture redesign)."),
            divider(),
            h2("Next Ticket"), p("None."),
        ),
    },

    {
        "summary": "TIME-125: Fix on-device regressions (location/push 500s + empty Today at night)",
        "labels": ["backend", "bug", "migrations", "timeline"],
        "description": doc(
            h2("Goal"),
            p("Two production-only bugs found via on-device testing (both invisible to the SQLite "
              "create_all test setup)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "BUG 1: the hand-written migrations for user_location_states/user_places/"
                "device_tokens/push_notifications omitted the created_at/updated_at server_default "
                "the TimestampMixin expects, so every INSERT 500'd on Postgres (NotNullViolation) — "
                "blocking location posting, device registration, and place sync. Fix: migration "
                "y5z6a7b8c9d0 adds SET DEFAULT now() on all four tables",
                "BUG 2: /timeline/today only included untimed pending tasks when the requested date "
                "== server UTC date; a late-evening user's client sends its LOCAL date (a day behind "
                "UTC), so the branch was skipped -> empty 'your day is open'. Fix: include untimed "
                "when the date is within a day of UTC-today",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "Profile timezone is still 'UTC' (app doesn't send the real tz) — separate follow-up; "
                "capture date-parsing (why 'Walmart today at 5pm' wasn't scheduled) — separate",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: migrations/versions/y5z6a7b8c9d0_*.py, api/v1/timeline.py; tests/test_timeline.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "INSERTs into the four tables succeed on Postgres; /timeline/today returns untimed "
                "pending tasks even when the client date lags UTC; suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && alembic upgrade head && pytest tests/test_timeline.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-108/115/121 (the tables); TIME-092 (Today)."),
            divider(),
            h2("Next Ticket"), p("Send the device's real timezone; capture date-parsing reliability."),
        ),
    },

    {
        "summary": "TIME-126: Register for APNs unconditionally (token was never obtained)",
        "labels": ["ios", "notifications", "push", "bug"],
        "description": doc(
            h2("Goal"),
            p("Diagnosis showed the app never called PUT /devices — it gated registerForRemote"
              "Notifications behind the notification-permission grant, so no permission meant no "
              "token, ever. Register unconditionally (the token is separate from alert permission)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "AppDelegate: call registerForRemoteNotifications() unconditionally on launch; "
                "request alert permission separately",
                "Log the token on success + a clear failure message (visible in Xcode console)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Getting a token still requires the Push Notifications capability on the provisioning profile (Apple/Xcode-side)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/App/AppDelegate.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["App calls registerForRemoteNotifications on every launch regardless of permission; on token receipt it PUTs to /devices and logs it; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-121/122/125."),
            divider(),
            h2("Next Ticket"), p("End-to-end on-device push once the Push capability is provisioned + Celery runs."),
        ),
    },

    {
        "summary": "TIME-127: Loud launch + registration markers to confirm fresh build",
        "labels": ["ios", "notifications", "push", "devx"],
        "description": doc(
            h2("Goal"),
            p("Diagnostic: the phone never registers for push and the console shows no ✅/❌, which "
              "means a stale binary or a detached console. Add unmissable launch/registration prints "
              "so the running build is unambiguous."),
            divider(),
            h2("Scope"),
            bullet_list([
                "AppDelegate.didFinishLaunching logs a loud '🚀 build TIME-127' marker",
                "Logs before registerForRemoteNotifications() and the notification-permission result",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No behavior change; pure logging to disambiguate stale-build vs registration failure"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/App/AppDelegate.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["On launch from Xcode the console prints the 🚀 marker, the registerForRemoteNotifications log, and then ✅/❌; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-126."),
            divider(),
            h2("Next Ticket"), p("Once the token registers: confirm backend receipt + fire a test push."),
        ),
    },

    {
        "summary": "TIME-128: Disable Firebase delegate swizzling so APNs token callback fires",
        "labels": ["ios", "notifications", "push", "firebase", "bug"],
        "description": doc(
            h2("Goal"),
            p("Console proved registration is called on a fresh build (🚀/📡/granted=true) but neither "
              "didRegister nor didFail fired — FirebaseAuth's UIApplicationDelegate swizzling was "
              "intercepting didRegisterForRemoteNotificationsWithDeviceToken and not forwarding it to "
              "our @UIApplicationDelegateAdaptor delegate."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Info.plist: FirebaseAppDelegateProxyEnabled = NO (we use neither FCM nor phone-auth, "
                "so disabling the proxy is safe and lets our delegate receive the APNs token)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Getting a token still requires the Push capability on the provisioning profile (paid Apple account)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Info.plist"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["After a fresh build, didRegisterForRemoteNotificationsWithDeviceToken fires (✅ token) or didFail fires (❌); key present in the built Info.plist; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-122/126/127."),
            divider(),
            h2("Next Ticket"), p("Confirm backend receives the token + fire a test push."),
        ),
    },

    {
        "summary": "TIME-129: Show notifications while the app is in the foreground",
        "labels": ["ios", "notifications", "push", "ux"],
        "description": doc(
            h2("Goal"),
            p("iOS suppresses banners for foreground apps unless the app presents them, which looked "
              "like 'the push never arrived' during testing. Present them explicitly."),
            divider(),
            h2("Scope"),
            bullet_list([
                "AppDelegate conforms to UNUserNotificationCenterDelegate; set as the center delegate",
                "willPresent returns [.banner, .sound, .badge] so pushes + local (geofence) "
                "notifications show even with the app open",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No tap-handling / deep-link routing yet"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/App/AppDelegate.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["A push received while the app is foregrounded shows a banner; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-128 (push delivery working)."),
            divider(),
            h2("Next Ticket"), p("Gate debug prints behind #if DEBUG; notification tap deep-links."),
        ),
    },

    {
        "summary": "TIME-130: Gate push debug logs behind #if DEBUG",
        "labels": ["ios", "cleanup", "notifications"],
        "description": doc(
            h2("Goal"),
            p("The launch/registration/token diagnostics were invaluable but shouldn't log in "
              "production. Route them through a debug-only helper."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Add debugLog(_:) — an @autoclosure helper that compiles to a no-op in release (#if DEBUG)",
                "Replace the raw print() calls in AppDelegate (launch marker, register, permission, "
                "token, fail, foreground-present) with debugLog",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No behavior change; the device token is still PUT to the backend regardless of logging"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/App/AppDelegate.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Diagnostics print in Debug builds and are absent in Release; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-127/128/129."),
            divider(),
            h2("Next Ticket"), p("Notification tap deep-linking; per-user push timing preferences."),
        ),
    },

    {
        "summary": "TIME-131: Apple Calendar (EventKit) — synced-events store + engine wiring",
        "labels": ["backend", "calendar", "recommendations"],
        "description": doc(
            h2("Goal"),
            p("Backend half of the Apple Calendar feature: a place to store the events the iOS app "
              "reads from EventKit, an endpoint to sync them, and wiring so the engine factors them "
              "(meeting prep/join/leave, free-block from real events)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "synced_calendar_events table (user_id, source, external_id, title, starts_at, "
                "ends_at, location, all_day; unique per user+source+external_id) + migration WITH "
                "created_at/updated_at server_default (per the TIME-125 lesson)",
                "SyncedCalendarEventRepository (replace_for_source, list_window)",
                "PUT /api/v1/calendar/synced — the app pushes its EventKit events (replace-all for the "
                "source); GET /api/v1/calendar/synced/today",
                "context_builder feeds synced events into the engine's calendar_context (current/next "
                "event, minutes-until, free block, meeting density) so calendar candidates fire",
                "tests: sync + engine produces a prepare_for_meeting when a meeting is imminent",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list([
                "iOS EventKit read/permission/sync (TIME-132); showing events as blocks on Today + "
                "the write-back path (TIME-133); Google server-side OAuth stays untouched",
            ]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list([
                "backend: models/synced_calendar_event.py + migration + __init__, "
                "repositories/synced_calendar_event_repository.py, api/v1/calendar.py, "
                "services/recommendation/context_builder.py; tests/test_calendar_sync.py",
            ]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "PUT /calendar/synced stores events; context_builder exposes them; with an imminent "
                "meeting the engine recommends prepare_for_meeting; suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && alembic upgrade head && pytest tests/test_calendar_sync.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-112..114 (engine), TIME-125 (migration-defaults lesson)."),
            divider(),
            h2("Next Ticket"), p("TIME-132: iOS EventKit read + permission + sync to /calendar/synced."),
        ),
    },

    {
        "summary": "TIME-132: iOS Apple Calendar (EventKit) connect + sync",
        "labels": ["ios", "calendar", "eventkit"],
        "description": doc(
            h2("Goal"),
            p("iOS half: request calendar access (EventKit), read upcoming events, and sync them to "
              "the backend so the engine factors the schedule. Native permission — no OAuth."),
            divider(),
            h2("Scope"),
            bullet_list([
                "CalendarSyncService (EventKit): requestFullAccessToEvents (iOS17+) / requestAccess; "
                "read now-12h..now+36h; PUT /api/v1/calendar/synced; syncIfAuthorized + disconnect",
                "CalendarSettingsView rewired: Connect Apple Calendar -> permission -> sync; shows "
                "connected + event count, Sync now, Disconnect, and Open-Settings when denied",
                "Info.plist: NSCalendarsFullAccessUsageDescription + NSCalendarsUsageDescription",
                "Re-sync on app launch (AppDelegate) when authorized",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Showing events as blocks on Today + write-back to the calendar (TIME-133); needs on-device test for the permission prompt"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Calendar/CalendarSyncService.swift (new), Features/Settings/SettingsScreens.swift, App/AppDelegate.swift, Info.plist; TimeSense.xcodeproj"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Connect requests calendar access and syncs events; status/counts shown; re-syncs on launch; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-131 (/calendar/synced + engine wiring)."),
            divider(),
            h2("Next Ticket"), p("TIME-133: show calendar events on Today; write events to the calendar with approval."),
        ),
    },

    {
        "summary": "TIME-133: Show synced calendar events on Today",
        "labels": ["ios", "calendar", "ux"],
        "description": doc(
            h2("Goal"),
            p("Make the connected calendar visible: today's events appear on the Today screen "
              "(read-only), not just feeding the engine."),
            divider(),
            h2("Scope"),
            bullet_list([
                "CalendarSyncService exposes @Published events (CalEvent) populated on sync",
                "TodayView 'On your calendar' section: read-only event rows (title, time range, "
                "location) for today's timed events; syncs when the tab appears",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Write-back (add events to the calendar with approval) is TIME-134; no interleaving events into the task groups (separate section)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Calendar/CalendarSyncService.swift, Features/Today/TodayView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Today shows an 'On your calendar' card with today's timed events when connected; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-131/132 (calendar sync)."),
            divider(),
            h2("Next Ticket"), p("TIME-134: write events to the calendar with approval (EventKit)."),
        ),
    },

    {
        "summary": "TIME-134: Calendar write-back — add a task to the calendar (with approval)",
        "labels": ["ios", "calendar", "eventkit"],
        "description": doc(
            h2("Goal"),
            p("Let TimeSense schedule a task onto the calendar, honoring the 'calendar writes require "
              "user approval' rule via Apple's native event editor."),
            divider(),
            h2("Scope"),
            bullet_list([
                "CalendarSyncService: ensureWriteAccess() + makeDraftEvent + expose eventStore",
                "EventEditorView (EKEventEditViewController wrapper) — the native review/confirm UI",
                "Today: long-press a task -> 'Add to Calendar' -> pre-filled editor (title, "
                "task's scheduled time or now, estimated duration); on save, re-sync",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No auto-scheduling/free-slot picking (user confirms the time in the editor); no engine-initiated event creation yet"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Calendar/{CalendarSyncService,EventEditorView}.swift, Features/Today/TodayView.swift; TimeSense.xcodeproj"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Long-press a Today task -> Add to Calendar -> native editor pre-filled -> Add creates the event and re-syncs; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-131/132/133 (calendar read + sync + display)."),
            divider(),
            h2("Next Ticket"), p("Engine-suggested time blocks; auto-schedule into free slots (with approval)."),
        ),
    },

    {
        "summary": "TIME-135: Engine-suggested time blocks (find a free slot, approve)",
        "labels": ["backend", "ios", "calendar", "scheduling"],
        "description": doc(
            h2("Goal"),
            p("When adding a task to the calendar, the engine proposes the earliest free block that "
              "avoids the user's meetings and scheduled tasks and respects working hours; the user "
              "approves the time in the native editor."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend GET /api/v1/tasks/{id}/suggested-slot: SchedulingService.find_slot over busy "
                "= other scheduled tasks + timed synced calendar events; returns fits/start/end/"
                "duration/message",
                "iOS: TodayViewModel.suggestedSlot; the Today 'Find a time & add to calendar' action "
                "fetches the slot and pre-fills the EKEventEditViewController with it (falls back to now)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Today-only window (no roll to tomorrow yet); no automatic scheduling without the approval editor"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: api/v1/tasks.py; tests/test_suggested_slot.py; ios: Features/Today/{TodayView,TodayViewModel}.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Suggested slot starts at/after a blocking meeting; unknown task -> 404; Add-to-Calendar pre-fills the suggested time; suite + iOS build pass"]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_suggested_slot.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-084 (SchedulingService), TIME-131 (calendar events), TIME-134 (editor)."),
            divider(),
            h2("Next Ticket"), p("Roll suggestions to tomorrow; engine proactively offers to block time for high-priority tasks."),
        ),
    },

    {
        "summary": "TIME-136: Roll suggested time blocks to the next few days when today is full",
        "labels": ["backend", "scheduling", "calendar"],
        "description": doc(
            h2("Goal"),
            p("When no free slot fits today, the suggested-slot search rolls forward to the next few "
              "days (respecting each day's working window + calendar) and reports which day."),
            divider(),
            h2("Scope"),
            bullet_list([
                "SchedulingService: _earliest_in_window helper; find_slot_multiday(now, duration, "
                "busy, tz, not_before, max_days) that searches today..+N days",
                "/tasks/{id}/suggested-slot uses find_slot_multiday over a 3-day horizon (busy = "
                "other scheduled tasks + timed calendar events across the horizon) and returns a "
                "'day' label (today/tomorrow/later this week)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["iOS unchanged (uses start/end; native editor shows the date); horizon fixed at 3 days"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: services/scheduling_service.py, api/v1/tasks.py; tests/test_suggested_slot.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["When today's window is full/past, a suggestion rolls to a later day with a day label; suite passes"]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_suggested_slot.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-135 (suggested-slot)."),
            divider(),
            h2("Next Ticket"), p("TIME-137: proactively offer to block time for high-priority tasks (push)."),
        ),
    },

    {
        "summary": "TIME-137: Proactively offer to block time for high-priority tasks",
        "labels": ["backend", "notifications", "push", "scheduling"],
        "description": doc(
            h2("Goal"),
            p("When a high-priority or overdue task is unscheduled, proactively push an offer to block "
              "the next free slot for it (avoiding the user's calendar), so nothing important slips."),
            divider(),
            h2("Scope"),
            bullet_list([
                "ProactivePushService.offer_time_block_for_user: pick the top high-priority/overdue "
                "UNSCHEDULED task, find a free slot (multiday, avoids calendar + scheduled tasks), "
                "push 'Block time for X? Free <day> at <time>', honoring the shared 45-min cooldown; "
                "record as action_type offer_time_block",
                "Celery scan: if no eligible recommendation, try the time-block offer",
                "POST /api/v1/devices/test-offer to fire one on demand (bypasses cooldown)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Tapping the push doesn't yet deep-link into the schedule editor; offer is one per cooldown window"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: services/push/push_service.py, workers/push_tasks.py, api/v1/devices.py; tests/test_push_service.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list([
                "High-priority unscheduled task + free slot -> offer pushed (collapse_id offer_time_block); "
                "no suitable task -> no offer; cooldown honored; test-offer works; suite passes",
            ]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_push_service.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-121 (push), TIME-135/136 (suggested slots)."),
            divider(),
            h2("Next Ticket"), p("Notification-tap deep-linking to schedule; profile timezone; capture date-parsing."),
        ),
    },

    {
        "summary": "TIME-138: Notification-tap deep-linking",
        "labels": ["ios", "backend", "notifications", "ux"],
        "description": doc(
            h2("Goal"),
            p("Tapping a notification routes the user to the relevant action instead of just opening "
              "the app — an 'offer_time_block' push opens the pre-filled scheduler; others open Now."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: push sender accepts a data dict merged into the APNs payload; offer push "
                "carries {type: offer_time_block, task_id, task_title}; recommendation push carries "
                "{type: recommendation, task_id?}",
                "iOS: DeepLinkRouter + AppDelegate didReceive (tap) -> route; MainTabView switches "
                "tab; TodayView on .scheduleTask presents the pre-filled scheduler",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Geofence local notifications route to Now (default); no per-notification action buttons"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: services/push/{sender,push_service}.py; ios: App/{DeepLinkRouter,AppDelegate,MainTabView}.swift, Features/Today/TodayView.swift; TimeSense.xcodeproj; tests updated"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Tapping the offer push opens Today with the scheduler pre-filled for that task; push data flows through the sender; suite + iOS build pass"]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_push_service.py -v ; xcodebuild build ..."),
            divider(),
            h2("Dependencies"), p("TIME-135/137 (scheduler + offer push)."),
            divider(),
            h2("Next Ticket"), p("Profile timezone; capture date-parsing."),
        ),
    },

    {
        "summary": "TIME-139: App sends the device timezone (fix UTC-stuck profile)",
        "labels": ["ios", "bug", "timezone"],
        "description": doc(
            h2("Goal"),
            p("The profile timezone was stuck on UTC because the app never sent it — degrading "
              "greetings, 'today' boundaries, working-hours windows, and scheduling. Auto-sync the "
              "device timezone."),
            divider(),
            h2("Scope"),
            bullet_list([
                "MainTabView: on launch PATCH /api/v1/users/me/profile with TimeZone.current.identifier "
                "(endpoint + schema already support timezone)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No manual timezone picker; timeline ±1-day tolerance (TIME-125) stays as a safety net"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/App/MainTabView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["On launch the app updates the profile timezone to the device's; greetings/scheduling use it; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("PATCH /users/me/profile (existing)."),
            divider(),
            h2("Next Ticket"), p("TIME-140: capture date-parsing reliability."),
        ),
    },

    {
        "summary": "TIME-140: Capture parses specific times into scheduled_start",
        "labels": ["backend", "capture", "bug"],
        "description": doc(
            h2("Goal"),
            p("Captured tasks with a specific clock time ('today at 5pm') lost their slot — the LLM "
              "prompt + rule-based parser only produced due_at. Extract a time as scheduled_start, "
              "and run the deterministic parser alongside the LLM to fill gaps."),
            divider(),
            h2("Scope"),
            bullet_list([
                "parse_datetime -> (scheduled_start, due_at, title): specific time -> scheduled_start "
                "(given/today date), date-only -> due_at (end of day)",
                "capture_service: LLM prompt gains scheduled_start with clear time-vs-date rules; the "
                "deterministic parser always runs and fills any field the LLM leaves null; set "
                "scheduled_end = start + estimated (or 30 min)",
                "updated parser tests to the 3-tuple + scheduled_start assertions",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No recurring-event parsing; capture endpoint auto-schedule for untimed tasks unchanged"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: services/capture_date_parser.py, services/capture_service.py; tests/test_capture_date_parser.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["'Go to Walmart today at 5pm' -> scheduled_start 17:00 local + a block; date-only -> due_at; suite passes"]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_capture_date_parser.py tests/test_capture.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-072 (parser), TIME-139 (real tz makes local times correct)."),
            divider(),
            h2("Next Ticket"), p("Recurring/relative phrases (in 2 hours, every Monday); on-device capture verification."),
        ),
    },

    {
        "summary": "TIME-141: 'Why this recommendation' Calendar signal — real free time (not the 240 cap)",
        "labels": ["backend", "recommendations", "calendar", "bug"],
        "description": doc(
            h2("Goal"),
            p("The Calendar signal almost always said '240 minutes free before the end of your day' — "
              "the UsableTimeService 4-hour cap, measured to midnight, ignoring the user's calendar. "
              "Make free time genuinely reflect calendar events + scheduled tasks within working hours."),
            divider(),
            h2("Scope"),
            bullet_list([
                "recommendation_explainer._free_and_next: free time until the next commitment (task OR "
                "calendar event) or the end of the WORKING day, with busy = scheduled tasks + timed "
                "calendar events, via SchedulingService (working-hours + tz aware)",
                "Replaces UsableTimeService(240-cap, tasks-only, to-midnight) in the explainer; "
                "phrasing 'before your workday ends'; confidence uses the real free time",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["/now usable_minutes path unchanged; location + time-of-day signals already derived; no all-day event handling change"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: services/recommendation_explainer.py; tests/test_calendar_sync.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["With a meeting in 40 min the Calendar signal names it and shows ~40 min free, not 240; suite passes"]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_calendar_sync.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-131 (calendar events), TIME-084 (SchedulingService)."),
            divider(),
            h2("Next Ticket"), p("Make /now usable_minutes calendar-aware too; routine-aware time-of-day."),
        ),
    },

    {
        "summary": "TIME-142: Now 'analyzed your day' banner ticks (not frozen at 'just now')",
        "labels": ["ios", "now", "ux"],
        "description": doc(
            h2("Goal"),
            p("The 'Re-evaluated just now' text never appeared to change (no timer; and lastLoaded "
              "resets each visit). Make it tick so elapsed time counts up while viewing."),
            divider(),
            h2("Scope"),
            bullet_list([
                "AnalysisBanner: 15s Timer updates a @State now; reevaluated computes from lastLoaded "
                "to now; reset the clock on new load (onChange lastLoaded)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Re-fetch cadence unchanged (opening Now still re-evaluates → resets to 'just now')"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Features/Now/NowView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["The banner counts up over time while the Now screen stays open; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-090 (Now redesign)."),
            divider(),
            h2("Next Ticket"), p("Engine: surface imminent calendar appointments over stale tasks."),
        ),
    },

    {
        "summary": "TIME-143: Surface upcoming appointments; don't recommend errands right before one",
        "labels": ["backend", "recommendations", "calendar", "bug"],
        "description": doc(
            h2("Goal"),
            p("Reported: at 1:53pm the top pick was a gym task scheduled for 8am, while a 2:40pm "
              "acupuncture appointment sat on the calendar. Cause: calendar candidates only fired "
              "<=15 min out (so a 45-min appointment was never surfaced), and a maps-resolved gym "
              "errand that 'fit' the 45-min pre-appointment block scored top."),
            divider(),
            h2("Scope"),
            bullet_list([
                "calendar_candidates: surface the next event within ~an hour — join(<=2), prep(<=20), "
                "leave-for-located(<=30), and a 'Coming up' candidate up to 60min (located)/75min "
                "with urgency scaled by proximity",
                "penalties: a location errand with a commitment <=60 min away is penalized (don't "
                "start a trip right before an appointment)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No maps travel-time-based leave timing yet; engine doesn't yet know a task's scheduled_start (the gym's 8am slot is invisible to it)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: services/recommendation/candidates/calendar_candidates.py, scoring/penalties.py; tests/test_calendar_sync.py"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["An appointment ~45 min out is the top recommendation (calendar domain), not an errand; suite passes"]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_calendar_sync.py -v"),
            divider(),
            h2("Dependencies"), p("TIME-131 (calendar events in the engine)."),
            divider(),
            h2("Next Ticket"), p("Give the engine tasks scheduled_start awareness; travel-time-based leave timing via maps."),
        ),
    },

    {
        "summary": "TIME-144: Voice capture (on-device speech-to-text)",
        "labels": ["ios", "capture", "voice"],
        "description": doc(
            h2("Goal"),
            p("Let the user speak a task on the Capture screen. Transcribe on-device (Speech "
              "framework) into the existing capture text field — no backend change, and no raw audio "
              "stored (honors the raw-audio-opt-in rule)."),
            divider(),
            h2("Scope"),
            bullet_list([
                "VoiceCaptureService (Speech + AVAudioEngine): request mic + speech permission; live "
                "partial transcription; on-device recognition when supported; start/stop",
                "CaptureView: mic button toggles recording (pulsing/stop state); live transcript fills "
                "the input field; error/permission messaging. Replaces the coming-soon stub",
                "Info.plist: NSMicrophoneUsageDescription + NSSpeechRecognitionUsageDescription",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No raw-audio storage or upload; no wake word / background listening; transcript still goes through the normal capture parse (POST /capture)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Capture/VoiceCaptureService.swift (new), Features/Capture/CaptureView.swift, Info.plist; TimeSense.xcodeproj"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Tapping the mic requests permission, records, live-transcribes into the field, and stops; the text captures normally; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-094 (Capture redesign)."),
            divider(),
            h2("Next Ticket"), p("Optional raw-audio opt-in for review; multi-language."),
        ),
    },

    {
        "summary": "TIME-145: Audio-reactive waveform while voice-capturing",
        "labels": ["ios", "capture", "voice", "ux"],
        "description": doc(
            h2("Goal"),
            p("Show a live waveform in the Capture hero while recording, reacting to mic loudness, so "
              "voice capture feels alive and gives clear 'I'm listening' feedback."),
            divider(),
            h2("Scope"),
            bullet_list([
                "VoiceCaptureService: publish a normalized RMS level (0..1) from the audio tap; reset on stop",
                "CaptureView: WaveformView (7 bars, heights scale with level + per-bar jitter, idle pulse); "
                "hero shows the waveform while recording, static icon otherwise",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No FFT/frequency bars; no waveform when idle"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Capture/VoiceCaptureService.swift, Features/Capture/CaptureView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["While recording, the hero shows a waveform that visibly reacts to speaking volume; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-144 (voice capture)."),
            divider(),
            h2("Next Ticket"), p("Optional auto-submit on stop; raw-audio opt-in review."),
        ),
    },

    {
        "summary": "TIME-146: Fix voice capture — continuous dictation (no wipe) + live waveform",
        "labels": ["ios", "capture", "voice", "bug"],
        "description": doc(
            h2("Goal"),
            p("Reported: no waveform animation while speaking, and pausing then continuing wiped the "
              "text. Root cause: the recognizer's isFinal (after a pause) was treated as stop — "
              "recording ended (waveform vanished) and the next segment reset transcript to empty."),
            divider(),
            h2("Scope"),
            bullet_list([
                "VoiceCaptureService: keep the audio engine running for the whole session; on isFinal "
                "(or segment-end error) commit the text and seamlessly restart recognition; accumulate "
                "committed + current partial so pausing never wipes; stronger RMS scaling",
                "WaveformView: idle shimmer + stronger per-bar level reaction so it always animates "
                "while recording and clearly responds to volume",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No FFT bars; single-language (device locale)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Core/Capture/VoiceCaptureService.swift, Features/Capture/CaptureView.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Speaking animates the waveform; pausing and continuing appends (never clears) the transcript; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-144/145 (voice capture + waveform)."),
            divider(),
            h2("Next Ticket"), p("Optional auto-submit on stop; tune RMS scaling on device."),
        ),
    },

    {
        "summary": "TIME-147: App icon — guiding-star clock (cosmic brand mark)",
        "labels": ["ios", "branding", "design"],
        "description": doc(
            h2("Goal"),
            p("Install the user-provided app icon (a blue->violet glowing ring with a four-point "
              "north-star clock on near-black navy) as the real AppIcon, and use it as the anchor for "
              "the forthcoming cosmic palette."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Process the source PNG into a full-bleed 1024 (crop inside the rounded corners so the "
                "navy runs edge-to-edge; no alpha, no baked rounding) — iOS applies the mask",
                "AppIcon.appiconset: AppIcon-1024.png + single-size universal Contents.json",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Palette/token changes (next ticket); no in-app orb mark yet"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios/TimeSense/Assets.xcassets/AppIcon.appiconset/{AppIcon-1024.png,Contents.json}"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["actool generates all icon sizes with no alpha/rounding warnings; iOS build succeeds; icon shows full-bleed"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("None."),
            divider(),
            h2("Next Ticket"), p("Cosmic palette foundation (DesignTokens) sampled from the icon."),
        ),
    },

    {
        "summary": "TIME-148: Cosmic palette foundation (DesignTokens sampled from the icon)",
        "labels": ["ios", "design", "branding"],
        "description": doc(
            h2("Goal"),
            p("Evolve the design system to the dark cosmic theme anchored by the new app icon: "
              "near-black navy, blue->violet accents, gradient + glow tokens, semantic energy green."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Recolor colorsets (dark = cosmic; light kept coherent): Background #070912, Surface "
                "#141A2E, AccentColor violet-indigo #8A6BFF, TextPrimary/Secondary, Success/energy "
                "green #34D39A, Destructive",
                "New AccentBlue colorset (azure #4C8DFF)",
                "DesignTokens: accentBlue, energy, hairline; Gradient.hero (blue->violet) + .screen; "
                "Glow.accent/.subtle",
                "Default appTheme to dark (toggle preserved)",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No per-screen redesign yet (hero card + cards are later tickets); light theme not fully cosmic"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios: Assets.xcassets/*.colorset, Core/Design/DesignTokens.swift, App/TimeSenseApp.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["App renders the dark cosmic palette by default; new gradient/glow tokens available; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-147 (app icon anchor)."),
            divider(),
            h2("Next Ticket"), p("Domain-adaptive hero card on Now using Gradient.hero + Glow."),
        ),
    },

    {
        "summary": "TIME-149: Domain-adaptive hero card + cosmic Now screen",
        "labels": ["ios", "design", "now"],
        "description": doc(
            h2("Goal"),
            p("Apply the cosmic theme visibly: a gradient 'Best Next Action' hero card with a glowing "
              "domain icon + signal pills, on a cosmic Now background. This is where the palette "
              "foundation becomes visible."),
            divider(),
            h2("Scope"),
            bullet_list([
                "CosmicComponents: CosmicBackground (navy + corner auras), HeroPill, HeroGlyph, heroGradient(end:)",
                "BestNextActionCard: gradient header (label, big title, glyph, pills) + surface footer "
                "(confidence, Why, actions); glow shadow; gradient end color adapts to task category",
                "SuggestionCard (cross-domain): same gradient hero treatment; end color per domain",
                "Now screen background -> CosmicBackground",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Today/Insights/Capture cosmic pass (later); context/dashboard cards (later)"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios: Core/Design/CosmicComponents.swift (new), Features/Now/NowView.swift; TimeSense.xcodeproj"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Now shows a gradient, glowing, domain-adaptive hero card on a cosmic background; iOS build succeeds; sim renders the cosmic theme"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-148 (palette + tokens)."),
            divider(),
            h2("Next Ticket"), p("Cosmic pass on Today + context/dashboard cards."),
        ),
    },

    {
        "summary": "TIME-150: Cosmic pass — glass cards + cosmic background on all tabs",
        "labels": ["ios", "design"],
        "description": doc(
            h2("Goal"),
            p("Carry the cosmic theme across the whole app: update the shared card style to a glass "
              "look (propagates to every card) and put the cosmic background on Today, Capture, "
              "Insights, and Settings."),
            divider(),
            h2("Scope"),
            bullet_list([
                "cardStyle(): translucent surface + white hairline (Color.hairline) + soft dark shadow",
                "Today/Capture/Insights/Settings backgrounds -> CosmicBackground()",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["Per-screen hero redesigns beyond Now (Today hero is a separate ticket); dashboard cards separate"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["ios: Core/Design/ViewModifiers.swift; Features/{Today,Capture,Insights,Settings}/*View.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Every tab renders on the cosmic background with glass cards; iOS build succeeds"]),
            divider(),
            h2("Verification"),
            code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(),
            h2("Dependencies"), p("TIME-148/149 (palette + cosmic components)."),
            divider(),
            h2("Next Ticket"), p("Now dashboard context cards; Today hero polish."),
        ),
    },

    {
        "summary": "TIME-151: Now dashboard context cards (real signals)",
        "labels": ["ios", "backend", "now", "design"],
        "description": doc(
            h2("Goal"),
            p("Add the glanceable Calendar/Tasks/Energy/Nearby cards under the Now hero — populated "
              "from REAL data only (no fabricated metrics), with cards hidden when the signal is absent."),
            divider(),
            h2("Scope"),
            bullet_list([
                "Backend: NowResponse.context (NowContextCards) — next timed calendar event (title/time/"
                "minutes), tasks due today + completed today, energy+sleep hours (from sleep), current place",
                "iOS: decode context; ContextGrid (2x2 LazyVGrid) + ContextCard (glass); show Calendar "
                "if next event, Energy if sleep signal, Nearby if a place, Tasks always",
            ]),
            divider(),
            h2("Non-Goals"),
            bullet_list(["No steps/activity (needs HealthKit extension); no live map card; no sparklines yet"]),
            divider(),
            h2("Files Likely Changed"),
            bullet_list(["backend: api/v1/now.py; ios: Features/Now/NowView.swift, NowViewModel.swift"]),
            divider(),
            h2("Acceptance Criteria"),
            bullet_list(["Now shows a 2x2 dashboard of real signals below the hero; missing signals hide their card; suite + iOS build pass"]),
            divider(),
            h2("Verification"),
            code_block("cd backend && pytest tests/test_now.py -q ; xcodebuild build ..."),
            divider(),
            h2("Dependencies"), p("TIME-149/150 (cosmic hero + glass cards)."),
            divider(),
            h2("Next Ticket"), p("Today hero + agenda cosmic polish; optional HealthKit steps extension."),
        ),
    },

    {
        "summary": "TIME-152: Today agenda cosmic polish (time-of-day accent dots)",
        "labels": ["ios", "design", "today"],
        "description": doc(
            h2("Goal"), p("Finish the cosmic pass on Today: give the time-of-day group headers glowing accent dots (like the mockup's colored timeline), so the agenda reads as designed for the cosmic theme."),
            divider(), h2("Scope"), bullet_list(["SmartPlanCard group headers: a glowing Circle dot colored by part of day (Morning=blue, Afternoon=violet, Evening=purple, Anytime=muted)"]),
            divider(), h2("Non-Goals"), bullet_list(["No new Today hero card; agenda structure unchanged"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Today/TodayView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Today shows glowing accent dots on each time-of-day header; iOS build succeeds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-150 (cosmic pass)."),
            divider(), h2("Next Ticket"), p("App Store marketing screenshots; optional HealthKit steps extension."),
        ),
    },

    {
        "summary": "TIME-153: Premium glassmorphism refinement (soft blue->violet, glass cards, neon edge)",
        "labels": ["ios", "design"],
        "description": doc(
            h2("Goal"), p("Match the premium dark-glass spec: soft blue->violet hero gradients (fix flat blue), glassmorphism cards, richer navy->indigo->violet background, and neon edge lighting on primary cards."),
            divider(), h2("Scope"), bullet_list([
                "heroGradient -> soft 3-stop blue->indigo->violet (end optional, warms for health only) — fixes the flat-blue appointment card",
                "CosmicBackground -> navy->indigo->violet gradient + 3 soft glows",
                "cardStyle -> glass: ultraThinMaterial + translucent navy tint + top-light + gradient hairline",
                "heroCardChrome() modifier: neon edge stroke + violet/blue glow shadows on hero cards",
                "glassy context chips + hero pills",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No new content; other tabs inherit the glass card + background automatically"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios: Core/Design/CosmicComponents.swift, Core/Design/ViewModifiers.swift, Features/Now/NowView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Hero cards show a soft blue->violet gradient with a neon glow; cards read as frosted glass; background has navy->indigo depth; iOS build succeeds (verified via mock-data screenshot)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-148/149/150 (cosmic base)."),
            divider(), h2("Next Ticket"), p("Extend glass treatment nuances to Today/Insights hero elements if desired; App Store screenshots."),
        ),
    },

    {
        "summary": "TIME-154: Unify cosmic palette + nav/tab bar (backgrounds & colors match)",
        "labels": ["ios", "design", "bug"],
        "description": doc(
            h2("Goal"), p("User: backgrounds and colors do not match across the app. Root cause: two parallel palettes (hardcoded Cosmic vs DesignTokens assets) + a purple-heavy background that diverged from the near-black neutral navy reference. Unify to one palette matched to the reference."),
            divider(), h2("Scope"), bullet_list([
                "Single Cosmic palette matched to reference: base #080B14 (== asset Background), deep #05070E, surface #11141F (== asset Surface, neutral dark slate)",
                "CosmicBackground -> near-black base->deep with faint (0.10) blue/violet corner glows only (no purple wash)",
                "heroGradient muted (blue #3A5AE0 -> indigo #5E48CC -> violet #8A54DC)",
                "cardStyle -> solid dark slate + faint sheen + hairline (was translucent/purple)",
                "Align asset Background/Surface to Cosmic; hero footer + explanation sheet use unified colors",
                "Global UINavigationBar transparent + UITabBar = Cosmic.base so bars match",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No layout changes; light theme unchanged"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios: Core/Design/CosmicComponents.swift, ViewModifiers.swift; Features/Now/NowView.swift; App/TimeSenseApp.swift; Assets.xcassets Background/Surface"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Background, cards, chips, footer, tab bar share one near-black navy; no purple wash; matches the reference; iOS build succeeds (verified via mock screenshot)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-153 (glassmorphism)."),
            divider(), h2("Next Ticket"), p("Optional per-tab hero elements; App Store screenshots."),
        ),
    },

    {
        "summary": "TIME-155: Domain-coloured hero (dark card + domain glow) + multi-colour accents",
        "labels": ["ios", "design"],
        "description": doc(
            h2("Goal"), p("Match the reference: the recommendation card is a DARK navy card with a domain-COLOURED glow (green for a walk, blue for focus, cyan for errand, violet for meeting) — not a fixed bright blue->violet gradient — and the screen uses multiple semantic accent colours."),
            divider(), h2("Scope"), bullet_list([
                "Cosmic accents: green/blue/cyan/violet/amber; heroAccent(descriptor) + domainAccent(domain) maps",
                "HeroBackground: dark navy base + top-right RadialGradient in the domain accent (behind the glyph)",
                "HeroGlyph tinted to the accent (glow); HeroPill dark translucent with a coloured icon",
                "BestNextActionCard + SuggestionCard use domain accent for bg/glyph/pills/edge-glow",
                "Dashboard cards: Calendar=blue, Tasks=violet, Energy=green, Nearby=cyan; amber for High priority",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No new content; other tabs unchanged"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios: Core/Design/CosmicComponents.swift; Features/Now/NowView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Health rec -> dark card with green glow + green walker; other domains use their colour; multi-colour dashboard; iOS build succeeds (verified via mock screenshot matching the reference walk card)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-154 (unified palette)."),
            divider(), h2("Next Ticket"), p("Carry domain-colour treatment to Today; App Store screenshots."),
        ),
    },

    {
        "summary": "TIME-156: Domain-colour/cosmic treatment for Today, Capture, Insights",
        "labels": ["ios", "design"],
        "description": doc(
            h2("Goal"), p("Extend the domain-coloured cosmic system (from Now) to Today, Capture and Insights so the whole app matches."),
            divider(), h2("Scope"), bullet_list([
                "taskCategoryStyle colours -> Cosmic accents (blue/green/cyan/violet) — propagates to Today rows + cards",
                "Today AIRecommendedCard -> domain hero (dark HeroBackground + tinted glyph + pills + Why footer), like the Now hero",
                "Capture hero orb -> blue->violet gradient + glow + hairline",
                "Insights StatRow -> coloured icon chips (green/blue/amber/violet/cyan)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No new content; Insights premium gate unchanged; no HealthKit steps"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios: Features/Now/NowView.swift (taskCategoryStyle), Features/Today/TodayView.swift, Features/Capture/CaptureView.swift, Features/Insights/InsightsView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Today recommendation is a domain-coloured hero; task rows use cosmic accents; Capture orb is a blue->violet gradient; Insights stats have coloured chips; iOS build succeeds (Capture verified via screenshot)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-155 (domain-colour hero)."),
            divider(), h2("Next Ticket"), p("App Store screenshots; HealthKit steps extension."),
        ),
    },

    {
        "summary": "TIME-157: Cosmic/domain-colour pass on the Why-this-recommendation sheet",
        "labels": ["ios", "design"],
        "description": doc(
            h2("Goal"), p("Bring the Why-this-recommendation sheet in line with the cosmic domain-colour theme."),
            divider(), h2("Scope"), bullet_list([
                "RecommendedActionHeaderCard -> domain hero (HeroBackground + tinted icon + white title) with a domain-coloured ConfidenceRing",
                "ConfidenceRing gains tint + onDark params",
                "SignalsCard signalStyle colours -> Cosmic accents (Calendar=blue, Time=amber, Location=cyan, Priority=violet, Energy=green); available check -> Cosmic.green",
                "AlternativesCard already uses cosmic taskCategoryStyle",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No content/logic change"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Now/NowView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["The Why sheet header is a domain-coloured hero with a matching confidence ring; signals use multi-colour chips + green checks; iOS build succeeds (verified via mock screenshot)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-155/156 (domain-colour system)."),
            divider(), h2("Next Ticket"), p("App Store screenshots."),
        ),
    },

    {
        "summary": "TIME-158: Backend — daily activity (HealthKit steps/energy/exercise) store + /now",
        "labels": ["backend", "health"],
        "description": doc(
            h2("Goal"), p("Store and surface HealthKit activity (steps, active energy, exercise minutes) so the Now dashboard can show real steps/activity."),
            divider(), h2("Scope"), bullet_list([
                "DailyActivity model (one row per user/day, unique) + migration (server_default on timestamps)",
                "DailyActivityRepository upsert/get_for_day; POST /api/v1/activity + GET /activity/today",
                "NowContextCards gains steps/steps_goal/active_energy_kcal/exercise_minutes; _context_cards reads today's activity",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No iOS yet (separate ticket); no sitting/inactivity inference"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend: models/daily_activity.py, migrations/*, repositories/daily_activity_repository.py, api/v1/activity.py, api/v1/now.py, api/v1/__init__.py, models/__init__.py; tests/test_activity.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["POST /activity upserts today; /now context includes steps; suite passes; migration applies on the main chain"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_activity.py -v"),
            divider(), h2("Dependencies"), p("TIME-151 (now context cards)."),
            divider(), h2("Next Ticket"), p("TIME-159: iOS HealthService reads+syncs steps/activity; Steps dashboard card."),
        ),
    },

    {
        "summary": "TIME-159: iOS HealthKit activity — read+sync steps/energy/exercise, Steps card",
        "labels": ["ios", "health"],
        "description": doc(
            h2("Goal"), p("Extend the existing HealthService (sleep-only) to also read steps, active energy, and exercise minutes, sync them, and show a Steps card on Now."),
            divider(), h2("Scope"), bullet_list([
                "HealthService: request read auth for stepCount/activeEnergyBurned/appleExerciseTime; sumToday via HKStatisticsQuery; syncActivity -> POST /api/v1/activity; connectAndSync syncs both",
                "Launch: AppDelegate best-effort syncActivity (no-op without access)",
                "Info.plist NSHealthShareUsageDescription (required for any HealthKit read)",
                "NowContextCards decode steps/steps_goal/active_energy_kcal/exercise_minutes; Steps dashboard card",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No sitting/inactivity inference; no HealthKit writes"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios: Core/Health/HealthService.swift, App/AppDelegate.swift, Info.plist, Features/Now/NowView.swift, NowViewModel.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Connecting Health reads+syncs steps/energy/exercise; Now shows a real Steps card; iOS build succeeds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-158 (activity backend)."),
            divider(), h2("Next Ticket"), p("App Store screenshots."),
        ),
    },

    {
        "summary": "TIME-160: Inactivity/sedentary signal (the 'Sitting for 82m' reference)",
        "labels": ["backend", "ios", "health", "recommendations"],
        "description": doc(
            h2("Goal"), p("Infer how long the user has been sitting (from step data) and use it to drive the 'take a short walk' recommendation and a dashboard signal — the reference's 'Sitting for 82m'."),
            divider(), h2("Scope"), bullet_list([
                "iOS HealthService.inactiveMinutes(): 15-min step buckets over 4h -> minutes since last active (>=30 steps); included in the activity sync",
                "Backend: daily_activity.inactive_minutes column + migration; accept in /activity; surface in /now context",
                "context_builder._health now also reads DailyActivity (steps + sedentary_minutes) and builds HealthContext even without a sleep event",
                "health_candidates: the existing walk candidate now names the minutes and scales urgency with how long you've been sitting",
                "iOS: Energy card sub shows 'Sitting Xm — time to move' when >= 60",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No Apple Watch stand-hours; point-in-time value (as of last sync)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend: models/daily_activity.py, migrations/*, repositories/daily_activity_repository.py, api/v1/activity.py, api/v1/now.py, services/recommendation/context_builder.py, candidates/health_candidates.py; ios: Core/Health/HealthService.swift, Features/Now/NowView.swift, NowViewModel.swift; tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Sitting >= 90 min surfaces a 'Go for a short walk' recommendation naming the minutes; dashboard shows the sitting signal; suite + iOS build pass"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_inactivity.py -v"),
            divider(), h2("Dependencies"), p("TIME-158/159 (activity)."),
            divider(), h2("Next Ticket"), p("App Store screenshots."),
        ),
    },

    {
        "summary": "TIME-161: App Store marketing screenshots",
        "labels": ["marketing", "design", "ios"],
        "description": doc(
            h2("Goal"), p("Produce App Store listing screenshots from the real, cosmic-themed app: cosmic backdrop + Didot serif headline + a device screen, matching the reference mockups."),
            divider(), h2("Scope"), bullet_list([
                "Capture 5 real screens via a DEBUG env-driven mock (MOCK_NOW/MOCK_TITLE/MOCK_TAB/MOCK_WHY), reverted after",
                "Compose each onto a cosmic backdrop with a Didot headline + TimeSense wordmark (build_screenshots.py, Pillow) at 1290x2796",
                "Deliverables in docs/marketing/appstore/ (5 PNGs + README); preview gallery artifact",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No 6.9\" (1320x2868) render yet (one-line change); no App Store Connect upload"]),
            divider(), h2("Files Likely Changed"), bullet_list(["docs/marketing/appstore/*.png, README.md; docs/marketing/build_screenshots.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["5 App Store-sized marketing screenshots exist showing the cosmic/domain-colour app with headlines"]),
            divider(), h2("Verification"), code_block("open docs/marketing/appstore/*.png"),
            divider(), h2("Dependencies"), p("The cosmic redesign (TIME-147..157) + health (TIME-158..160)."),
            divider(), h2("Next Ticket"), p("Upload to App Store Connect; localized variants."),
        ),
    },

    {
        "summary": "TIME-162: Multi-colour Capture + Insights screens (fix mono-purple)",
        "labels": ["ios", "design"],
        "description": doc(
            h2("Goal"), p("Capture and Insights were just purple + white on dark. Bring in the multi-colour palette (blue/amber/green/cyan/violet) so they match the rest of the redesign."),
            divider(), h2("Scope"), bullet_list([
                "Capture: chips get an icon + distinct colour (Task blue, Reminder amber, Schedule violet, Errand cyan, Idea green); detector row -> coloured icon tiles",
                "Insights gate: each preview card its own accent (focus blue line, pattern amber bars, balance green ring, routine violet ring) with glowing charts; lock banner -> blue->violet gradient with a lock chip",
                "Regenerated the two affected App Store frames",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["Premium (loaded) Insights StatRow already coloured (TIME-156)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios: Features/Capture/CaptureView.swift, Features/Insights/InsightsView.swift; docs/marketing/appstore/*"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Capture + Insights show multiple accent colours, not mono-purple; iOS build succeeds (verified via screenshots)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-155/156 (domain colours)."),
            divider(), h2("Next Ticket"), p("6.9\" screenshots; App Store Connect upload."),
        ),
    },

    {
        "summary": "TIME-163: Capture chips — functional type hints + fixed wrapping bar",
        "labels": ["ios", "backend", "capture", "ux"],
        "description": doc(
            h2("Goal"), p("The Capture chips (Task/Reminder/Schedule/Errand/Idea) did nothing and scrolled off-screen. Make them functional (bias the parse) and fully visible (no horizontal scroll)."),
            divider(), h2("Scope"), bullet_list([
                "Backend: /capture accepts optional type_hint; CaptureService.parse injects it into the LLM prompt (per-type guidance) and forces Idea -> priority 5, no schedule",
                "iOS: CaptureRequest/submit carry typeHint (the selected chip); chips row uses a FlowLayout (wraps to 2 rows, fully visible) instead of a horizontal scroll",
                "New FlowLayout (Layout protocol) in CosmicComponents",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No multi-select; hint is a soft bias, not a hard override"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend: api/v1/capture.py, services/capture_service.py; ios: Features/Capture/CaptureView.swift, CaptureViewModel.swift, Core/Design/CosmicComponents.swift; tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Selecting a chip changes the parse (Idea -> low priority); all 5 chips visible without scrolling; suite + iOS build pass"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_capture_hint.py -v"),
            divider(), h2("Dependencies"), p("TIME-162 (coloured chips)."),
            divider(), h2("Next Ticket"), p("6.9\" screenshots; App Store Connect upload."),
        ),
    },

    {
        "summary": "TIME-164: Backend — explicit capture inputs (time/date/location) + places search",
        "labels": ["backend", "capture", "location"],
        "description": doc(
            h2("Goal"), p("Let Capture send explicit scheduled_at / due_at / location that OVERRIDE the parse, store a real location on tasks, and provide an autocomplete search (saved places + maps)."),
            divider(), h2("Scope"), bullet_list([
                "Task: location_name/lat/lng columns + migration; TaskCreate/Response + task_service persist them",
                "Capture request: scheduled_at/due_at/location_name/lat/lng; endpoint applies as overrides (explicit time -> scheduled_start + end from duration, prevents auto-schedule; explicit due date; location stored)",
                "GET /places/search?q=&lat=&lng= -> saved places matching + maps text search (name/address/coords/source)",
                "Made the flaky calendar test assert action_type (deterministic) not the LLM-phrased title",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["iOS inputs (TIME-165); engine use of task.location for candidates (follow-up)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend: models/task.py, migrations/*, schemas/task.py, services/task_service.py, api/v1/capture.py, api/v1/places.py; tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Explicit time/location on /capture override the parse and persist; /places/search returns saved + maps matches; suite passes"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_capture_overrides.py -v"),
            divider(), h2("Dependencies"), p("TIME-163 (capture chips)."),
            divider(), h2("Next Ticket"), p("TIME-165: iOS contextual inputs (date+time pickers, Places autocomplete)."),
        ),
    },

    {
        "summary": "TIME-165: iOS contextual Capture inputs (time / date / location)",
        "labels": ["ios", "capture", "ux"],
        "description": doc(
            h2("Goal"), p("Reveal a relevant, optional input when a type chip is picked: Reminder/Schedule -> a date with optional time; Errand -> a Places/maps autocomplete. Explicit values override the parse."),
            divider(), h2("Scope"), bullet_list([
                "CaptureView: contextualInput(for:) below the chips; dateTimeInput (DatePicker + 'Add a time' toggle, fuller-but-optional); errandInput (debounced /places/search autocomplete with saved-star vs maps-pin results)",
                "submit builds scheduled_at (time set) / due_at (date only) / location; onChange(chip) defaults includeTime for Reminder and clears state",
                "CaptureViewModel: PlaceSearchResult + searchPlaces; submit carries the structured fields; near-bias from LocationService.currentLocation",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No map preview; no multi-location"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios: Features/Capture/CaptureView.swift, CaptureViewModel.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Picking Reminder/Schedule shows a date(+optional time) picker; Errand shows a location autocomplete; the values reach /capture and override the parse; iOS build succeeds (verified via screenshots)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16' CODE_SIGNING_ALLOWED=NO"),
            divider(), h2("Dependencies"), p("TIME-164 (backend overrides + places search)."),
            divider(), h2("Next Ticket"), p("Engine use of task.location for errand candidates; 6.9\" screenshots."),
        ),
    },

    {
        "summary": "TIME-166: Refresh Capture App Store screenshot (final 2-row chips)",
        "labels": ["marketing", "design"],
        "description": doc(
            h2("Goal"), p("The Capture App Store frame predated the 2-row chip layout + contextual inputs. Recapture from main and regenerate the frame + preview gallery."),
            divider(), h2("Scope"), bullet_list(["Recapture Capture on current main (2-row coloured chips); regenerate 03_capture.png; redeploy the gallery artifact"]),
            divider(), h2("Non-Goals"), bullet_list(["No app code change; other frames unchanged"]),
            divider(), h2("Files Likely Changed"), bullet_list(["docs/marketing/appstore/03_capture.png"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["03_capture.png shows the final Capture screen (2-row chips)"]),
            divider(), h2("Verification"), code_block("open docs/marketing/appstore/03_capture.png"),
            divider(), h2("Dependencies"), p("TIME-163/165 (chips + inputs)."),
            divider(), h2("Next Ticket"), p("Engine use of task.location; 6.9\" screenshot set."),
        ),
    },

    {
        "summary": "TIME-167: Engine uses a task's stored errand location (not the title)",
        "labels": ["backend", "recommendations", "location"],
        "description": doc(
            h2("Goal"), p("When a task has an explicit location (from the Capture errand field), the engine should use those exact coordinates as the errand destination instead of searching for a place by the task title."),
            divider(), h2("Scope"), bullet_list([
                "LocationIntent gains coordinates; context_builder._location_intent prefers task.location_lat/lng (query=location_name) over title detection",
                "location_candidates: with explicit coordinates, build the destination Place directly (PREFERRED_PLACE_FOUND, no maps search); still compute travel feasibility via maps",
                "Fallback: with a known destination but no maps, estimate travel from straight-line distance (~35 km/h) so the errand stays usable",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to title-based detection when there's no stored location"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend: services/recommendation/types.py, context_builder.py, candidates/location_candidates.py; tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A task with stored coordinates yields a location candidate for that exact place (not a title guess); works even without maps via estimate; suite passes"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_errand_location.py -v"),
            divider(), h2("Dependencies"), p("TIME-164/165 (stored errand location)."),
            divider(), h2("Next Ticket"), p("6.9\" screenshots; App Store Connect."),
        ),
    },

    {
        "summary": "TIME-168: Companion website — cosmic marketing landing page",
        "labels": ["web", "marketing", "design"],
        "description": doc(
            h2("Goal"), p("The web companion only had an admin login. Build a proper marketing landing page that showcases TimeSense in the app's cosmic aesthetic, while keeping the admin entry."),
            divider(), h2("Scope"), bullet_list([
                "app/page.tsx: sticky nav (orb wordmark + Admin link + Get the app), hero (serif headline + gradient + phone), 5 alternating feature rows with real app screenshots + domain-colour pills, a 6-card capability grid, CTA band, footer (keeps Admin link)",
                "globals.css: cosmic theme (navy base, blue/violet/cyan/green/amber accents, glass cards, glows) scoped to a .site wrapper; Playfair Display serif via next/font",
                "layout.tsx: real metadata/OG/title + serif font; app screenshots copied to public/screens; app icon -> favicon/OG",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No real App Store links yet (anchors); admin dashboard unchanged; no CMS"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/{page,layout}.tsx, web/app/globals.css, web/public/screens/*, web/public/app-icon.png"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Landing page showcases TimeSense (hero + features + screenshots), matches the app's cosmic look, keeps Admin access; next build succeeds; verified via headless-Chrome screenshots"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("Heeded web/AGENTS.md (Next 16 docs)."),
            divider(), h2("Next Ticket"), p("Wire real App Store / Play links; privacy + support pages."),
        ),
    },

    {
        "summary": "TIME-169: Fix website logo — return to top of home on click",
        "labels": ["web", "bug", "ux"],
        "description": doc(
            h2("Goal"), p("Clicking the TimeSense wordmark didn't appear to do anything on the home page (Next.js doesn't scroll on same-route navigation). Make the logo return you to the top."),
            divider(), h2("Scope"), bullet_list([
                "Brand client component: on home, smooth-scroll to top (preventDefault); otherwise navigate to /",
                "Use Brand in nav + footer (removes duplicated inline wordmark + Orb helper)",
                "Smooth scroll + scroll-margin so #features/#how/#get anchors clear the sticky nav",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No content change"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/Brand.tsx (new), web/app/page.tsx, web/app/globals.css"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Clicking the logo returns to the top of the home page; anchor links land below the nav; next build succeeds"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-168 (website)."),
            divider(), h2("Next Ticket"), p("Real store links; privacy/support pages; SVG icons."),
        ),
    },

    {
        "summary": "TIME-170: Companion web app — Now, Today, Capture for signed-in users",
        "labels": ["web", "feature"],
        "description": doc(
            h2("Goal"), p("Give a signed-in user a real (companion) web experience, not just admin. A cosmic /app with their best next action, today's plan, and quick capture."),
            divider(), h2("Scope"), bullet_list([
                "/app route (any signed-in user; reuses Firebase auth) with a cosmic shell (wordmark, Now/Today/Capture tabs, sign out) + email/password sign-in gate",
                "Now: /api/v1/now -> domain-coloured best-next-action hero + Calendar/Tasks/Steps/Energy cards + Mark done (PATCH /tasks)",
                "Today: /api/v1/timeline/today -> the day's plan (coloured icons, times, done state)",
                "Capture: POST /api/v1/capture with the coloured type-hint chips",
                "Landing: nav gets Log in / Open the app -> /app; Admin moved to the footer; useApi alias; app CSS",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["Not the full native product (companion only per product rules); no voice on web; no contextual capture pickers yet; Insights/Settings later"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/{layout,page,today/page,capture/page}.tsx, web/lib/{api.ts,appTypes.ts}, web/app/{page.tsx,globals.css}"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Signed-in users get Now/Today/Capture at /app matching the app's cosmic look; non-Firebase env shows a friendly gate; next build succeeds; verified via mock-data screenshots"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-168/169 (website)."),
            divider(), h2("Next Ticket"), p("Insights on web; store links; privacy page."),
        ),
    },
    {
        "summary": "TIME-171: Insights in the companion web app",
        "labels": ["web", "feature"],
        "description": doc(
            h2("Goal"), p("Complete the /app companion (Now/Today/Capture/Insights) by adding an Insights tab that mirrors the native app: Premium users see their weekly insight; non-Premium users see an upgrade gate."),
            divider(), h2("Scope"), bullet_list([
                "Add an Insights tab to the /app shell (TABS in layout.tsx)",
                "New app/app/insights/page.tsx fetching GET /api/v1/insights/weekly via the authed useApi hook",
                "Premium: Playfair 'Your week' + week range, summary card, domain-coloured stat cards (tasks/completion/most-skipped-meal/late-wakes/commutes/kept-vs-deferred); optional rows hide when zero",
                "Non-Premium (403 SUBSCRIPTION_REQUIRED): cosmic upgrade gate — 'Your AI insights' banner, four preview cards with inline SVG mini-charts, 'Upgrade in the mobile app' CTA",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No web checkout (subscriptions are managed in the mobile app); no insights history view yet"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/layout.tsx, web/app/app/insights/page.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Insights tab renders the weekly insight for Premium users and a graceful upgrade gate for non-Premium (403); next build succeeds; both states verified via screenshots"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-170 (companion web app); backend GET /api/v1/insights/weekly (Premium-gated)."),
            divider(), h2("Next Ticket"), p("Public privacy page; store links."),
        ),
    },
    {
        "summary": "TIME-172: Public Privacy Policy page for the marketing site",
        "labels": ["web", "feature"],
        "description": doc(
            h2("Goal"), p("Give the marketing site a real, public Privacy Policy at /privacy, cosmic-styled and specific to how TimeSense actually handles data."),
            divider(), h2("Scope"), bullet_list([
                "New public web/app/privacy/page.tsx (Metadata title/description) in the cosmic .site shell, linked from the footer",
                "TimeSense-specific copy: what we collect, the opt-in-only raw-audio rule (highlighted), AI/LLM parsing under no-training terms, sub-processors (Firebase/OpenAI/Apple/Google/Stripe), user controls (approval-first, opt-in connections, export, delete), retention, security, children, changes, contact",
                "Scoped .legal prose styles in globals.css (section numbers, bulleted lists, callout box)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No Terms of Service page yet; contact address is a placeholder pending a real mailbox; not legal advice / human legal review still required"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/privacy/page.tsx, web/app/globals.css, web/app/page.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["/privacy renders a styled, accurate policy reachable from the footer; next build succeeds (static); verified via screenshot"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-168 (marketing site)."),
            divider(), h2("Next Ticket"), p("Terms of Service; real App Store / Play download links."),
        ),
    },
    {
        "summary": "TIME-173: Public Terms of Service page for the marketing site",
        "labels": ["web", "feature"],
        "description": doc(
            h2("Goal"), p("Give the marketing site a real, public Terms of Service at /terms, cosmic-styled and specific to TimeSense (an assistant that suggests, never acts without approval)."),
            divider(), h2("Scope"), bullet_list([
                "New public web/app/terms/page.tsx (Metadata) in the cosmic .site shell, reusing the .legal styles; linked from the footer and cross-linked with Privacy",
                "TimeSense-specific ToS: service scope (suggestions not instructions; approval-first), accounts (Firebase, age 13+), subscriptions & billing (14-day trial requires payment, Free Basic after; Apple/Google/Stripe; no card numbers; auto-renew/cancel/refunds), acceptable use, your content + AI license, third-party connections, disclaimers, limitation of liability, termination, changes, contact",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No App Store / Play download links yet (real app URLs pending); contact address is a placeholder; not legal advice / human legal review still required"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/terms/page.tsx, web/app/page.tsx, web/app/privacy/page.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["/terms renders a styled, accurate ToS reachable from the footer and cross-linked with Privacy; next build succeeds (static); verified via screenshot"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-168 (marketing site), TIME-172 (Privacy / .legal styles)."),
            divider(), h2("Next Ticket"), p("Real App Store / Play download links once available."),
        ),
    },
    {
        "summary": "TIME-174: Hide the Next.js dev-tools indicator on the web app",
        "labels": ["web", "chore"],
        "description": doc(
            h2("Goal"), p("Remove the on-screen Next.js dev-tools indicator (the 'N' badge in the lower-left corner) from the web app."),
            divider(), h2("Scope"), bullet_list(["Set devIndicators:false in web/next.config.ts"]),
            divider(), h2("Non-Goals"), bullet_list(["No other config changes"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/next.config.ts"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["The 'N' indicator no longer renders; next build succeeds"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("None."),
            divider(), h2("Next Ticket"), p("Web Now 'Why this recommendation?'."),
        ),
    },
    {
        "summary": "TIME-175: Why this recommendation on the web Now page",
        "labels": ["web", "feature"],
        "description": doc(
            h2("Goal"), p("Surface the reasoning behind the web Now pick, matching the native app's 'Why This Recommendation?' sheet."),
            divider(), h2("Scope"), bullet_list([
                "New WhyPanel disclosure under the Now hero; lazily fetches GET /api/v1/now/why?task_id= on first open",
                "Renders the structured WhyResponse: summary, colour-coded signals (connected vs not), decision-factor chips, alternatives considered",
                "appTypes: WhyResponse type + signalColor() helper",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No backend changes (/now/why already exists)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/WhyPanel.tsx, web/app/app/page.tsx, web/lib/appTypes.ts"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Tapping 'Why this recommendation?' expands the structured explanation; next build succeeds; verified via screenshot"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-170 (companion web app); backend GET /api/v1/now/why."),
            divider(), h2("Next Ticket"), p("App-icon logo mark."),
        ),
    },
    {
        "summary": "TIME-176: Web logo uses the app-icon mark",
        "labels": ["web", "feature"],
        "description": doc(
            h2("Goal"), p("Replace the plain circle in the web wordmark with a mark that matches the real app icon (glowing blue→violet ring + sparkle)."),
            divider(), h2("Scope"), bullet_list([
                "New reusable SVG <Mark> (gradient ring, subtle clock ticks, sparkle core), used in the marketing nav/footer, the /app bar, and sign-in",
                "New file-based app/icon.svg favicon (rounded dark square) replacing the heavy PNG favicon (PNG kept as OG image)",
                "Remove the now-unused .orb CSS",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No changes to the native iOS/Android app icons (web only)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/Mark.tsx, web/app/Brand.tsx, web/app/app/layout.tsx, web/app/icon.svg, web/app/layout.tsx, web/app/globals.css"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Wordmark + favicon show the app-icon-style mark; next build succeeds; verified via screenshot"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-168 (marketing site)."),
            divider(), h2("Next Ticket"), p("Google/Outlook calendar + Slack integration connect flow."),
        ),
    },
    {
        "summary": "TIME-177: Backend OAuth handshake + Google Calendar connect",
        "labels": ["backend", "integrations", "feature"],
        "description": doc(
            h2("Goal"), p("Implement the server-side OAuth handshake the integration config already assumed, starting with Google Calendar, so a user can grant calendar access and have tokens stored securely."),
            divider(), h2("Scope"), bullet_list([
                "GET /api/v1/integrations/google/authorize (Premium) → Google consent URL carrying a signed, expiring state (user identity + CSRF); 503 until configured",
                "GET /api/v1/integrations/google/callback → verify state, exchange code for tokens server-side, store encrypted via CalendarService.connect, deep-link back; all failure branches → failure deep link",
                "app/core/oauth_state.py (HS256 signed/expiring state), app/integrations/google_oauth.py (authorize URL + code exchange), oauth_success/failure_redirect config",
                "Scope calendar.events (writes still gated behind in-app approval)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No mobile Connect UI yet (separate ticket); no Outlook/Slack yet; no token-refresh scheduler"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/api/v1/integrations.py, backend/app/core/oauth_state.py, backend/app/integrations/google_oauth.py, backend/app/core/config.py, backend/app/api/v1/__init__.py, backend/tests/test_integrations_oauth.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["authorize returns a valid Google consent URL when configured (503 otherwise); callback exchanges the code and stores encrypted tokens, redirecting back; all failure paths handled; tests green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_integrations_oauth.py -q"),
            divider(), h2("Dependencies"), p("Existing GoogleCalendarProvider + CalendarService.connect + EncryptedString (TIME-056)."),
            divider(), h2("Next Ticket"), p("Outlook/Microsoft calendar provider + handshake; then mobile Connect UI."),
        ),
    },
    {
        "summary": "TIME-178: Everyone is Premium for their first 2 weeks (intro trial)",
        "labels": ["backend", "subscriptions", "feature"],
        "description": doc(
            h2("Goal"), p("Give every account Premium free for its first 2 weeks (no payment), so new users get the full experience (Insights, integrations, AI features) from day one."),
            divider(), h2("Scope"), bullet_list([
                "SubscriptionService.is_premium returns True when the account is younger than settings.intro_trial_days (14), in addition to an active/trialing subscription",
                "Route /subscriptions/me/entitlement through is_premium; report status 'trialing' during the intro window",
                "config.intro_trial_days = 14; helpers in_intro_trial / intro_trial_ends_at",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to paid billing/webhooks; no per-user trial overrides; after the window users fall back to Free Basic unless subscribed"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/subscription_service.py, backend/app/api/v1/subscriptions.py, backend/app/core/config.py, backend/tests/*"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A brand-new account is Premium (entitlement is_premium True, status trialing); after intro_trial_days it is not (absent a subscription); active subs stay Premium; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_subscriptions.py tests/test_entitlements.py -q"),
            divider(), h2("Dependencies"), p("Existing SubscriptionService/entitlement gate."),
            divider(), h2("Next Ticket"), p("Wire real Premium state into the mobile apps."),
        ),
    },
    {
        "summary": "TIME-179: Wire real Premium state into the mobile apps",
        "labels": ["ios", "android", "subscriptions", "bug"],
        "description": doc(
            h2("Goal"), p("Make the iOS and Android apps reflect the user's real Premium entitlement, so Insights (and Premium-gated Connect flows) actually work instead of always showing the upgrade gate."),
            divider(), h2("Scope"), bullet_list([
                "iOS AppState: on sign-in, fetch GET /api/v1/subscriptions/me/entitlement and set isPremium; clear on sign-out; InsightsView .task(id: isPremium) so it loads when Premium resolves",
                "Android AppViewModel: fetch entitlement on auth and combine into AppUiState.isPremium (replace the hardcoded false)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No StoreKit/Play purchase UI; no live mid-session entitlement refresh"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/App/AppState.swift, ios/TimeSense/Features/Insights/InsightsView.swift, android/app/src/main/java/com/timesense/app/AppViewModel.kt"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A Premium/intro-trial user sees real Insights (not the gate) on both platforms; isPremium reflects /me/entitlement; iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-178 (entitlement reflects the intro trial)."),
            divider(), h2("Next Ticket"), p("Outlook + Slack backend handshakes; mobile Connect UI."),
        ),
    },
    {
        "summary": "TIME-180: Outlook/Microsoft calendar provider + OAuth handshake",
        "labels": ["backend", "integrations", "feature"],
        "description": doc(
            h2("Goal"), p("Add Outlook/Microsoft calendar support (net-new provider + OAuth), alongside Google."),
            divider(), h2("Scope"), bullet_list([
                "MicrosoftCalendarProvider against Microsoft Graph (/me/calendarView read, /me/events create/delete), registered as 'microsoft'",
                "microsoft_oauth.py (common-tenant authorize + code exchange; scope offline_access + Calendars.ReadWrite)",
                "/api/v1/integrations/microsoft/{authorize,callback}; refactor the Google callback into a shared helper both providers use",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No token-refresh scheduler; no mobile UI (separate ticket)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/integrations/microsoft_calendar.py, backend/app/integrations/microsoft_oauth.py, backend/app/services/calendar_service.py, backend/app/api/v1/integrations.py, backend/tests/test_integrations_oauth.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["authorize returns a Microsoft consent URL when configured (503 otherwise); callback exchanges + stores encrypted tokens; provider maps Graph events; tests green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_integrations_oauth.py -q"),
            divider(), h2("Dependencies"), p("TIME-177 (handshake framework)."),
            divider(), h2("Next Ticket"), p("Slack OAuth handshake."),
        ),
    },
    {
        "summary": "TIME-181: Slack OAuth handshake",
        "labels": ["backend", "integrations", "feature"],
        "description": doc(
            h2("Goal"), p("Add the Slack OAuth consent handshake so users can connect Slack without pasting a token (scan→task already exists)."),
            divider(), h2("Scope"), bullet_list([
                "slack_oauth.py (v2 authorize URL + oauth.v2.access exchange; check ok:false; bot scopes channels:history/read, groups:history)",
                "/api/v1/integrations/slack/{authorize,callback}; callback stores the token via SlackService.connect",
                "config.slack_redirect_uri",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to the existing scan/pending/confirm flow; no mobile UI (separate ticket)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/integrations/slack_oauth.py, backend/app/api/v1/integrations.py, backend/app/core/config.py, backend/tests/test_integrations_oauth.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["authorize returns a Slack consent URL when configured (503 otherwise); callback exchanges the code and stores the token; ok:false raises; tests green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_integrations_oauth.py -q"),
            divider(), h2("Dependencies"), p("TIME-177 (handshake framework); existing SlackService (TIME-049)."),
            divider(), h2("Next Ticket"), p("Mobile Connect UI for Google/Outlook/Slack."),
        ),
    },
    {
        "summary": "TIME-182: iOS Connect UI for Google/Outlook/Slack",
        "labels": ["ios", "integrations", "feature"],
        "description": doc(
            h2("Goal"), p("Let users connect Google Calendar, Outlook, and Slack from the iOS app via the OAuth handshake."),
            divider(), h2("Scope"), bullet_list([
                "Settings ▸ Connections (ConnectionsView) with a Connect button per provider",
                "Connect → GET /api/v1/integrations/{provider}/authorize → open the URL in ASWebAuthenticationSession (callback scheme 'timesense')",
                "Handle cancel / 403 (Premium) / 503 (not configured); Premium-gated section; register the new file in the Xcode target",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No per-provider connected-status endpoint; no token refresh UI"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Settings/ConnectionsView.swift, ios/TimeSense/Features/Settings/SettingsView.swift, ios/TimeSense.xcodeproj/project.pbxproj"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Settings ▸ Connections shows Connect buttons that launch the provider consent flow; iOS builds; failure states handled"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-177/180/181 (backend handshakes); TIME-179 (Premium state)."),
            divider(), h2("Next Ticket"), p("Android Connect UI."),
        ),
    },
    {
        "summary": "TIME-183: Android Connect UI for Google/Outlook/Slack",
        "labels": ["android", "integrations", "feature"],
        "description": doc(
            h2("Goal"), p("Let users connect Google Calendar, Outlook, and Slack from the Android app via the OAuth handshake."),
            divider(), h2("Scope"), bullet_list([
                "Settings ▸ Connections (ConnectionsScreen + ConnectionsViewModel) with a Connect button per provider",
                "Connect → GET /api/v1/integrations/{provider}/authorize → open the URL via an ACTION_VIEW intent",
                "MainActivity timesense://integrations deep-link filter + singleTask so the redirect returns to the app; Premium-gated",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No per-provider connected-status endpoint; no Custom Tabs dependency"]),
            divider(), h2("Files Likely Changed"), bullet_list(["android/app/src/main/java/com/timesense/app/features/settings/ConnectionsScreen.kt, .../ConnectionsViewModel.kt, .../SettingsScreen.kt, .../navigation/MainNavHost.kt, android/app/src/main/AndroidManifest.xml"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Settings ▸ Connections shows Connect buttons that open the provider consent flow; redirect returns to the app; failure states handled (compile verified in CI)"]),
            divider(), h2("Verification"), code_block("cd android && ./gradlew assembleDebug"),
            divider(), h2("Dependencies"), p("TIME-177/180/181 (backend handshakes); TIME-179 (Premium state); TIME-182 (iOS parity)."),
            divider(), h2("Next Ticket"), p("Set the OAuth app credentials to go live; add a connected-status endpoint."),
        ),
    },
    {
        "summary": "TIME-184: Imminent appointment beats a generic context-switch nudge",
        "labels": ["backend", "recommendation-engine", "bug"],
        "description": doc(
            h2("Goal"), p("An appointment coming up within the hour should reliably be the top recommendation, not occasionally edged out by a generic 'wind down / switch mode' nudge. Fixes the flaky test_calendar_sync test."),
            divider(), h2("Scope"), bullet_list([
                "Add a scoring penalty: a context_switch nudge (work/home/sleep) is suppressed when a calendar event is within the hour",
                "Root cause was a near-tie score at 'night' (part_of_day derives from UTC when the user has no timezone)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["Not changing part_of_day's UTC fallback (harmless in production); no scoring-weight overhaul"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation/scoring/penalties.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["test_calendar_sync::test_appointment_within_the_hour_is_surfaced_over_tasks passes deterministically; full suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest -q"),
            divider(), h2("Dependencies"), p("None."),
            divider(), h2("Next Ticket"), p("(backlog) give part_of_day a per-user timezone fallback."),
        ),
    },
    {
        "summary": "TIME-185: agree/disagree feedback signals + demote-not-hide",
        "labels": ["backend", "recommendation-engine", "feature"],
        "description": doc(
            h2("Goal"), p("Add first-class agree/disagree feedback signals so the Now screen can offer a two-stage Agree/Disagree flow; disagree surfaces a different recommendation without hiding the task for hours."),
            divider(), h2("Scope"), bullet_list([
                "Add agree/disagree to FeedbackRequest Literal + RecommendationFeedback.VALID_SIGNALS (no migration)",
                "agree: positive, non-suppressing (recorded only)",
                "disagree: 'demote, don't hide' — new get_recently_disagreed_task_ids (3h window) → UserContext.recently_disagreed_task_ids → RECENTLY_DISAGREED reason code → +30 demotion penalty; NOT the not_now 4h hide",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to done/snooze/not_now; no impression log yet (separate telemetry plan)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/api/v1/recommendations.py, backend/app/models/recommendation_feedback.py, backend/app/repositories/recommendation_feedback_repository.py, backend/app/services/recommendation/{types.py,context_builder.py,candidates/task_candidates.py,scoring/penalties.py}, tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["agree/disagree accepted (201); a disagreed task is demoted (different best surfaces) but still appears in alternatives (not hidden); agree stays best; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_feedback.py tests/test_now.py -q"),
            divider(), h2("Dependencies"), p("Existing recommendation feedback + engine."),
            divider(), h2("Next Ticket"), p("iOS/Android/web two-stage UI."),
        ),
    },
    {
        "summary": "TIME-186: iOS two-stage Agree/Disagree on the Best Next Action card",
        "labels": ["ios", "feature"],
        "description": doc(
            h2("Goal"), p("Replace Done/Snooze/Not-now on the Now card with a two-stage Agree/Disagree flow."),
            divider(), h2("Scope"), bullet_list([
                "QuickActionRow: initial Agree/Disagree; on Agree reveal existing Done/Snooze; reset via .id(task.id)",
                "NowViewModel agree()/disagree(); sendFeedback gains a reload flag (agree no-reload, disagree reload)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No snooze-duration picker (keeps 3h default)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Now/NowView.swift, NowViewModel.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Two-stage swap works; Disagree surfaces a different action; iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-185."),
            divider(), h2("Next Ticket"), p("Android + web parity."),
        ),
    },
    {
        "summary": "TIME-187: Android two-stage Agree/Disagree on the Best Next Action card",
        "labels": ["android", "feature"],
        "description": doc(
            h2("Goal"), p("Bring Android to parity: build the Now feedback plumbing (none today) and the two-stage Agree/Disagree flow."),
            divider(), h2("Scope"), bullet_list([
                "NowViewModel: sendFeedback POST + agree/disagree/snooze (java.time.Instant for snooze_until)",
                "NowScreen BestTaskCard: two-stage remember(task.id){mutableStateOf(false)} replacing the no-op Snooze/Not-now buttons",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No local compile (no JDK) — build in CI"]),
            divider(), h2("Files Likely Changed"), bullet_list(["android/app/src/main/java/com/timesense/app/features/now/NowViewModel.kt, NowScreen.kt"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Two-stage flow wired to the feedback endpoint; builds in CI"]),
            divider(), h2("Verification"), code_block("cd android && ./gradlew assembleDebug"),
            divider(), h2("Dependencies"), p("TIME-185/186."),
            divider(), h2("Next Ticket"), p("Web parity."),
        ),
    },
    {
        "summary": "TIME-188: web two-stage Agree/Disagree on the Now page",
        "labels": ["web", "feature"],
        "description": doc(
            h2("Goal"), p("Bring the web companion to parity with the two-stage Agree/Disagree flow."),
            divider(), h2("Scope"), bullet_list([
                "page.tsx: replace 'Mark done' with Agree/Disagree → Done/Snooze; agreedFor state keyed to task id",
                "New sendFeedback POST to /api/v1/recommendations/feedback",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No snooze-duration picker"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/page.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Two-stage swap renders and calls feedback; next build succeeds; verified via screenshot"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-185."),
            divider(), h2("Next Ticket"), p("(future) wire agree/disagree into the impression->outcome telemetry log."),
        ),
    },
    {
        "summary": "TIME-189: Capture input validation & hygiene",
        "labels": ["backend", "capture", "guardrails"],
        "description": doc(
            h2("Goal"), p("Reject/normalize malformed capture input at the schema boundary (Phase 1 of the capture-guardrails plan)."),
            divider(), h2("Scope"), bullet_list([
                "Pydantic validators on CaptureRequest: timezone via zoneinfo (invalid→UTC), type_hint whitelist to the 5 chips (unknown→None), lat/lng ranges (422), raw_input strip/collapse/reject-whitespace-only, model_validator date sanity (scheduled_at over due_at; reject <2000 or >now+5y)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No LLM-output coercion (separate ticket)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/api/v1/capture.py, backend/tests/test_capture.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Bad lat/lng → 422; whitespace-only → 422; invalid tz → UTC; unknown chip → ignored; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_capture.py -q"),
            divider(), h2("Dependencies"), p("None."),
            divider(), h2("Next Ticket"), p("LLM-output safety."),
        ),
    },
    {
        "summary": "TIME-190: Harden the flaky time-dependent calendar-sync test",
        "labels": ["backend", "tests"],
        "description": doc(
            h2("Goal"), p("Make test_why_calendar_signal_reflects_real_free_time deterministic (it was UTC/work-hours flaky)."),
            divider(), h2("Scope"), bullet_list(["Pin the server clock (patch now.datetime with a datetime subclass → noon UTC) and place the meeting relative to it"]),
            divider(), h2("Non-Goals"), bullet_list(["No product/engine change"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/tests/test_calendar_sync.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Test passes deterministically regardless of run time; full suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_calendar_sync.py -q"),
            divider(), h2("Dependencies"), p("None."),
            divider(), h2("Next Ticket"), p("LLM-output safety."),
        ),
    },
    {
        "summary": "TIME-191: LLM-output safety in CaptureService",
        "labels": ["backend", "capture", "guardrails"],
        "description": doc(
            h2("Goal"), p("Never trust the model's structured parse output — bound and sanity-check every field."),
            divider(), h2("Scope"), bullet_list([
                "Clamp estimated_minutes to [1,1440] (+ le=1440 on TaskCreate/TaskUpdate)",
                "Null absurd parsed dates (<2000 or >now+5y); clean title (collapse ws, cap 500, never blank)",
                "Rule-based fallback runs through the same cleaning",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No prompt-injection handling (separate ticket)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/capture_service.py, backend/app/schemas/task.py, backend/tests/test_capture.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["999999 min → 1440; year-3000 date → null; blank title → non-empty; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_capture.py -q"),
            divider(), h2("Dependencies"), p("TIME-189."),
            divider(), h2("Next Ticket"), p("Prompt-injection handling."),
        ),
    },
    {
        "summary": "TIME-192: Prompt-injection handling in the capture parse prompt",
        "labels": ["backend", "capture", "guardrails"],
        "description": doc(
            h2("Goal"), p("Treat captured raw_input strictly as data, never instructions, in the LLM parse."),
            divider(), h2("Scope"), bullet_list([
                "Fence raw_input in <user_input>…</user_input> + _PARSE_SYSTEM instruction; strip spoofed fence tags; extract _build_parse_prompt",
                "Non-JSON/echoed output still falls back to the deterministic parse",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No output-content moderation"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/capture_service.py, backend/tests/test_capture.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Prompt fences input + strips spoofed tags; injection-shaped input still yields a sane task; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_capture.py -q"),
            divider(), h2("Dependencies"), p("TIME-191."),
            divider(), h2("Next Ticket"), p("Dedupe."),
        ),
    },
    {
        "summary": "TIME-193: Near-duplicate capture dedupe",
        "labels": ["backend", "capture", "guardrails"],
        "description": doc(
            h2("Goal"), p("Make rapid double-tap / retry captures idempotent — return the same task instead of a duplicate."),
            divider(), h2("Scope"), bullet_list([
                "TaskRepository.find_recent_duplicate (same user, source=capture, active, case-insensitive raw_input, 60s window)",
                "Capture endpoint returns the existing task on a hit, before parsing (skips the LLM call)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to the 30/min rate limiter"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/repositories/task_repository.py, backend/app/api/v1/capture.py, backend/tests/test_capture.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Identical text (case-insensitive) within the window → same task id; different text → distinct tasks; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_capture.py -q"),
            divider(), h2("Dependencies"), p("TIME-189."),
            divider(), h2("Next Ticket"), p("Cross-client cap."),
        ),
    },
    {
        "summary": "TIME-194: Cross-client capture input consistency (2000-char cap)",
        "labels": ["ios", "android", "web", "capture"],
        "description": doc(
            h2("Goal"), p("Enforce the backend's 2000-char raw_input cap on every client so long input is prevented at the source."),
            divider(), h2("Scope"), bullet_list([
                "iOS TextField truncates onChange; web textarea maxLength=2000; Android OutlinedTextField ignores >2000",
                "Document Android's leaner payload (raw_input+tz) as intentional",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No new Android chips/contextual capture UI"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/.../Capture/CaptureView.swift, web/app/app/capture/page.tsx, android/.../capture/CaptureScreen.kt"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["No client can submit >2000 chars; iOS builds, web builds (Android in CI)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense && cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-189."),
            divider(), h2("Next Ticket"), p("Analytics enrichment."),
        ),
    },
    {
        "summary": "TIME-195: Enrich the task_captured analytics event",
        "labels": ["backend", "capture", "analytics"],
        "description": doc(
            h2("Goal"), p("Make Phase-1 capture behavior observable via non-PII analytics properties."),
            divider(), h2("Scope"), bullet_list([
                "Add had_type_hint/had_explicit_time/had_location/auto_scheduled/was_deduped to the consent-gated task_captured event",
                "Dedupe early-return emits the event with was_deduped=true",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No new admin analytics UI"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/api/v1/capture.py, backend/tests/test_monitoring_analytics.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Emitted event carries the enriched props; consent gating unchanged; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_monitoring_analytics.py -q"),
            divider(), h2("Dependencies"), p("TIME-193 (dedupe flag)."),
            divider(), h2("Next Ticket"), p("Phase 2: recommendation telemetry (impression→outcome log)."),
        ),
    },
    {
        "summary": "TIME-196: RecommendationEvent impression→outcome log (repo + migration)",
        "labels": ["backend", "telemetry", "recommendation-engine"],
        "description": doc(
            h2("Goal"), p("Turn the write-only RecommendationEvent audit into a real impression→outcome log (Phase 2 foundation)."),
            divider(), h2("Scope"), bullet_list([
                "Add nullable typed columns (surface, action_type, domain, score, rank, outcome, outcome_at, feedback_id) + indexes; Alembic migration",
                "RecommendationEventRepository.record_impression (dedupe on user/task/surface, no-outcome, 10-min window) + set_outcome",
                "Refactor the 2 existing write sites (/now/why, /now/recommendation) to write via the repo with surface + typed columns",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No metrics endpoint yet; no client changes"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/models/recommendation_event.py, backend/migrations/versions/*, backend/app/repositories/recommendation_event_repository.py, backend/app/api/v1/now.py, backend/tests/test_recommendation_events.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["record_impression inserts + dedupes; set_outcome records reaction; migration head loads; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_recommendation_events.py -q"),
            divider(), h2("Dependencies"), p("Existing RecommendationEvent model."),
            divider(), h2("Next Ticket"), p("Write an impression on /now."),
        ),
    },
    {
        "summary": "TIME-197: Write an impression on /now + surface its id",
        "labels": ["backend", "telemetry"],
        "description": doc(
            h2("Goal"), p("Log an impression of the shown best task on the main /now, and return its id so the client can echo it on feedback."),
            divider(), h2("Scope"), bullet_list([
                "record_impression(surface='now', best-effort, consent-gated on analytics); thread the top pick's action_type/domain/score up from the engine ranking",
                "Add recommendation_event_id to NowResponse",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["Only log rank 0 in v1 (not alternatives)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/api/v1/now.py, backend/tests/test_now.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["With analytics consent /now returns an id + one 'now' impression; without consent → null id + no row; /now never blocks on telemetry"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_now.py -q"),
            divider(), h2("Dependencies"), p("TIME-196."),
            divider(), h2("Next Ticket"), p("Link feedback→outcome."),
        ),
    },
    {
        "summary": "TIME-198: Link feedback → impression → outcome",
        "labels": ["backend", "telemetry"],
        "description": doc(
            h2("Goal"), p("Record how the user reacted to a shown recommendation by linking feedback to its impression."),
            divider(), h2("Scope"), bullet_list([
                "Add optional recommendation_event_id to FeedbackRequest",
                "On feedback, set_outcome(outcome=signal incl agree/disagree, feedback_id) when present",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No completion linkage for non-feedback 'done' paths"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/api/v1/recommendations.py, backend/tests/test_feedback.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Feedback with an event id sets the impression outcome; feedback without one still works (backward-compat); suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_feedback.py -q"),
            divider(), h2("Dependencies"), p("TIME-196/197."),
            divider(), h2("Next Ticket"), p("Acceptance-rate + calibration metrics."),
        ),
    },
    {
        "summary": "TIME-199: Recommendation acceptance-rate + calibration metrics (admin)",
        "labels": ["backend", "telemetry", "admin"],
        "description": doc(
            h2("Goal"), p("Read the impression→outcome log to measure recommendation quality."),
            divider(), h2("Scope"), bullet_list([
                "Repo acceptance_stats (accepted÷shown overall + per action_type) + calibration_buckets (predicted vs observed per confidence decile)",
                "Admin GET /api/v1/admin/recommendations/metrics?days=N",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["Per-user WeeklyInsight acceptance columns deferred (optional follow-up)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/repositories/recommendation_event_repository.py, backend/app/api/v1/admin.py, backend/tests/test_admin.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Metrics report acceptance rate + per-action breakdown + calibration; 403 for non-admin; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_admin.py -q"),
            divider(), h2("Dependencies"), p("TIME-196/197/198."),
            divider(), h2("Next Ticket"), p("Privacy export/purge."),
        ),
    },
    {
        "summary": "TIME-200: Privacy export + purge for recommendation_events",
        "labels": ["backend", "privacy"],
        "description": doc(
            h2("Goal"), p("Include the impression→outcome log in the GDPR data export (deletion already cascades)."),
            divider(), h2("Scope"), bullet_list(["Add recommendation_events to privacy_service _USER_DATA"]),
            divider(), h2("Non-Goals"), bullet_list(["No change to deletion (FK cascade already covers it)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/privacy_service.py, backend/tests/test_privacy.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Export includes recommendation_events; account delete removes them; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_privacy.py -q"),
            divider(), h2("Dependencies"), p("TIME-196."),
            divider(), h2("Next Ticket"), p("Clients echo the impression id."),
        ),
    },
    {
        "summary": "TIME-201: Clients echo the impression id on feedback",
        "labels": ["ios", "android", "web", "telemetry"],
        "description": doc(
            h2("Goal"), p("Close the loop: clients read recommendation_event_id from /now and send it on feedback so outcomes link to impressions."),
            divider(), h2("Scope"), bullet_list([
                "iOS NowContext + FeedbackBody; web NowResponse + sendFeedback; Android NowContext + FeedbackRequest",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["'Done' via task PATCH stays a separate path (not linked)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/.../Now/NowViewModel.swift, web/lib/appTypes.ts, web/app/app/page.tsx, android/.../now/NowViewModel.kt"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Feedback payloads include the id when available; iOS builds, web builds (Android in CI)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense && cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-197/198."),
            divider(), h2("Next Ticket"), p("Phase 3: learning (revive apply_feedback)."),
        ),
    },
    {
        "summary": "TIME-202: Revive the apply_feedback seam (learning from telemetry)",
        "labels": ["backend", "recommendation-engine", "learning"],
        "description": doc(
            h2("Goal"), p("Wire the built-but-unused apply_feedback layer, fed by the Phase-2 impression→outcome log, so the engine boosts/penalizes action types the user accepts/rejects."),
            divider(), h2("Scope"), bullet_list([
                "build_feedback_summary(db, user, now, tz) → FeedbackSummary(accepts/rejects per action_type + recently_dismissed) from recommendation_events",
                "Apply in the main /now fast path (_engine_rank_tasks), /now/recommendation, and both push run_engine sites",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["Empty history must be a no-op (existing behavior unchanged)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation/feedback/build_summary.py, backend/app/api/v1/now.py, backend/app/services/push/push_service.py, backend/tests/test_recommendation_events.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Summary counts accepts/rejects per action_type; feedback influences ranking for users with history; no-history = no-op; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_recommendation_events.py -q"),
            divider(), h2("Dependencies"), p("Phase 2 telemetry (TIME-196..201)."),
            divider(), h2("Next Ticket"), p("Accepts boost."),
        ),
    },
    {
        "summary": "TIME-203: USER_OFTEN_ACCEPTS boost in scoring",
        "labels": ["backend", "recommendation-engine", "learning"],
        "description": doc(
            h2("Goal"), p("Make consistently-accepted action types rank higher (symmetry with the reject penalty)."),
            divider(), h2("Scope"), bullet_list(["Add a bounded boost (-15 penalty) for USER_OFTEN_ACCEPTS_THIS_ACTION in penalties.py"]),
            divider(), h2("Non-Goals"), bullet_list(["Must stay bounded so hard safety rules dominate"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation/scoring/penalties.py, backend/tests/test_recommendation_engine_selection.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["The accepts code lowers a candidate's penalty by 15; safety penalties still dominate; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_recommendation_engine_selection.py -q"),
            divider(), h2("Dependencies"), p("TIME-202."),
            divider(), h2("Next Ticket"), p("Time-of-day rule."),
        ),
    },
    {
        "summary": "TIME-204: Time-of-day learning rule",
        "labels": ["backend", "recommendation-engine", "learning"],
        "description": doc(
            h2("Goal"), p("Avoid an action type at the time of day the user repeatedly rejects it."),
            divider(), h2("Scope"), bullet_list([
                "build_feedback_summary buckets rejections by the local part_of_day of the impression; avoided_now = action types with >=3 rejects at the current part of day",
                "apply_feedback tags AVOIDED_AT_THIS_TIME; penalties.py +20; callers pass the user's timezone",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["Fuller acceptance-rate-scaled user_preference_fit deferred (optional)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation/feedback/{build_summary,apply_feedback}.py, backend/app/services/recommendation/{types,scoring/penalties}.py, backend/app/api/v1/now.py, backend/app/services/push/push_service.py, tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["3 rejects at the current time-of-day → avoided_now; AVOIDED_AT_THIS_TIME adds +20; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_recommendation_events.py tests/test_recommendation_engine_selection.py -q"),
            divider(), h2("Dependencies"), p("TIME-202/203."),
            divider(), h2("Next Ticket"), p("(optional) per-user WeeklyInsight acceptance columns; surface learned preferences."),
        ),
    },
    {
        "summary": "TIME-205: 'What TimeSense has learned' endpoint",
        "labels": ["backend", "learning", "transparency"],
        "description": doc(
            h2("Goal"), p("Surface the engine's learned preferences to users as plain-language statements (transparency)."),
            divider(), h2("Scope"), bullet_list([
                "GET /api/v1/recommendations/learned (not premium-gated) → prefers/avoids/avoids_at_time per action_type from recommendation_events",
                "Humanized labels; >=3-reaction threshold; capped at 6; based_on = reaction count",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No editing of learned preferences"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/learned_preferences_service.py, backend/app/api/v1/recommendations.py, backend/tests/test_feedback.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["prefers/avoids derived from history; empty for a new user; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_feedback.py -q"),
            divider(), h2("Dependencies"), p("Phase 2/3 (telemetry + learning)."),
            divider(), h2("Next Ticket"), p("iOS + web surfaces."),
        ),
    },
    {
        "summary": "TIME-206: Surface learned preferences on iOS",
        "labels": ["ios", "learning", "transparency"],
        "description": doc(
            h2("Goal"), p("Show 'What TimeSense has learned' in the Learned Patterns screen."),
            divider(), h2("Scope"), bullet_list(["Fetch /api/v1/recommendations/learned (best-effort) + render a section of plain-language rows above the routines"]),
            divider(), h2("Non-Goals"), bullet_list(["No editing"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Settings/LearnedAssumptionsView.swift, LearnedAssumptionsViewModel.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Learned section renders when preferences exist; failure doesn't block routines; iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-205."),
            divider(), h2("Next Ticket"), p("Web surface."),
        ),
    },
    {
        "summary": "TIME-207: Surface learned preferences on web",
        "labels": ["web", "learning", "transparency"],
        "description": doc(
            h2("Goal"), p("Show 'What TimeSense has learned' on the web Insights page."),
            divider(), h2("Scope"), bullet_list(["Best-effort fetch of /api/v1/recommendations/learned + a card below the weekly stats"]),
            divider(), h2("Non-Goals"), bullet_list(["No Android in this ticket (CI-verified follow-up)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/insights/page.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Learned card renders when preferences exist; next build succeeds; verified via screenshot"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-205."),
            divider(), h2("Next Ticket"), p("(optional) Android learned surface in CI."),
        ),
    },
    {
        "summary": "TIME-208: Acceptance-rate-scaled user_preference_fit",
        "labels": ["backend", "recommendations", "learning"],
        "description": doc(
            h2("Goal"), p("Make user_preference_fit a continuous learned signal (observed acceptance rate) instead of a binary +0.2 bump."),
            divider(), h2("Scope"), bullet_list([
                "In apply_feedback_adjustments: once an action type has >=PREFERENCE_MIN_SAMPLES (5) reactions, set user_preference_fit = acc/(acc+rej), clamped 0..1",
                "Below the sample floor it stays neutral (0.5); reject/accept reason codes unchanged",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No weight changes; no new reason codes"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation/feedback/apply_feedback.py, backend/tests/test_recommendation_engine_selection.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["8/2 reactions -> 0.8; <5 reactions -> stays 0.5; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest -q"),
            divider(), h2("Dependencies"), p("Phase 2/3 (telemetry + learning)."),
            divider(), h2("Next Ticket"), p("Per-user WeeklyInsight acceptance columns."),
        ),
    },
    {
        "summary": "TIME-209: Per-user recommendation acceptance columns on WeeklyInsight",
        "labels": ["backend", "insights", "telemetry"],
        "description": doc(
            h2("Goal"), p("Record per-user recommendation quality on each weekly insight from the impression->outcome log."),
            divider(), h2("Scope"), bullet_list([
                "Add recommendations_shown, recommendations_accepted, recommendation_acceptance_rate, mean_confidence to WeeklyInsight + Alembic migration",
                "Populate in InsightsService._generate via acceptance_stats(start,end,user_id) scoped to the user's week",
                "Null rate/mean_confidence when no impressions (same rule as completion_rate); _summarize gains mean_confidence",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No backfill of past weeks"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/models/insight.py, app/schemas/insight.py, app/services/insights_service.py, app/repositories/recommendation_event_repository.py, migrations/, tests/test_insights.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Columns populate correctly; null when no impressions; single alembic head; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && alembic heads && pytest tests/test_insights.py -q"),
            divider(), h2("Dependencies"), p("TIME-196 (impression log), TIME-046 (weekly insights)."),
            divider(), h2("Next Ticket"), p("Surface acceptance stat in Insights UI."),
        ),
    },
    {
        "summary": "TIME-210: Surface recommendation acceptance on Insights (iOS + web)",
        "labels": ["ios", "web", "insights"],
        "description": doc(
            h2("Goal"), p("Show a 'Recommendations accepted' stat on the weekly Insights screen."),
            divider(), h2("Scope"), bullet_list([
                "iOS StatsGrid: new StatRow with rate + 'N of M shown' detail line",
                "Web insights grid: new stat card with a muted 'N of M shown' subline",
                "Render only when recommendation_acceptance_rate is non-null",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No Android in this ticket (CI-verified follow-up)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/.../Insights/InsightsView.swift, InsightsViewModel.swift, web/app/app/insights/page.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Card renders when rate present, hidden otherwise; iOS builds; web build clean"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense && cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-209."),
            divider(), h2("Next Ticket"), p("(optional) Android acceptance surface in CI."),
        ),
    },
    {
        "summary": "TIME-211: Fix inverted geofence arrive/leave notifications",
        "labels": ["ios", "location", "bug"],
        "description": doc(
            h2("Goal"), p("Fix a consistent inversion: leaving home fires 'You're at Home' and arriving fires 'You left Home'. Derive the crossing direction from the user's actual current position, not a stale point-in-region check."),
            divider(), h2("Scope"), bullet_list([
                "LocationService.swift: on didEnter/didExit, request a fresh location and compute inside/outside from distance to the place center (supersedes the TIME-105 requestState mechanism, whose CLRegionState reflects the stale pre-crossing location)",
                "Carry the event direction (pendingEvents: [regionId: enteredEvent]) as a fallback",
                "Resolve crossings in didUpdateLocations (fresh-fix distance) with the existing dedup + backend place-sync + notify; fall back to the event direction in didFailWithError",
                "Preserve the stationary seed/place-sync path (registerGeofence/reregisterGeofences requestState -> didDetermineState, no notify)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No Android/web (no geofencing there)", "No change to notification copy or the LLM recommendation branch"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Core/Location/LocationService.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "Leaving home -> 'You left Home' (or LLM nudge), never 'You're at'",
                "Arriving home -> 'You're at Home', never 'You left'",
                "One notification per crossing (dedup intact); backend place still updates; iOS builds",
            ]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense\n# then on-device: walk out/in past the geofence and check the notification text"),
            divider(), h2("Dependencies"), p("TIME-103/105 (location subsystem + geofence notifications)."),
            divider(), h2("Next Ticket"), p("(none — bug fix)"),
        ),
    },
    {
        "summary": "TIME-212: 'Why this recommendation?' sheet — summary at top",
        "labels": ["ios", "recommendations", "bug"],
        "description": doc(
            h2("Goal"), p("On the iOS 'Why this recommendation?' sheet the plain-language Summary renders at the very bottom; move it to the top so users read the takeaway first."),
            divider(), h2("Scope"), bullet_list([
                "RecommendationExplanationSheet (NowView.swift): move the Summary block above 'Signals analyzed' (directly under the recommended-action header card)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No copy/content changes; no backend changes; Signals/Alternatives order unchanged"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Now/NowView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "Summary appears near the top of the sheet (under the action header), before Signals analyzed",
                "iOS builds",
            ]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-175 / recommendation explanation sheet."),
            divider(), h2("Next Ticket"), p("(none — bug fix)"),
        ),
    },
    {
        "summary": "TIME-213: Score-based, consistent recommendation confidence",
        "labels": ["backend", "recommendations", "bug"],
        "description": doc(
            h2("Goal"), p("Make the confidence % reflect the pick's actual strength (its 0-100 engine score) and show ONE consistent value on every surface, replacing the flat 0.50-0.95 heuristic and the hardcoded per-candidate literals."),
            divider(), h2("Scope"), bullet_list([
                "New score_to_confidence(score) helper in scoring/score.py: round(min(0.95, max(0.30, score/100)), 2)",
                "/now: confidence = score_to_confidence(best_meta['score'])",
                "/now/recommendation (select.py): confidence = score_to_confidence(best.score) (also feeds eligible_for_push; thresholds align at 75/0.75 so push behavior is preserved)",
                "/now/why: thread the target task's score through _engine_rank_tasks/_ranked_candidates + build_explanation and use score_to_confidence",
                "Remove the now-unused compute_confidence heuristic",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No 'margin over runner-up' nuance (deferred)", "No iOS/web change (clients already render confidence*100)", "Leave vestigial per-candidate confidence= literals (optional later cleanup)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation/scoring/score.py, backend/app/api/v1/now.py, backend/app/services/recommendation/selection/select.py, backend/app/services/recommendation_explainer.py, backend/tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "/now, /now/why, /now/recommendation all report the same score-based confidence for the same pick",
                "Strong pick reads high (~0.8), weak pick low (~0.4); mapping floored 0.30, capped 0.95",
                "Push eligibility unchanged at the score>=75 boundary; suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && pytest -q"),
            divider(), h2("Dependencies"), p("TIME-112/113 (engine scoring), TIME-117/118 (explanation + recommendation endpoint)."),
            divider(), h2("Next Ticket"), p("(optional) margin-over-runner-up nuance."),
        ),
    },
    {
        "summary": "TIME-214: Email integration — Gmail OAuth connect + EmailIntegration",
        "labels": ["backend", "integrations", "email"],
        "description": doc(
            h2("Goal"), p("First slice of email->task detection: connect a user's Gmail account read-only via OAuth and store the tokens encrypted, reusing the existing integration/OAuth pattern."),
            divider(), h2("Scope"), bullet_list([
                "gmail_oauth.py: build_authorize_url/exchange_code/refresh_access_token, SCOPES=openid email gmail.readonly, reuses google_client_id/secret, own gmail_redirect_uri",
                "EmailIntegration model (mirror SlackIntegration): provider, access_token/refresh_token (EncryptedString), token_expires_at, is_active, sync_cursor",
                "EmailIntegrationRepository (get_active/upsert/deactivate); EmailService.connect/disconnect",
                "Router: /integrations/gmail/authorize (PremiumUser) + /gmail/callback (stores via EmailService, mirrors the bespoke Slack callback)",
                "Alembic migration for email_integrations; register model + config gmail_redirect_uri",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No fetching/scanning yet (TIME-215/216)", "No Outlook", "No client UI (TIME-217)", "Read-only — never send/modify mail"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/integrations/gmail_oauth.py, app/models/email_integration.py, app/repositories/email_repository.py, app/services/email_service.py, app/api/v1/integrations.py, app/core/config.py, app/models/__init__.py, migrations/, tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "GET /integrations/gmail/authorize returns a Google consent URL (premium-gated; 503 if unconfigured)",
                "Callback exchanges the code and stores an encrypted EmailIntegration; single alembic head; suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && alembic heads && pytest tests/test_email_integration.py -q"),
            divider(), h2("Dependencies"), p("TIME-177/181 (integration OAuth pattern), TIME-050 (action-item detection)."),
            divider(), h2("Next Ticket"), p("TIME-215: email_content consent + Gmail fetch + token refresh."),
        ),
    },
    {
        "summary": "TIME-215: Email — email_content consent + read-only Gmail fetch + token refresh",
        "labels": ["backend", "integrations", "email", "privacy"],
        "description": doc(
            h2("Goal"), p("Fetch recent unread Primary emails read-only using the stored Gmail token (subject/sender/snippet only, never the body), gated on a new email_content consent, refreshing the access token when expired."),
            divider(), h2("Scope"), bullet_list([
                "Add email_content to VALID_CONSENT_TYPES + ConsentRecord docstring",
                "EmailSourceProvider ABC + EmailMessage (subject/sender/snippet/message_id/thread_id); GmailEmailSource fetches is:unread newer_than:7d category:primary via format=metadata (no body)",
                "EmailService: refresh access token via gmail_oauth.refresh_access_token when token_expires_at is past, then upsert; fetch_recent(user_id) -> list[EmailMessage]",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No detection/pending/approve yet (TIME-216)", "Never fetch or store the full body", "No background job"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/integrations/email_source_base.py, app/integrations/gmail_source.py, app/services/email_service.py, app/repositories/consent_repository.py, app/models/consent.py, tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "GmailEmailSource returns EmailMessage(subject, sender, snippet, ids) from a mocked Gmail response; never requests the full body",
                "EmailService refreshes an expired token before fetching; email_content is a valid consent type; suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_email_fetch.py -q"),
            divider(), h2("Dependencies"), p("TIME-214 (Gmail connect)."),
            divider(), h2("Next Ticket"), p("TIME-216: scan -> detect -> pending EmailActionItem + confirm/reject API."),
        ),
    },
    {
        "summary": "TIME-216: Email — scan -> detect -> pending EmailActionItem + confirm/reject API",
        "labels": ["backend", "integrations", "email"],
        "description": doc(
            h2("Goal"), p("Turn fetched emails into pending task suggestions via the shared action-item detector, and expose the approval-gated confirm/reject API. Detected items NEVER become Tasks without user approval."),
            divider(), h2("Scope"), bullet_list([
                "EmailActionItem model (mirror SlackActionItem): message_id (dedup), thread_id, subject, sender, source_text(snippet), detected_title/priority/estimated_minutes, status, created_task_id; migration + repo",
                "EmailService.scan(user_id): email_content consent-gated + connected check -> fetch_recent -> ActionItemDetectionService.detect(subject+snippet) -> dedup -> pending items; confirm()=only Task path (source='email'); reject()",
                "Router /email/scan (Premium), /email/pending, /email/actions/{id}/confirm, /email/actions/{id}/reject; schemas; register router",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No client UI (TIME-217)", "No due-date extraction", "Never auto-create tasks"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/models/email_integration.py, app/repositories/email_repository.py, app/services/email_service.py, app/schemas/email.py, app/api/v1/email.py, app/api/v1/__init__.py, migrations/, tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "scan creates pending items (not Tasks); confirm creates exactly one Task with source='email'; reject creates none; dedup on message_id",
                "scan without email_content consent -> 403; without connection -> 404; premium-gated; suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && alembic heads && pytest tests/test_email_scan.py -q"),
            divider(), h2("Dependencies"), p("TIME-215 (fetch + consent), TIME-050 (detection)."),
            divider(), h2("Next Ticket"), p("TIME-217: iOS Gmail connect + review screen."),
        ),
    },
    {
        "summary": "TIME-217: iOS — Gmail connect + 'Email tasks' review screen",
        "labels": ["ios", "integrations", "email"],
        "description": doc(
            h2("Goal"), p("Make email->task detection usable on iPhone: connect Gmail from Connections and review/approve detected tasks."),
            divider(), h2("Scope"), bullet_list([
                "ConnectionsView: add a Gmail (read-only) connect row + a NavigationLink to the review screen",
                "New EmailTasksView + view model: explicit email_content consent grant (GET/POST /consent), 'Scan for tasks' (POST /email/scan), pending list with Approve (confirm) / Dismiss (reject)",
                "Backend: add email_content to the ConsentType Literal in schemas/consent.py (POST /consent/ would 422 otherwise)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No Android/web (follow-up)", "No background scan", "No nagging — explicit user-triggered review"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Settings/ConnectionsView.swift, ios/TimeSense/Features/Settings/EmailTasksView.swift (new), backend/app/schemas/consent.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "Gmail connect row opens the OAuth sheet; review screen grants consent, scans, lists detected items, approve creates a Task, dismiss removes it",
                "iOS builds; backend suite green",
            ]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense && cd backend && pytest -q"),
            divider(), h2("Dependencies"), p("TIME-214/215/216 (email backend)."),
            divider(), h2("Next Ticket"), p("(follow-up) Outlook; Android + web review screens; background scan."),
        ),
    },
    {
        "summary": "TIME-218: Premium test allowlist (test premium features past the intro trial)",
        "labels": ["backend", "subscriptions", "devx"],
        "description": doc(
            h2("Goal"), p("Let developers/testers use Premium-gated features regardless of the 14-day intro-trial window, so premium UI + PremiumUser-gated endpoints are testable on aged accounts."),
            divider(), h2("Scope"), bullet_list([
                "config: premium_test_emails (comma-separated, empty by default)",
                "SubscriptionService.is_premium: also True when the user's email is in the allowlist (checked after sub + intro-trial); unblocks both the app entitlement and every PremiumUser endpoint",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to real subscription/billing logic", "Empty by default -> no production behavior change", "Not a client change"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/core/config.py, backend/app/services/subscription_service.py, backend/tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "An allowlisted email is premium even with no subscription and an expired intro trial",
                "Empty allowlist -> unchanged behavior; a non-listed, past-trial, no-sub user stays non-premium; suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_subscriptions.py -q"),
            divider(), h2("Dependencies"), p("TIME-178 (intro trial)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-219: Now/Today color refresh — warm variety + warmer-dark ground",
        "labels": ["ios", "design"],
        "description": doc(
            h2("Goal"), p("Now & Today read as green/blue/violet on flat near-black. Add warm accents (orange/red/amber/yellow), spread them across task types, and lift the background to a 'warmer dark' ground."),
            divider(), h2("Scope"), bullet_list([
                "Cosmic palette: add orange/red/yellow; CosmicBackground -> lifted navy + warm amber glow (warmer-dark ground)",
                "taskCategoryStyle (shared by Now+Today): map task types across the wheel (errand=orange, quick/personal=yellow, deadline=red, email=amber, focus=blue, health=green, meeting=violet)",
                "heroAccent/domainAccent warm mappings; TodayView group colors warm->cool day arc; high-priority pill -> red",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No light theme", "No non-color layout changes", "Backend unchanged"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Core/Design/CosmicComponents.swift, ios/TimeSense/Features/Now/NowView.swift, ios/TimeSense/Features/Today/TodayView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Now/Today show varied warm+cool accents; background is warmer-dark (not flat black); iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-148..165 (cosmic palette)."),
            divider(), h2("Next Ticket"), p("TIME-220: swipe between tabs."),
        ),
    },
    {
        "summary": "TIME-220: Swipe between bottom tabs",
        "labels": ["ios", "navigation"],
        "description": doc(
            h2("Goal"), p("Let users swipe horizontally to move across the Now/Today/Capture/Insights/Settings tabs, in addition to tapping the tab bar."),
            divider(), h2("Scope"), bullet_list([
                "MainTabView: a low-priority horizontal DragGesture that moves to the adjacent tab (predominantly-horizontal, distance-thresholded, so it doesn't fight vertical scrolling or Today's row swipe-to-reveal)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No paged TabView (keeps the native tab bar)", "No wrap-around past the first/last tab"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/App/MainTabView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A horizontal swipe changes tabs; vertical scroll + Today row swipe still work; iOS builds (gesture feel verified on device)"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("(none)"),
            divider(), h2("Next Ticket"), p("TIME-221: Now tasks card -> Today."),
        ),
    },
    {
        "summary": "TIME-221: Now 'Tasks' card taps through to Today",
        "labels": ["ios", "navigation"],
        "description": doc(
            h2("Goal"), p("Make the Tasks context card on Now tappable so it jumps to the Today task list."),
            divider(), h2("Scope"), bullet_list([
                "NowView/ContextGrid: wrap the 'Tasks' ContextCard in a tap that sets appState.selectedTab = .today",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to other context cards", "No deep link to a specific task"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Now/NowView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Tapping the Now Tasks card switches to the Today tab; iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("(none)"),
            divider(), h2("Next Ticket"), p("TIME-222: calendar events -> tasks."),
        ),
    },
    {
        "summary": "TIME-222: Calendar events become editable tasks in the list",
        "labels": ["ios", "backend", "calendar", "tasks"],
        "description": doc(
            h2("Goal"), p("Bring the user's connected/synced calendar events into the task list as real editable tasks (with their start time), so the day lives in one place."),
            divider(), h2("Scope"), bullet_list([
                "Backend: endpoint to convert synced calendar events in a window into Tasks (title=event title, scheduled_start=event start, source='calendar'), deduped so re-import doesn't duplicate (store the source event id)",
                "iOS: trigger import (on calendar sync / a control) so events show in Today as tasks",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No two-way write-back to the calendar", "No recurring-event expansion beyond the synced window"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/*, app/api/v1/calendar.py, app/models/task.py (source event id), migrations/, ios TodayView/CalendarSyncService, tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A synced event appears as an editable task with its start time; re-import doesn't duplicate; suite green; iOS builds"]),
            divider(), h2("Verification"), code_block("cd backend && pytest -q && cd .. && xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("Calendar sync (SyncedCalendarEvent)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-223: OAuth callback can return to the web app (platform-aware)",
        "labels": ["backend", "integrations", "web"],
        "description": doc(
            h2("Goal"), p("Let a browser-initiated OAuth connect finish on the web app. Today the callback 302s to timesense://... (mobile deep link) which a browser can't follow."),
            divider(), h2("Scope"), bullet_list([
                "config: oauth_web_success_redirect / oauth_web_failure_redirect (default the web /app/connections page)",
                "oauth_state: sign_state(platform='mobile'); OAuthState dataclass + decode_state (full verify) + platform_from_state (best-effort); verify_state stays backward-compatible (returns user_id)",
                "integrations.py: authorize endpoints take platform query param; _success/_failure pick mobile deep link vs the web URL from the state's platform (default mobile → iOS unchanged)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No arbitrary return_to (platform enum + config target only — no open redirect)", "No web UI (TIME-224/225)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/core/config.py, app/core/oauth_state.py, app/api/v1/integrations.py, tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "authorize?platform=web signs platform=web; a web-state callback 302s to the web URL (with &provider=)",
                "mobile / no-platform callback still 302s to timesense://... (unchanged); suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_integrations_oauth.py -q"),
            divider(), h2("Dependencies"), p("TIME-177/214 (OAuth handshakes)."),
            divider(), h2("Next Ticket"), p("TIME-224: web Connections page."),
        ),
    },
    {
        "summary": "TIME-224: Web Connections page (connect Google/Outlook/Gmail/Slack)",
        "labels": ["web", "integrations"],
        "description": doc(
            h2("Goal"), p("A web Connections page to connect the calendar/Slack/Gmail providers via OAuth."),
            divider(), h2("Scope"), bullet_list([
                "web/app/app/connections/page.tsx: provider rows; Connect -> GET /integrations/{provider}/authorize?platform=web -> window.location = authorize_url; handle ?status=connected return, 403 (premium), 503 (unconfigured)",
                "Add a Connections tab to layout TABS; Gmail row links to the email review page",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No per-provider connected-state endpoint (infer from return param)", "No email review here (TIME-225)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/connections/page.tsx, web/app/app/layout.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Connect opens the provider consent URL; return shows connected; premium/unconfigured handled; npm run build clean"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-223 (web-return)."),
            divider(), h2("Next Ticket"), p("TIME-225: web email review."),
        ),
    },
    {
        "summary": "TIME-225: Web Email-tasks review page (scan + approve)",
        "labels": ["web", "integrations", "email"],
        "description": doc(
            h2("Goal"), p("A web page to grant email consent, scan Gmail for tasks, and approve/dismiss the detected ones."),
            divider(), h2("Scope"), bullet_list([
                "web/app/app/email/page.tsx: email_content consent gate (GET/POST /consent); Scan for tasks (POST /email/scan); pending list (GET /email/pending) with Add task (confirm) / Dismiss (reject)",
                "Branch on 403 (consent/premium) and 404 (not connected -> link to Connections); reachable from the Gmail row on Connections",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No top-level Email tab (avoid nav crowding)", "No background scan"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/email/page.tsx"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Consent -> scan -> pending list -> approve creates a task / dismiss removes it; gates handled; npm run build clean"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("TIME-216 (email API), TIME-224 (connections)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-226: Notion OAuth handshake (connect via consent, not a pasted token)",
        "labels": ["backend", "integrations", "notion"],
        "description": doc(
            h2("Goal"), p("Add the missing Notion OAuth handshake so a user can connect Notion by consent (the import flow already exists; today /notion/connect only accepts a pasted token)."),
            divider(), h2("Scope"), bullet_list([
                "notion_oauth.py (mirror slack_oauth): build_authorize_url / exchange_code (Basic-auth token endpoint) / is_configured; NotionTokenResult(access_token, workspace_id)",
                "config: notion_redirect_uri",
                "integrations.py: /integrations/notion/authorize (PremiumUser, platform-aware) + /notion/callback storing via NotionService.connect (platform-aware return, TIME-223)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No change to the existing scan/import approval flow", "No client UI here (TIME-227)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/integrations/notion_oauth.py, app/core/config.py, app/api/v1/integrations.py, tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "GET /integrations/notion/authorize returns a Notion consent URL (premium, 503 if unconfigured)",
                "callback exchanges the code and stores a NotionIntegration; platform=web returns to web; suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_integrations_oauth.py tests/test_notion.py -q"),
            divider(), h2("Dependencies"), p("TIME-051 (Notion import), TIME-223 (OAuth web-return)."),
            divider(), h2("Next Ticket"), p("TIME-227: Notion in the Connect UIs (web + iOS)."),
        ),
    },
    {
        "summary": "TIME-227: Notion in the Connect UIs (web + iOS)",
        "labels": ["web", "ios", "integrations", "notion"],
        "description": doc(
            h2("Goal"), p("Let users connect Notion from the web Connections page and the iOS Connections screen."),
            divider(), h2("Scope"), bullet_list([
                "web/app/app/connections/page.tsx: add a Notion provider row (uses the generic /integrations/{provider}/authorize?platform=web flow)",
                "ios ConnectionsView: add a Notion connect row (generic authorize flow)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No Notion import-review UI (follow-up)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/app/app/connections/page.tsx, ios/TimeSense/Features/Settings/ConnectionsView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Notion appears on web + iOS Connections; Connect opens the consent flow; web build + iOS build clean"]),
            divider(), h2("Verification"), code_block("cd web && npm run build && cd .. && xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-226 (Notion handshake)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-228: Deploy — backend container prod server + hardening + migrate-on-deploy",
        "labels": ["backend", "deployment", "infra"],
        "description": doc(
            h2("Goal"), p("Make the backend image production-grade: a multi-worker server, non-root + healthcheck hardening, and migrations applied on the web role's startup."),
            divider(), h2("Scope"), bullet_list([
                "requirements.txt: add gunicorn; Dockerfile CMD -> gunicorn with uvicorn workers (WEB_CONCURRENCY)",
                "Dockerfile: install curl (compose healthcheck), non-root USER, HEALTHCHECK on /api/v1/health",
                "entrypoint.sh: if RUN_MIGRATIONS=1 run alembic upgrade head, then exec CMD (web migrates, worker/beat don't)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No app code change", "Docker build not run in this session (user verifies)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/Dockerfile, backend/entrypoint.sh, backend/requirements.txt"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Image runs gunicorn as non-root; RUN_MIGRATIONS=1 applies migrations then starts; pytest green; docker build succeeds (user-run)"]),
            divider(), h2("Verification"), code_block("cd backend && pytest -q   # app unaffected; docker build run by the user"),
            divider(), h2("Dependencies"), p("Existing Dockerfile/compose."),
            divider(), h2("Next Ticket"), p("TIME-229: web container."),
        ),
    },
    {
        "summary": "TIME-229: Deploy — web (Next.js) container",
        "labels": ["web", "deployment", "infra"],
        "description": doc(
            h2("Goal"), p("Containerize the Next.js companion for deployment."),
            divider(), h2("Scope"), bullet_list([
                "next.config.ts: output: 'standalone'",
                "web/Dockerfile: multi-stage (deps->build->runner), non-root, runs .next/standalone/server.js; NEXT_PUBLIC_API_BASE_URL + Firebase as build args (NEXT_PUBLIC_* baked at build)",
                "web/.dockerignore",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No app code change", "Docker build run by the user"]),
            divider(), h2("Files Likely Changed"), bullet_list(["web/next.config.ts, web/Dockerfile, web/.dockerignore"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["npm run build clean (emits .next/standalone); docker build web succeeds (user-run)"]),
            divider(), h2("Verification"), code_block("cd web && npm run build"),
            divider(), h2("Dependencies"), p("(none)"),
            divider(), h2("Next Ticket"), p("TIME-230: prod config + client URLs."),
        ),
    },
    {
        "summary": "TIME-230: Deploy — prod env template + client prod-URL wiring",
        "labels": ["backend", "ios", "web", "deployment"],
        "description": doc(
            h2("Goal"), p("Document every prod override and point the clients at the prod API."),
            divider(), h2("Scope"), bullet_list([
                ".env.example: a 'PRODUCTION — override these' section (APP_ENV=production, real SECRET_KEY/TOKEN_ENCRYPTION_KEY, DATABASE_URL/REDIS_URL, CORS_ORIGINS, Firebase, OPENAI, Stripe live, APNS_USE_SANDBOX=false, OAuth *_REDIRECT_URI + OAUTH_WEB_* off localhost, GOOGLE_MAPS_API_KEY, SENTRY_DSN)",
                "ios APIClient.swift: Release base URL -> prod domain (drop the TODO; keep API_BASE_URL override); note aps-environment flips at distribution",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No secret values (user sets)", "No behavior change"]),
            divider(), h2("Files Likely Changed"), bullet_list([".env.example, ios/TimeSense/Core/API/APIClient.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Every must-set prod var documented; iOS Release URL is the prod domain; pytest green; iOS builds"]),
            divider(), h2("Verification"), code_block("cd backend && pytest -q && cd .. && xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-223 (oauth_web_* redirects)."),
            divider(), h2("Next Ticket"), p("TIME-231: Render blueprint + DEPLOY.md."),
        ),
    },
    {
        "summary": "TIME-231: Deploy — Render blueprint + DEPLOY.md",
        "labels": ["deployment", "infra", "docs"],
        "description": doc(
            h2("Goal"), p("A one-file Render Blueprint that stands up the whole backend (api + worker + beat + Postgres + Redis) and a step-by-step deploy guide."),
            divider(), h2("Scope"), bullet_list([
                "render.yaml: Docker web service (healthCheckPath /api/v1/health, RUN_MIGRATIONS=1) + worker + beat (celery) + managed Postgres + Redis; DATABASE_URL/REDIS_URL wired; secrets sync:false; optional Next web service",
                "docs/DEPLOY.md: connect repo -> Blueprint -> set secrets -> domain/TLS -> register prod OAuth redirect URIs -> point clients -> user-owned checklist (rotate Android key, OpenAI billing, Maps key, store/legal), cross-linked to release_checklist.md",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No actual deploy (user runs it)", "No CI/CD (deferred)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["render.yaml, docs/DEPLOY.md"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["render.yaml is valid YAML referencing the real Dockerfiles/commands; DEPLOY.md matches the manifest and lists the user-owned steps"]),
            divider(), h2("Verification"), code_block("python -c \"import yaml,sys; yaml.safe_load(open('render.yaml')); print('ok')\""),
            divider(), h2("Dependencies"), p("TIME-228/229/230."),
            divider(), h2("Next Ticket"), p("(follow-up) CI/CD; Redis-backed rate limiter."),
        ),
    },
    {
        "summary": "TIME-232: Slim the Render blueprint for cost (~$48 -> ~$20/mo)",
        "labels": ["deployment", "infra", "cost"],
        "description": doc(
            h2("Goal"), p("Reduce the Render blueprint from 6 billable pieces to a lean always-on setup (~$20/mo) without losing functionality."),
            divider(), h2("Scope"), bullet_list([
                "Merge worker + beat into one worker service running embedded beat (celery worker --beat) — keep it at 1 instance",
                "Redis -> free plan; remove the timesense-web service (deploy web on Vercel free instead)",
                "Keep API + combined worker on Starter (always-on) + Postgres basic (durable)",
                "DEPLOY.md: reflect merged worker/beat, Redis free, a short Vercel-for-web section, and the ~$20/mo note",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No app code change", "No functional loss (scheduled jobs still run via embedded beat)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["render.yaml, docs/DEPLOY.md"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["render.yaml valid YAML; worker runs embedded beat; web service removed; Redis free; DEPLOY.md updated with Vercel + cost"]),
            divider(), h2("Verification"), code_block("python -c \"import yaml; yaml.safe_load(open('render.yaml')); print('ok')\""),
            divider(), h2("Dependencies"), p("TIME-231 (blueprint)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-233: Auto-wire DATABASE_URL from managed Postgres (fix failed deploy)",
        "labels": ["backend", "deployment", "infra"],
        "description": doc(
            h2("Goal"), p("Remove the manual DATABASE_URL step that caused the Render API deploy to fail: coerce the async driver in config so the plain provider URL works, and wire DATABASE_URL from the managed Postgres in the blueprint."),
            divider(), h2("Scope"), bullet_list([
                "config.py: field_validator coerces postgres:// / postgresql:// -> postgresql+asyncpg:// for database_url (explicit +driver untouched)",
                "render.yaml: set DATABASE_URL via fromDatabase (connectionString) on api + worker; remove it from the sync:false secrets group so nothing needs hand-entering to boot",
                "test: the coercion",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No other behavior change"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/core/config.py, render.yaml, backend/tests/"]),
            divider(), h2("Acceptance Criteria"), bullet_list([
                "settings.database_url is +asyncpg even when given a plain postgres:// URL; render.yaml wires DATABASE_URL from the DB; suite green",
            ]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_config.py -q"),
            divider(), h2("Dependencies"), p("TIME-231/232 (blueprint)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-234: Bind the server to $PORT (fix Render web-service deploy)",
        "labels": ["backend", "deployment", "infra"],
        "description": doc(
            h2("Goal"), p("Render assigns web services a $PORT and requires the app to bind to it; the Dockerfile hardcoded :8000, so Render found no open port and failed the api deploy (the worker has no port, so it was fine)."),
            divider(), h2("Scope"), bullet_list([
                "Dockerfile CMD: gunicorn -b 0.0.0.0:${PORT:-8000} (honors Render's PORT; 8000 locally)",
                "HEALTHCHECK curl uses ${PORT:-8000}",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No app code change; compose unaffected (no PORT set -> 8000)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/Dockerfile"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Server binds $PORT when set; Render api deploy succeeds (user re-syncs)"]),
            divider(), h2("Verification"), code_block("# user: Manual sync -> api deploys; hit /api/v1/health"),
            divider(), h2("Dependencies"), p("TIME-228 (Dockerfile)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-235: Run migrations from the entrypoint, not preDeployCommand (fix Render)",
        "labels": ["backend", "deployment", "infra"],
        "description": doc(
            h2("Goal"), p("The preDeploy `alembic upgrade head` connected to localhost — Render's preDeployCommand didn't have the fromDatabase DATABASE_URL. Run migrations from the container entrypoint (RUN_MIGRATIONS=1) instead, where the full runtime env is present."),
            divider(), h2("Scope"), bullet_list([
                "render.yaml: remove preDeployCommand from the api service; add RUN_MIGRATIONS=1 to its envVars",
                "DEPLOY.md: reflect entrypoint-based migrations",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No app/entrypoint change (entrypoint already supports RUN_MIGRATIONS)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["render.yaml, docs/DEPLOY.md"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["api starts, runs migrations against the wired DB, then serves; deploy succeeds (user re-syncs)"]),
            divider(), h2("Verification"), code_block("python -c \"import yaml; yaml.safe_load(open('render.yaml')); print('ok')\""),
            divider(), h2("Dependencies"), p("TIME-228/233."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-236: Rename Redis service to force a fresh Free instance (Render downgrade block)",
        "labels": ["deployment", "infra"],
        "description": doc(
            h2("Goal"), p("Render won't downgrade the existing Starter Redis to Free in place, which blocks every blueprint sync. Rename the service so Render creates a NEW Free Key Value instead of trying to downgrade."),
            divider(), h2("Scope"), bullet_list([
                "render.yaml: rename timesense-redis -> timesense-cache (plan free) and update the fromService references on api + worker",
                "DEPLOY.md: note to delete the orphaned old timesense-redis (Starter) after sync",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No app change; REDIS_URL still auto-wired from the new service"]),
            divider(), h2("Files Likely Changed"), bullet_list(["render.yaml, docs/DEPLOY.md"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Sync creates a Free timesense-cache; api/worker get its REDIS_URL; the downgrade error is gone; old redis deleted by user"]),
            divider(), h2("Verification"), code_block("python -c \"import yaml; yaml.safe_load(open('render.yaml')); print('ok')\""),
            divider(), h2("Dependencies"), p("TIME-232 (free Redis)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-237: Point the iOS app at the deployed API (off-LAN device testing)",
        "labels": ["ios", "deployment"],
        "description": doc(
            h2("Goal"), p("Let the iPhone app work without the Mac's LAN by pointing physical-device + Release builds at the deployed Render API."),
            divider(), h2("Scope"), bullet_list([
                "APIClient.resolveBaseURL: physical device (DEBUG or Release) -> https://timesense-api.onrender.com (prodBaseURL constant); simulator stays localhost; API_BASE_URL env override still wins",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No custom domain yet (can swap prodBaseURL later)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Core/API/APIClient.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A device build hits the Render API over the internet (no Mac LAN); simulator unchanged; iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-228..236 (deployed backend)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-238: Add missing created_at/updated_at server defaults (Postgres insert 500)",
        "labels": ["backend", "bug", "database"],
        "description": doc(
            h2("Goal"), p("Connecting Google Calendar 500'd: INSERT into calendar_integrations violated the NOT NULL created_at constraint. TimestampMixin uses server_default=now() (so the ORM omits the column), but several hand-written migrations created created_at/updated_at NOT NULL with no server_default — fine on SQLite (create_all) but broken on real Postgres. fix_timestamp_defaults only covered 4 tables."),
            divider(), h2("Scope"), bullet_list([
                "New migration: add server_default now() to created_at + updated_at for the 10 remaining affected tables (calendar_integrations, pending_calendar_actions, recommendation_events, notifications, replan_requests, waitlist_entries, invite_codes, referral_codes, referral_conversions, task_duration_estimates)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No model change (mixin already correct); no SQLite-testable change (tests use create_all)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/migrations/versions/*_fix_timestamp_defaults_2.py"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["single alembic head; migration parses; after deploy, connecting an integration inserts without a NOT NULL violation; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && alembic heads && pytest -q"),
            divider(), h2("Dependencies"), p("TIME-235 (migrations run on deploy)."),
            divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
    {
        "summary": "TIME-239: Swipe between tabs has no visual transition",
        "labels": ["ios", "navigation", "polish"],
        "description": doc(
            h2("Goal"), p("Swiping between tabs cuts instantly with no motion; add a slide transition so the swipe feels like navigation."),
            divider(), h2("Scope"), bullet_list(["MainTabView: animate the tab content on swipe (slide in the direction of travel), keeping the native tab bar and existing gesture"]),
            divider(), h2("Non-Goals"), bullet_list(["No new tabs; tap behaviour unchanged"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/App/MainTabView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A swipe slides the outgoing/incoming screen; iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-220 (swipe)."), divider(), h2("Next Ticket"), p("TIME-240."),
        ),
    },
    {
        "summary": "TIME-240: Connections — show Disconnect after connecting",
        "labels": ["ios", "web", "backend", "integrations"],
        "description": doc(
            h2("Goal"), p("After connecting a provider, the Connect button should become a Disconnect button so the user can remove the connection."),
            divider(), h2("Scope"), bullet_list([
                "Backend: a per-user connected-integrations status endpoint (which providers are active); ensure a disconnect endpoint exists for each (calendar/slack/notion/email)",
                "iOS ConnectionsView + web connections page: reflect connected state from the status endpoint; swap Connect->Disconnect (calls the disconnect endpoint)",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No revoking the token at the provider (just deactivate locally)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/api/v1/integrations.py (status), disconnect routes, ios ConnectionsView, web connections/page.tsx, tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Connected providers show Disconnect; tapping it deactivates + reverts to Connect; status endpoint returns active providers; suite green; builds clean"]),
            divider(), h2("Verification"), code_block("cd backend && pytest -q && cd .. && npm --prefix web run build"),
            divider(), h2("Dependencies"), p("TIME-177/214/224 (connect)."), divider(), h2("Next Ticket"), p("TIME-241."),
        ),
    },
    {
        "summary": "TIME-241: Gmail 'Scan for tasks' gives no feedback and generates no tasks",
        "labels": ["backend", "ios", "email", "bug"],
        "description": doc(
            h2("Goal"), p("Scanning Gmail returns nothing visible and creates no pending tasks. Surface the scan result (scanned/found counts) and fix why detection yields nothing."),
            divider(), h2("Scope"), bullet_list([
                "Investigate the scan path end-to-end (fetch -> detect -> pending) on the live flow; confirm Gmail is connected + email_content consent",
                "iOS EmailTasksView: show scan feedback (e.g. 'Scanned N emails, found M') incl. the zero case",
                "Fix any bug preventing detection/pending creation",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No background scan"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios EmailTasksView, backend email_service/gmail_source as needed, tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Scan shows a result count; a scannable email yields a pending task; iOS builds; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_email_scan.py -q"),
            divider(), h2("Dependencies"), p("TIME-215/216/217 (email)."), divider(), h2("Next Ticket"), p("TIME-242."),
        ),
    },
    {
        "summary": "TIME-242: 'Why this' from Other Good Options mislabels the alternative as the recommended action",
        "labels": ["ios", "recommendations", "bug"],
        "description": doc(
            h2("Goal"), p("Tapping an item in Other Good Options opens the Why sheet but shows that alternative as THE recommended action. The sheet should explain the tapped task correctly, not relabel it as the top pick."),
            divider(), h2("Scope"), bullet_list(["Trace how the Why sheet gets its explanation for an alternative vs the main pick (NowView OptionRow -> fetchExplanation(taskId) -> /now/why); fix so recommended_action reflects the tapped task's real standing"]),
            divider(), h2("Non-Goals"), bullet_list(["No change to ranking"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios NowView / NowViewModel, backend now/why + build_explanation as needed"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Opening Why for an alternative shows that task's explanation without calling it the recommended pick; iOS builds; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_now.py -q"),
            divider(), h2("Dependencies"), p("TIME-117/175 (explanation)."), divider(), h2("Next Ticket"), p("TIME-243."),
        ),
    },
    {
        "summary": "TIME-243: Why-sheet free-time reasoning is wrong (free before a past/earlier meeting)",
        "labels": ["backend", "recommendations", "bug"],
        "description": doc(
            h2("Goal"), p("The explanation says e.g. '180 minutes free before your 11am meeting' for a 4pm appointment — it references the wrong (earlier/past) event and the math doesn't fit. Fix the free-time / next-event reasoning to use the correct upcoming event relative to now."),
            divider(), h2("Scope"), bullet_list(["build_explanation free-and-next / calendar signal: pick the next event AFTER now (not a past one) and compute free time correctly for the recommended task"]),
            divider(), h2("Non-Goals"), bullet_list(["No ranking change"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation_explainer.py, tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["The Calendar/free-time line references the correct upcoming event with sensible minutes; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_now.py -q"),
            divider(), h2("Dependencies"), p("TIME-141 (real free time)."), divider(), h2("Next Ticket"), p("TIME-244."),
        ),
    },
    {
        "summary": "TIME-244: Gmail scan finds no unread emails (query too narrow)",
        "labels": ["backend", "email", "bug"],
        "description": doc(
            h2("Goal"), p("Scanning says 'No recent unread emails to scan' even when the inbox has unread mail. The Gmail query 'is:unread newer_than:7d category:primary' is too narrow (misses non-Primary tabs and mail older than 7 days). Broaden it so a normal unread inbox is scanned."),
            divider(), h2("Scope"), bullet_list([
                "gmail_source: widen the query to 'in:inbox is:unread newer_than:30d' (drop the Primary-category filter, extend the window)",
                "Keep it read-only (format=metadata) and inbox-scoped",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No reading of bodies; no background scan; no per-user query config"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/integrations/gmail_source.py", "tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["The query matches unread inbox mail across tabs within 30 days; scan returns them; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_email_scan.py tests/test_email_fetch.py -q"),
            divider(), h2("Dependencies"), p("TIME-215 (fetch)."), divider(), h2("Next Ticket"), p("TIME-245."),
        ),
    },
    {
        "summary": "TIME-245: Disconnect button label wraps on long provider rows (Google Calendar)",
        "labels": ["ios", "integrations", "polish"],
        "description": doc(
            h2("Goal"), p("On the Connections screen the 'Disconnect' button wraps to two lines next to a long provider name (e.g. Google Calendar). Keep the button label on one line and let the name column flex instead."),
            divider(), h2("Scope"), bullet_list(["ConnectionsView trailing button: lineLimit(1) + fixedSize so 'Disconnect' never wraps; allow the provider name to truncate/shrink"]),
            divider(), h2("Non-Goals"), bullet_list(["No behaviour change; layout only"]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Settings/ConnectionsView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["'Disconnect' renders on one line on every provider row; iOS builds"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense"),
            divider(), h2("Dependencies"), p("TIME-240 (disconnect button)."), divider(), h2("Next Ticket"), p("TIME-246."),
        ),
    },
    {
        "summary": "TIME-246: Why-sheet Energy signal ignores Apple Health activity",
        "labels": ["backend", "recommendations", "health", "bug"],
        "description": doc(
            h2("Goal"), p("The 'Energy' signal in Why-this-recommendation says no signal is connected unless there is a sleep sample for today, so connecting Apple Health (which syncs activity) does nothing. The engine's context_builder already falls back to DailyActivity; the explainer's separate _health does not. Make the explainer use today's HealthKit activity for energy when there is no sleep sample."),
            divider(), h2("Scope"), bullet_list([
                "recommendation_explainer._health: after the sleep lookup, fall back to DailyActivity.get_for_day(today) -> default moderate energy + steps",
                "Update the Energy signal / context_used / decision-factor wording to reflect an activity-based estimate ('based on today's activity')",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No new HealthKit reads; no change to the engine context_builder (already handles this)"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation_explainer.py", "tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["With activity but no sleep, the Energy signal is available and mentions activity; with neither it stays 'not connected'; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_explanation_reasoning.py -q"),
            divider(), h2("Dependencies"), p("TIME-042/043 (health)."), divider(), h2("Next Ticket"), p("TIME-247."),
        ),
    },
    {
        "summary": "TIME-247: Alternatives-considered mislabels the higher-ranked top pick as a weaker fit",
        "labels": ["backend", "recommendations", "bug"],
        "description": doc(
            h2("Goal"), p("On an alternative's Why sheet, the real top pick appears under 'Alternatives considered' described as 'a solid option but a slightly weaker fit for right now' — but it is actually the stronger, higher-ranked pick. Make the alternative reasons rank/score aware so a higher-scored task is not called weaker."),
            divider(), h2("Scope"), bullet_list([
                "Pass per-task scores into build_explanation; for an alternative that scored higher than the explained task, say it ranked higher / is the current top pick",
                "Use neutral comparative wording that reads correctly whether the explained task is the top pick or an alternative",
            ]),
            divider(), h2("Non-Goals"), bullet_list(["No ranking change"]),
            divider(), h2("Files Likely Changed"), bullet_list(["backend/app/services/recommendation_explainer.py", "backend/app/api/v1/now.py", "tests"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["A higher-scored alternative is described as stronger/top, never 'weaker'; the top pick's own sheet is unchanged; suite green"]),
            divider(), h2("Verification"), code_block("cd backend && pytest tests/test_explanation_reasoning.py -q"),
            divider(), h2("Dependencies"), p("TIME-242 (alternative sheet)."), divider(), h2("Next Ticket"), p("TIME-248."),
        ),
    },
    {
        "summary": "TIME-248: Remove the non-functional signal-chip row from the Now screen",
        "labels": ["ios", "now", "polish"],
        "description": doc(
            h2("Goal"), p("Near the top of the Now screen a row of five capsule chips (Calendar/Routine/Location/Time/Tasks) looks tappable but is hard-coded, does nothing, and duplicates the live context cards + the 'Why This Recommendation?' sheet already on the screen. Remove it (false-affordance + redundant noise)."),
            divider(), h2("Scope"), bullet_list([
                "NowView: remove the ContextChipsRow() call in loadedBody and delete the private ContextChipsRow struct",
            ]),
            divider(), h2("Non-Goals"), bullet_list([
                "No change to the real context cards (ContextGrid/NowContextCards), the analyzed banner, or the Why sheet",
                "Not building the live/tappable signal-strip version (documented as a future option)",
            ]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Now/NowView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["The five-chip row no longer appears; Now goes banner -> recommendation -> context cards with no gap; iOS builds clean"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'"),
            divider(), h2("Dependencies"), p("None."), divider(), h2("Next Ticket"), p("TIME-249."),
        ),
    },
    {
        "summary": "TIME-249: Capture — tap outside the input to dismiss the keyboard",
        "labels": ["ios", "capture", "polish"],
        "description": doc(
            h2("Goal"), p("On the Capture screen, tapping the text field raises the keyboard (good), but tapping outside the field doesn't lower it or deactivate the field. Tapping empty space should dismiss the keyboard and unfocus the input."),
            divider(), h2("Scope"), bullet_list([
                "CaptureView: add a tap gesture on the scroll content that sets isInputFocused=false; child controls (field, chips, buttons) keep handling their own taps so only empty-space taps dismiss",
            ]),
            divider(), h2("Non-Goals"), bullet_list([
                "No change to the existing swipe-to-dismiss or the keyboard 'Done' button; no change to the errand location field",
            ]),
            divider(), h2("Files Likely Changed"), bullet_list(["ios/TimeSense/Features/Capture/CaptureView.swift"]),
            divider(), h2("Acceptance Criteria"), bullet_list(["Tapping outside the input lowers the keyboard and unfocuses the field; the field, chips, and buttons still work; iOS builds clean"]),
            divider(), h2("Verification"), code_block("xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'"),
            divider(), h2("Dependencies"), p("None."), divider(), h2("Next Ticket"), p("(none)"),
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Jira API calls
# ─────────────────────────────────────────────────────────────────────────────

# Transition IDs for this project's workflow
_TRANSITION_IDS = {"todo": "11", "inprogress": "21", "inreview": "31", "done": "41"}


def transition_ticket(issue_key: str, status: str) -> bool:
    """Move a ticket to a new status. status: todo | inprogress | inreview | done"""
    tid = _TRANSITION_IDS.get(status.lower().replace(" ", ""))
    if not tid:
        return False
    r = requests.post(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
        auth=AUTH,
        headers=HEADERS,
        data=json.dumps({"transition": {"id": tid}}),
    )
    return r.status_code == 204


REQUIRED_ADF_HEADINGS = ["Goal", "Scope", "Non-Goals", "Acceptance Criteria", "Verification"]

def validate_ticket(ticket: dict) -> list[str]:
    """Return a list of missing/invalid fields. Empty list = ticket is valid."""
    errors = []
    if not ticket.get("summary", "").strip():
        errors.append("missing: summary")
    if "TIME-" not in ticket.get("summary", ""):
        errors.append("summary must contain ticket key (e.g. TIME-###)")
    desc = ticket.get("description")
    if not desc:
        errors.append("missing: description")
        return errors
    # Check ADF doc has the required heading sections
    content_texts = []
    def _collect(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                content_texts.append(node.get("text", ""))
            for v in node.values():
                if isinstance(v, list):
                    for child in v:
                        _collect(child)
    _collect(desc)
    full_text = " ".join(content_texts)
    for heading in REQUIRED_ADF_HEADINGS:
        if heading.lower() not in full_text.lower():
            errors.append(f"description missing section: {heading}")
    return errors


def create_ticket(ticket: dict) -> str:
    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": ticket["summary"],
            "description": ticket["description"],
            "issuetype": {"name": "Story"},
            "labels": ticket.get("labels", []),
        }
    }
    response = requests.post(
        f"{JIRA_BASE_URL}/rest/api/3/issue",
        auth=AUTH,
        headers=HEADERS,
        data=json.dumps(payload),
    )
    if response.status_code == 201:
        key = response.json()["key"]
        return key
    else:
        print(f"  ERROR {response.status_code}: {response.text[:300]}")
        return "ERROR"


def update_ticket(issue_key: str, ticket: dict) -> bool:
    payload = {
        "fields": {
            "summary": ticket["summary"],
            "description": ticket["description"],
            "labels": ticket.get("labels", []),
        }
    }
    response = requests.put(
        f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}",
        auth=AUTH,
        headers=HEADERS,
        data=json.dumps(payload),
    )
    return response.status_code == 204


def get_existing_tickets() -> dict[str, str]:
    """Return mapping of summary -> issue key for existing TIME tickets.

    Paginates the ENTIRE project via nextPageToken. This is load-bearing: /rest/api/3/search/jql is
    token-paginated and returns only ~100 issues per page, so reading a single page (the old bug) made
    the dedup blind to everything past the first page and every full run re-created duplicate tickets.
    Keeps the FIRST key seen per summary (oldest by created) so re-runs update the canonical copy.
    """
    mapping: dict[str, str] = {}
    token, pages = None, 0
    while True:
        params = {"jql": f"project={JIRA_PROJECT_KEY} ORDER BY created ASC",
                  "maxResults": 100, "fields": "summary"}
        if token:
            params["nextPageToken"] = token
        response = requests.get(
            f"{JIRA_BASE_URL}/rest/api/3/search/jql", auth=AUTH, headers=HEADERS, params=params
        )
        if response.status_code != 200:
            break
        data = response.json()
        for i in data.get("issues", []):
            summary = i["fields"]["summary"]
            if summary not in mapping:   # keep the oldest (canonical) key per summary
                mapping[summary] = i["key"]
        token = data.get("nextPageToken")
        pages += 1
        if not token or pages > 200:
            break
    return mapping


def main():
    print(f"Connecting to {JIRA_BASE_URL}/rest/api/3 ...\n")

    # Validate all tickets before touching Jira — fail fast on missing fields
    validation_errors = []
    for ticket in TICKETS:
        errs = validate_ticket(ticket)
        if errs:
            validation_errors.append((ticket.get("summary", "(no summary)"), errs))

    if validation_errors:
        print("VALIDATION FAILED — fix these tickets before running:\n")
        for summary, errs in validation_errors:
            print(f"  {summary}")
            for e in errs:
                print(f"    ✗ {e}")
        raise SystemExit(1)

    existing = get_existing_tickets()
    print(f"Found {len(existing)} existing tickets.\n")

    for ticket in TICKETS:
        summary = ticket["summary"]
        # Match by the TIME-### prefix in summary
        ticket_ref = summary.split(":")[0].strip()

        matched_key = None
        for existing_summary, key in existing.items():
            if existing_summary.startswith(ticket_ref + ":") or existing_summary == summary:
                matched_key = key
                break

        if matched_key:
            print(f"  Updating {matched_key}: {summary[:60]}...")
            ok = update_ticket(matched_key, ticket)
            print(f"  {'✓ Updated' if ok else '✗ Failed'}: {matched_key}")
        else:
            print(f"  Creating: {summary[:60]}...")
            key = create_ticket(ticket)
            print(f"  {'✓ Created' if key != 'ERROR' else '✗ Failed'}: {key}")

    print("\nDone.")


if __name__ == "__main__":
    main()
