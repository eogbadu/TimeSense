# Skill: Integration Provider Pattern

## Purpose
Prevent hardcoded integration logic. Keep TimeSense extensible by using provider abstractions for all external services: calendars, task sources, LLM providers, notification channels, smart home assistants.

## When to Use
- Implementing any calendar integration (Apple, Google, Outlook)
- Implementing any task/reminder integration (Apple Reminders, Todoist, Things)
- Implementing any communication integration (Slack, Teams)
- Implementing Notion
- Implementing HomeKit, Alexa, Google Assistant, Siri Shortcuts
- Implementing LLM calls
- Adding a new integration provider
- Reviewing existing integration for hardcoded dependencies

## Pattern

```python
# 1. Abstract base class
class CalendarProvider(ABC):
    @abstractmethod
    async def get_events(self, user_id: str, start: datetime, end: datetime) -> list[CalendarEvent]: ...

    @abstractmethod
    async def create_event(self, user_id: str, event: CalendarEventCreate) -> CalendarEvent: ...
    # Note: create_event must only be called after user has explicitly approved the write

# 2. Concrete implementation
class GoogleCalendarProvider(CalendarProvider):
    async def get_events(self, user_id, start, end):
        # Google-specific API calls
        ...

# 3. Provider registry
CALENDAR_PROVIDERS: dict[str, type[CalendarProvider]] = {
    "google": GoogleCalendarProvider,
    "apple": AppleCalendarProvider,
    "outlook": OutlookCalendarProvider,
}

# 4. Factory / service uses the registry
def get_calendar_provider(provider_type: str) -> CalendarProvider:
    return CALENDAR_PROVIDERS[provider_type]()
```

Core product logic (services, recommendation engine) only calls the abstract interface — never a provider-specific class directly.

## Required Structure

```
backend/app/integrations/
  base.py                   # Abstract provider interfaces
  calendar/
    base.py                 # CalendarProvider ABC
    google.py               # GoogleCalendarProvider
    apple.py                # AppleCalendarProvider (server-side sync if applicable)
    outlook.py              # OutlookCalendarProvider
  tasks/
    base.py                 # TaskProvider ABC
    todoist.py
    things.py
    apple_reminders.py      # Server-side if applicable
  llm/
    base.py                 # LLMGateway ABC
    openai.py
    anthropic.py            # future
  notifications/
    base.py                 # NotificationProvider ABC
    apns.py                 # Apple Push Notification Service
    fcm.py                  # Firebase Cloud Messaging
  slack/
    slack_integration.py
  teams/
    teams_integration.py
  notion/
    notion_integration.py
```

## Capability Flags

Each provider should expose capability flags:

```python
class CalendarProvider(ABC):
    can_read: bool = True
    can_write: bool = False   # Requires approval before use
    can_sync: bool = True
    requires_approval_for_write: bool = True
```

## User Approval Gate

External write-back always requires explicit user approval. The provider abstraction must enforce this:

```python
# In the service layer
async def create_calendar_event(user_id, event, approved: bool):
    if not approved:
        raise ValueError("User approval required for calendar writes")
    provider = get_calendar_provider(user.calendar_provider_type)
    return await provider.create_event(user_id, event)
```

## Token Storage

- Never expose integration tokens to client apps
- Store encrypted in `integration_tokens` table
- Refresh tokens handled server-side
- Log integration failures for admin visibility

## Free Basic Mode

In Free Basic Mode, premium integrations must pause:

```python
async def sync_calendar(user_id):
    entitlement = await get_entitlement(user_id)
    if not entitlement.is_premium:
        return  # silently pause — keep tokens, don't sync
```

## Files to Read First
- `docs/architecture/architecture_overview.md` → Integration Abstraction Pattern section
- `backend/app/integrations/base.py`

## Commands / Checks
```bash
pytest backend/tests/test_integration_providers.py -v
pytest backend/tests/test_calendar_abstraction.py -v
```

## Prohibited Actions
- Do not call provider SDKs directly from route handlers or services
- Do not hardcode provider names as strings in core logic (use the registry)
- Do not expose API keys or OAuth tokens to mobile clients
- Do not write to external services without confirmed user approval

## End-of-Task Requirements
- New provider implements the abstract base class
- Provider is registered in the registry
- Core services call the abstract interface only
- Integration token stored securely
- Free Basic Mode pause behavior implemented
