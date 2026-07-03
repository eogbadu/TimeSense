# TimeSense Architecture Overview

## System Summary

TimeSense is a mobile-first consumer product with three main surfaces:

1. **iOS native app** (primary daily-use interface)
2. **Android native app** (primary daily-use interface)
3. **Web companion app** (account, settings, admin — secondary)

All surfaces share a single FastAPI backend and PostgreSQL database.

---

## High-Level Architecture

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   iOS App       │   │  Android App    │   │   Web App       │
│  (SwiftUI)      │   │  (Compose)      │   │  (React/Next)   │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                      │
         └─────────────────────┴──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   FastAPI Backend   │
                    │  (REST API + WS)    │
                    └──────────┬──────────┘
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐  ┌──────▼──────┐  ┌─────▼──────────┐
    │  PostgreSQL    │  │   Redis     │  │  Celery Workers │
    │  (primary DB)  │  │  (cache/q)  │  │  (background)   │
    └────────────────┘  └─────────────┘  └────────────────┘
```

---

## Backend Architecture

### Structure
```
backend/
  app/
    main.py               # FastAPI app entry
    core/
      config.py           # Settings / env vars
      security.py         # Auth helpers
      firebase.py         # Firebase Admin SDK
    api/
      v1/
        auth.py
        users.py
        subscriptions.py
        calendar.py
        capture.py
        recommendations.py
        timeline.py
        insights.py
        notifications.py
        search.py
        admin.py
        privacy.py
        ...
    services/             # Business logic
    repositories/         # Database access
    schemas/              # Pydantic request/response models
    models/               # SQLAlchemy ORM models
    workers/              # Celery tasks
    integrations/
      providers/          # Provider-specific implementations
      base.py             # Abstract provider interfaces
    llm/
      gateway.py          # LLM abstraction layer
      providers/
        openai.py
        anthropic.py      # future
    migrations/           # Alembic
```

### Key Patterns
- **Thin routes** → **services** → **repositories** → **models**
- Provider abstraction for all external integrations (calendar, LLM, notifications)
- Firebase Auth JWT verification as a FastAPI dependency
- Role-based access: `user`, `admin`
- Background workers (Celery + Redis) for integration syncs, notification orchestration, recommendation jobs
- All secrets via environment variables; never in code

---

## Mobile Architecture

### iOS
```
ios/
  TimeSense/
    App/
      TimeSenseApp.swift
    Features/
      Now/
      Today/
      Capture/
      Insights/
      Settings/
      Onboarding/
    Services/
      APIClient.swift
      AuthService.swift
      CalendarService.swift       # EventKit abstraction
      HealthService.swift         # HealthKit abstraction
      NotificationService.swift
      LocationService.swift
      SubscriptionService.swift   # StoreKit
    Models/
    Components/                   # Shared UI components
    Extensions/
    Widgets/
    Intents/                      # App Intents / Siri Shortcuts
```

### Android
```
android/
  app/
    src/main/
      kotlin/com/timesense/
        ui/
          now/
          today/
          capture/
          insights/
          settings/
          onboarding/
        services/
          ApiClient.kt
          AuthService.kt
          CalendarService.kt
          HealthService.kt
          NotificationService.kt
          LocationService.kt
          BillingService.kt       # Google Play Billing
        models/
        components/               # Shared Compose components
        widgets/
```

---

## Integration Abstraction Pattern

All external integrations follow the same pattern:

```python
# Abstract base
class CalendarProvider(ABC):
    async def get_events(self, user_id, start, end) -> list[CalendarEvent]: ...
    async def create_event(self, user_id, event) -> CalendarEvent: ...  # requires approval

# Concrete implementation
class GoogleCalendarProvider(CalendarProvider):
    ...

class AppleCalendarProvider(CalendarProvider):
    ...

# Registry
CALENDAR_PROVIDERS = {
    "google": GoogleCalendarProvider,
    "apple": AppleCalendarProvider,
    "outlook": OutlookCalendarProvider,
}
```

Same pattern for: LLM providers, notification providers, task/reminder providers.

---

## LLM Abstraction

```python
class LLMGateway(ABC):
    async def complete(self, prompt, context) -> str: ...

class OpenAIGateway(LLMGateway):
    ...

# Core product logic only calls LLMGateway — never OpenAI directly
```

---

## Subscription / Entitlement Architecture

```
Payment Sources:
  Stripe (web) → backend webhook → subscription_events table
  Apple StoreKit (iOS) → App Store Server Notifications → subscription_events table
  Google Play Billing (Android) → Real-time Developer Notifications → subscription_events table

Unified Entitlement:
  subscription_entitlements table
  → is_premium: bool
  → source: stripe | apple | google
  → expires_at: datetime
  → state: trialing | active | grace_period | canceled | expired | refunded

Mobile apps cache entitlement; backend is authoritative.
```

---

## Security Boundaries

- Firebase Auth JWTs verified server-side on every request
- Integration tokens encrypted at rest
- Admin routes protected by role check (`user.role == "admin"`)
- Calendar writes require explicit user approval event
- Replan suggestions require explicit user approval
- Raw audio stored only with explicit opt-in
- Consent records in database
- Audit logs for sensitive integration actions

---

## Background Worker Architecture

```
Celery + Redis:
  - Integration sync jobs (calendar, reminders, task sources)
  - Recommendation generation
  - Notification orchestration
  - Weekly insight generation
  - Habit change detection
  - Subscription state refresh
  - Webhook idempotency checks
```

---

## Data Flow: Recommendation

```
1. Trigger (time-based or user-requested)
2. Gather context:
   - Calendar events (next 3h)
   - Routine assumptions
   - Meal status
   - Commute risk
   - Sleep/wake data
   - Goals + deadlines
   - Energy level
   - Location context
3. Calculate usable time windows
4. Score task candidates
5. Select top recommendation + 2 alternatives
6. Send to LLM gateway for natural-language explanation
7. Return to mobile/web
8. User sees recommendation card; "Why this?" hidden by default
```

---

## Web App Structure

```
web/
  app/
    page.tsx              # Landing page
    login/
    signup/
    app/
      insights/
      integrations/
      settings/
      subscription/
    admin/
      page.tsx            # Admin dashboard (role-protected)
      users/
      invites/
      metrics/
      feedback/
  components/
  lib/
    api.ts
    auth.ts
    stripe.ts
```

---

## Docker Strategy

Docker is for backend/web infrastructure only:
- PostgreSQL
- Redis
- FastAPI backend
- Celery worker
- Web companion (optional)

**Never use Docker for iOS or Android development.**

```yaml
# docker-compose.yml covers: postgres, redis, backend, worker, web
```
