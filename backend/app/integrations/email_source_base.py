"""
Email-source provider abstraction.

An email source is any mailbox TimeSense can read READ-ONLY to detect action items (Gmail now,
Outlook later). We only ever read message *metadata* — subject, sender, and the provider's short
snippet — never the full body, and never write/send. Detected items ALWAYS require explicit user
approval before becoming Tasks (enforced in the service layer). Core services call this interface,
never a provider SDK directly.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EmailMessage:
    """A single email, reduced to the minimum we need for detection (no body is ever fetched)."""

    message_id: str          # provider-native id (Gmail: the message id)
    thread_id: str | None
    subject: str
    sender: str | None
    snippet: str             # the provider's short preview (~200 chars), NOT the full body
    received_at: datetime | None = None

    @property
    def detection_text(self) -> str:
        """What we hand the action-item detector: subject + snippet only."""
        return f"{self.subject}\n{self.snippet}".strip()


class EmailSourceProvider(ABC):
    """Abstract base — implement to add a mail source (Gmail, Outlook, …). Read-only."""

    can_read: bool = True
    can_write: bool = False

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def list_recent_emails(self, access_token: str, max_results: int = 25) -> list[EmailMessage]:
        """Read recent unread inbox emails (metadata + snippet only). Read-only — no approval needed."""
