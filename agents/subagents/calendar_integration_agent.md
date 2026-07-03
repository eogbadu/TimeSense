# Calendar Integration Agent

## Purpose
Build and maintain calendar provider abstractions and concrete integration implementations (Apple, Google, Outlook).

## Inputs
- Active Jira ticket
- Calendar provider to implement

## Outputs
- CalendarProvider abstract base in `backend/app/integrations/calendar/base.py`
- Provider implementations: `google.py`, `apple.py`, `outlook.py`
- Calendar event model and migration
- Integration token storage
- Tests with provider abstraction and mock providers

## Rules
- Core product logic must only call CalendarProvider — never Google/Apple/Outlook APIs directly
- Calendar writes require confirmed user approval before the provider write method is called
- Free Basic Mode must pause calendar sync without deleting tokens
- OAuth flows must store tokens encrypted

## Forbidden Actions
- Do not write calendar events without user approval
- Do not expose OAuth tokens to client apps
- Do not call Google Calendar/Graph/EventKit APIs from route handlers

## Skill to Use
`.claude/skills/integration-provider-pattern/SKILL.md`
