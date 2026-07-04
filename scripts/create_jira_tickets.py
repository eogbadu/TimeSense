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
    """Return mapping of summary -> issue key for existing TIME tickets."""
    response = requests.get(
        f"{JIRA_BASE_URL}/rest/api/3/search/jql",
        auth=AUTH,
        headers=HEADERS,
        params={"jql": f"project={JIRA_PROJECT_KEY} ORDER BY created ASC", "maxResults": 100, "fields": "summary"},
    )
    if response.status_code != 200:
        return {}
    issues = response.json().get("issues", [])
    return {i["fields"]["summary"]: i["key"] for i in issues}


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
