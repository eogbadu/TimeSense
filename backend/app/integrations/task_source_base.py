"""
External task-source provider abstraction.

A task source is an external system that already holds structured, task-like items (Notion
database pages now; Todoist/Things/Apple Reminders later). Distinct from MessageSourceProvider
(Slack/Teams): those are noisy chat streams needing LLM detection to find action items, whereas a
task source's items are already discrete tasks, so the integration reads their structured fields
directly. Read-only — imported items ALWAYS require explicit user approval before becoming Tasks
(enforced in the service layer, not here).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SourceTask:
    """A candidate task read from an external task source."""

    external_id: str  # provider-native id (Notion: the page id)
    title: str
    notes: str | None = None
    due: datetime | None = None


class TaskSourceProvider(ABC):
    """Abstract base — implement to add a new external task source (Notion, Todoist, …)."""

    # Capability flags — all task sources are read-only for now.
    can_read: bool = True
    can_write: bool = False

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def list_candidate_tasks(
        self,
        access_token: str,
        source_id: str,
        limit: int = 50,
    ) -> list[SourceTask]:
        """Read candidate tasks from a source container (Notion: a database id). Read-only."""
