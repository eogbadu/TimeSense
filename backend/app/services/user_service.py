from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)

    async def get_or_create_user(
        self, firebase_uid: str, email: str, role: str | None = None
    ) -> tuple[User, bool]:
        """Return (user, created). Called on every authenticated request that needs a DB user.

        The Firebase custom-claim role is the source of truth for authorization; when a caller
        passes the token's ``role``, mirror it into the DB so ``/users/me`` (and the web dashboard
        gate that reads it) stays in sync with the claim — including downgrades if the claim is
        removed. Persisted by the request's session commit (get_db commits on success).
        """
        user = await self.repo.get_by_firebase_uid(firebase_uid)
        if user is not None:
            if role is not None and user.role != role:
                user.role = role
            return user, False
        await self.repo.create(firebase_uid=firebase_uid, email=email, role=role or "user")
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
