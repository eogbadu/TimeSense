from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)

    async def get_or_create_user(self, firebase_uid: str, email: str) -> tuple[User, bool]:
        """Return (user, created). Called on every authenticated request that needs a DB user."""
        user = await self.repo.get_by_firebase_uid(firebase_uid)
        if user is not None:
            return user, False
        await self.repo.create(firebase_uid=firebase_uid, email=email)
        # Re-fetch with selectinload so relationships are available outside the session greenlet.
        user = await self.repo.get_by_firebase_uid(firebase_uid)
        return user, True  # type: ignore[return-value]

    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        return await self.repo.get_by_firebase_uid(firebase_uid)

    async def get_by_id(self, user_id) -> User | None:
        return await self.repo.get_by_id(user_id)

    async def update_profile(self, user_id, **kwargs) -> None:
        await self.repo.update_profile(user_id, **kwargs)

    async def update_preferences(self, user_id, **kwargs) -> None:
        await self.repo.update_preferences(user_id, **kwargs)

    async def list_users(self, offset: int = 0, limit: int = 50, search: str | None = None):
        return await self.repo.list_all(offset=offset, limit=limit, search=search)

    async def count_users(self, search: str | None = None) -> int:
        return await self.repo.count_all(search=search)
