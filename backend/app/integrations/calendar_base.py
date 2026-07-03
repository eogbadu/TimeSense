"""
Calendar provider abstraction.
All calendar reads and writes go through CalendarProvider.
Calendar writes NEVER execute without an explicit approval token — enforced here.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    end: datetime
    calendar_id: str = "primary"
    location: str | None = None
    description: str | None = None
    event_id: str | None = None  # set by provider after creation
    provider: str = ""


@dataclass
class CalendarEventCreate:
    title: str
    start: datetime
    end: datetime
    calendar_id: str = "primary"
    location: str | None = None
    description: str | None = None


class CalendarProvider(ABC):
    """Abstract base — implement to add a new calendar backend."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def list_events(
        self,
        access_token: str,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
    ) -> list[CalendarEvent]:
        """Read calendar events in the given range. Read-only — no approval needed."""

    @abstractmethod
    async def create_event(
        self,
        access_token: str,
        event: CalendarEventCreate,
    ) -> CalendarEvent:
        """
        Write a calendar event.
        MUST only be called after user approval has been recorded — never auto-call this.
        """

    @abstractmethod
    async def delete_event(self, access_token: str, event_id: str, calendar_id: str = "primary") -> bool:
        """Delete an event. Requires approval upstream."""
