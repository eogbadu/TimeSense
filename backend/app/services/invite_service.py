"""
Invite and Waitlist Service.
Signup is blocked unless a valid invite code is consumed at registration.
"""
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import InviteCode, WaitlistEntry
from app.repositories.invite_repository import InviteCodeRepository, WaitlistRepository


class InviteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.invite_repo = InviteCodeRepository(db)
        self.waitlist_repo = WaitlistRepository(db)

    async def join_waitlist(self, email: str, referral_code: str | None = None) -> WaitlistEntry:
        return await self.waitlist_repo.add(email=email, referral_code=referral_code)

    async def get_waitlist_position(self, email: str) -> int | None:
        entry = await self.waitlist_repo.get_by_email(email)
        if entry is None or entry.status != "waiting":
            return None
        return entry.position

    async def list_waiting(self, limit: int = 100) -> list[WaitlistEntry]:
        return await self.waitlist_repo.list_waiting(limit=limit)

    async def mark_joined(self, email: str) -> bool:
        return await self.waitlist_repo.mark_joined(email)

    async def create_invite_code(
        self, created_by_id: uuid.UUID | None = None, max_uses: int = 1,
        expires_at: datetime | None = None, note: str | None = None,
    ) -> InviteCode:
        return await self.invite_repo.create(created_by_id=created_by_id, max_uses=max_uses,
                                             expires_at=expires_at, note=note)

    async def validate_invite_code(self, code: str) -> bool:
        invite = await self.invite_repo.get_by_code(code)
        return invite is not None and invite.is_valid

    async def consume_invite_code(self, code: str) -> InviteCode | None:
        return await self.invite_repo.consume(code)

    async def disable_invite_code(self, code: str) -> bool:
        return await self.invite_repo.disable(code)

    async def list_active_codes(self) -> list[InviteCode]:
        return await self.invite_repo.list_active()

    async def invite_from_waitlist(self, entry_id: uuid.UUID, admin_user_id: uuid.UUID) -> InviteCode | None:
        marked = await self.waitlist_repo.mark_invited(entry_id)
        if not marked:
            return None
        return await self.invite_repo.create(created_by_id=admin_user_id, max_uses=1,
                                             note=f"waitlist:{entry_id}")
