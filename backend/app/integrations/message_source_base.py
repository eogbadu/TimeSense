"""
Message-source provider abstraction.

A message source is any external chat/comms system TimeSense can read messages from to detect
action items (Slack now, Teams later). Read-only — TimeSense never writes back, and detected
action items ALWAYS require explicit user approval before becoming Tasks (enforced in the service
layer, not here). Core services call this interface, never a provider SDK directly.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SourceMessage:
    """A single message read from an external source."""

    message_id: str  # provider-native id (Slack: the message ts)
    channel: str
    text: str
    author: str | None = None
    timestamp: datetime | None = None


class MessageSourceProvider(ABC):
    """Abstract base — implement to add a new message source (Slack, Teams, …)."""

    # Capability flags — all message sources are read-only for now.
    can_read: bool = True
    can_write: bool = False

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def list_recent_messages(
        self,
        access_token: str,
        channel: str,
        limit: int = 50,
    ) -> list[SourceMessage]:
        """Read recent messages from a channel. Read-only — no approval needed for reads."""
