import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.onboarding import AssistantPersonality, OnboardingState


class AssistantPersonalityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: uuid.UUID) -> AssistantPersonality | None:
        result = await self.db.execute(
            select(AssistantPersonality).where(AssistantPersonality.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_personality(self, user_id: uuid.UUID, style: str) -> AssistantPersonality:
        existing = await self.get_by_user_id(user_id)
        if existing is not None:
            existing.style = style
            await self.db.flush()
            return existing
        record = AssistantPersonality(user_id=user_id, style=style)
        self.db.add(record)
        await self.db.flush()
        return record


class OnboardingStateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(self, user_id: uuid.UUID) -> OnboardingState | None:
        result = await self.db.execute(
            select(OnboardingState).where(OnboardingState.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: uuid.UUID) -> OnboardingState:
        existing = await self.get_by_user_id(user_id)
        if existing is not None:
            return existing
        record = OnboardingState(user_id=user_id)
        self.db.add(record)
        await self.db.flush()
        return record

    async def advance_step(self, user_id: uuid.UUID, next_step: str) -> OnboardingState:
        state = await self.get_or_create(user_id)
        completed = json.loads(state.completed_steps)
        completed[state.current_step] = True
        state.completed_steps = json.dumps(completed)
        state.current_step = next_step
        await self.db.flush()
        return state

    async def update_fields(self, user_id: uuid.UUID, **kwargs) -> OnboardingState:
        state = await self.get_or_create(user_id)
        allowed = {"current_step", "chosen_path", "skipped_integrations", "skipped_health", "skipped_location", "skipped_goals"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(state, key, value)
        await self.db.flush()
        return state
