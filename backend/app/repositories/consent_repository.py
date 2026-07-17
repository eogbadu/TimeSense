import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import ConsentRecord

VALID_CONSENT_TYPES = frozenset({
    "audio_storage",
    "audio_training",
    "location_tracking",
    "health_data",
    "calendar_details",
    "analytics",
    "email_content",
})


class ConsentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        user_id: uuid.UUID,
        consent_type: str,
        granted: bool,
        source: str | None = None,
        notes: str | None = None,
    ) -> ConsentRecord:
        """Append a new consent decision (immutable audit trail)."""
        entry = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            source=source,
            notes=notes,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def ensure_granted(
        self, user_id: uuid.UUID, consent_type: str, source: str | None = None
    ) -> bool:
        """Idempotently grant a consent when the user enables the underlying signal (e.g. connecting a
        calendar). Records granted=True only if it isn't already effectively granted, so it can be wired
        into a connect flow that runs repeatedly without appending a row each time. Returns True if a
        new record was written."""
        effective = await self.get_effective(user_id)
        if effective.get(consent_type):
            return False
        await self.record(user_id, consent_type, True, source=source)
        return True

    async def get_effective(self, user_id: uuid.UUID) -> dict[str, bool]:
        """Return the latest consent decision for each type as {consent_type: granted}."""
        result = await self.db.execute(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user_id)
            .order_by(ConsentRecord.created_at.asc())
        )
        records = result.scalars().all()
        effective: dict[str, bool] = {}
        for r in records:
            effective[r.consent_type] = r.granted
        return effective

    async def get_history(self, user_id: uuid.UUID, consent_type: str) -> list[ConsentRecord]:
        result = await self.db.execute(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user_id, ConsentRecord.consent_type == consent_type)
            .order_by(ConsentRecord.created_at.desc())
        )
        return list(result.scalars().all())
