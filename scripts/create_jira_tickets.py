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
