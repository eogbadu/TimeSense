# TimeSense

**Don't make managing your day another job.**

TimeSense is a mobile-first, context-aware personal time assistant. It learns how you actually live — your routines, commute, meals, sleep, calendar — and tells you what to do next without making you maintain another productivity system.

---

## Stack

| Layer | Technology |
|---|---|
| iOS | Swift / SwiftUI |
| Android | Kotlin / Jetpack Compose |
| Backend | FastAPI + PostgreSQL + Redis/Celery |
| Auth | Firebase Auth |
| Payments | Stripe (web) · Apple StoreKit (iOS) · Google Play Billing (Android) |
| LLM | Provider-agnostic abstraction (OpenAI default) |
| Web Companion | React or Next.js (secondary product) |

---

## Mobile-First Architecture

TimeSense is **not** a web app with a mobile wrapper. iOS and Android are the primary product surfaces. The web companion supports account setup, subscription management, integrations, and admin — not daily use.

- iOS: Xcode + SwiftUI. Must use native Apple tooling.
- Android: Android Studio + Jetpack Compose + Gradle. Must use native Android tooling.
- Backend: FastAPI running locally or via Docker Compose for infrastructure.

---

## Backend Setup

```bash
# Requires Python 3.11+, PostgreSQL, Redis
cd backend
cp .env.example .env        # fill in secrets
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Health check: `GET /health`

---

## iOS Setup

```bash
# Requires Xcode 15+, iOS 17 SDK
open ios/TimeSense.xcodeproj
# Select target device or simulator
# Build & Run (Cmd+R)
```

---

## Android Setup

```bash
# Requires Android Studio Hedgehog+, JDK 17
# Open android/ directory in Android Studio
# Sync Gradle
# Run on emulator or device
```

---

## Web Companion Setup

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

---

## Environment Variables

See `backend/.env.example`, `ios/TimeSense/Config.xcconfig.example`, `android/local.properties.example`, and `web/.env.example` for required variables.

Core required secrets:
- `DATABASE_URL`
- `REDIS_URL`
- `FIREBASE_PROJECT_ID` + service account JSON
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`
- `OPENAI_API_KEY`
- `APPLE_BUNDLE_ID` + App Store Connect credentials
- `GOOGLE_PLAY_PACKAGE_NAME` + service account JSON

---

## Jira / GitHub Workflow

- Every task maps to a Jira ticket: `TIME-###`
- Branch format: `feature/TIME-001-short-description`
- Commit format: `TIME-001: short description`
- See `docs/workflows/jira_github_workflow.md`

---

## Project Memory

Claude and all coding agents must read project memory before coding:

1. `docs/project_memory/context_summary.md`
2. `docs/project_memory/phase_status.md`
3. `docs/project_memory/implementation_log.md`
4. `docs/project_memory/decision_log.md`
5. `docs/project_memory/known_issues.md`
6. `docs/project_memory/open_questions.md`
7. `tickets/implementation_sequence.md`

See `docs/workflows/memory_compaction_policy.md` for compaction rules.

---

## Docker Note

Docker is used for backend/web infrastructure only (PostgreSQL, Redis, FastAPI, background workers). It is **not** used for iOS or Android development. Native mobile tooling is required.

---

## Key Documents

| Document | Purpose |
|---|---|
| `CLAUDE.md` | Operational instructions for Claude Code |
| `AGENTS.md` | Agent rules and subagent model |
| `docs/product/product_brief.md` | Product vision and rules |
| `docs/architecture/architecture_overview.md` | System architecture |
| `tickets/implementation_sequence.md` | Full phased ticket plan |
| `docs/project_memory/context_summary.md` | Current build state |

---

## Verification Commands

```bash
# Backend
cd backend && pytest
cd backend && alembic upgrade head

# iOS
xcodebuild test -project ios/TimeSense.xcodeproj -scheme TimeSense

# Android
cd android && ./gradlew test

# Web
cd web && npm test
```
