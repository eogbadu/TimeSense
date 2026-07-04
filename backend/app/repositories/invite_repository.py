import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import InviteCode, WaitlistEntry


def _new_invite_code() -> str:
    return secrets.token_urlsafe(16).upper()[:16]


class WaitlistRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, email: str, referral_code: str | None = None) -> WaitlistEntry:
        existing = await self.get_by_email(email)
        if existing:
            return existing
        count_result = await self.db.execute(select(func.count()).select_from(WaitlistEntry))
        position = (count_result.scalar() or 0) + 1
        entry = WaitlistEntry(email=email, position=position, referral_code=referral_code)
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_by_email(self, email: str) -> WaitlistEntry | None:
        result = await self.db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
        return result.scalar_one_or_none()

    async def mark_invited(self, entry_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(WaitlistEntry).where(WaitlistEntry.id == entry_id))
        entry = result.scalar_one_or_none()
        if entry is None:
            return False
        entry.status = "invited"
        entry.invited_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def mark_joined(self, email: str) -> bool:
        result = await self.db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
        entry = result.scalar_one_or_none()
        if entry is None:
            return False
        entry.status = "joined"
        entry.joined_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_waiting(self, limit: int = 100) -> list[WaitlistEntry]:
        result = await self.db.execute(
            select(WaitlistEntry).where(WaitlistEntry.status == "waiting")
            .order_by(WaitlistEntry.position.asc()).limit(limit)
        )
        return list(result.scalars().all())


class InviteCodeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, created_by_id: uuid.UUID | None, max_uses: int = 1,
        expires_at: datetime | None = None, note: str | None = None,
    ) -> InviteCode:
        code = InviteCode(code=_new_invite_code(), created_by_id=created_by_id,
                          max_uses=max_uses, expires_at=expires_at, note=note)
        self.db.add(code)
        await self.db.flush()
        return code

    async def get_by_code(self, code: str) -> InviteCode | None:
        result = await self.db.execute(select(InviteCode).where(InviteCode.code == code))
        return result.scalar_one_or_none()

    async def consume(self, code: str) -> InviteCode | None:
        invite = await self.get_by_code(code)
        if invite is None or not invite.is_valid:
            return None
        invite.uses += 1
        await self.db.flush()
        return invite

    async def disable(self, code: str) -> bool:
        invite = await self.get_by_code(code)
        if invite is None:
            return False
        invite.is_active = False
        await self.db.flush()
        return True

    async def list_active(self) -> list[InviteCode]:
        result = await self.db.execute(
            select(InviteCode).where(InviteCode.is_active.is_(True))
            .order_by(InviteCode.created_at.desc())
        )
        return list(result.scalars().all())
