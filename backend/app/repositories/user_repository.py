import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserPreferences, UserProfile


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile), selectinload(User.preferences))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile), selectinload(User.preferences))
            .where(User.firebase_uid == firebase_uid)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, firebase_uid: str, email: str, role: str = "user") -> User:
        user = User(firebase_uid=firebase_uid, email=email, role=role)
        profile = UserProfile(user=user)
        preferences = UserPreferences(user=user)
        self.db.add(user)
        self.db.add(profile)
        self.db.add(preferences)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_profile(
        self,
        user_id: uuid.UUID,
        display_name: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        avatar_url: str | None = None,
        onboarding_path: str | None = None,
    ) -> UserProfile | None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            return None
        if display_name is not None:
            profile.display_name = display_name
        if timezone is not None:
            profile.timezone = timezone
        if locale is not None:
            profile.locale = locale
        if avatar_url is not None:
            profile.avatar_url = avatar_url
        if onboarding_path is not None:
            profile.onboarding_path = onboarding_path
        await self.db.flush()
        return profile

    async def update_preferences(
        self,
        user_id: uuid.UUID,
        notification_mode: str | None = None,
        capture_auto_create: str | None = None,
        theme: str | None = None,
        language: str | None = None,
    ) -> UserPreferences | None:
        result = await self.db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if prefs is None:
            return None
        if notification_mode is not None:
            prefs.notification_mode = notification_mode
        if capture_auto_create is not None:
            prefs.capture_auto_create = capture_auto_create
        if theme is not None:
            prefs.theme = theme
        if language is not None:
            prefs.language = language
        await self.db.flush()
        return prefs

    async def list_all(self, offset: int = 0, limit: int = 50) -> list[User]:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())
