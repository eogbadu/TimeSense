from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.onboarding_repository import (
    AssistantPersonalityRepository,
    OnboardingStateRepository,
)
from app.schemas.onboarding import (
    OnboardingPathUpdate,
    OnboardingStateResponse,
    OnboardingStepAdvance,
    PersonalityResponse,
    PersonalityUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


async def _resolve_user(current_user: CurrentUser, db: AsyncSession):
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user


# ── Assistant Personality ─────────────────────────────────────────────────────

@router.get("/personality", response_model=PersonalityResponse, summary="Get assistant personality")
async def get_personality(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PersonalityResponse:
    user = await _resolve_user(current_user, db)
    repo = AssistantPersonalityRepository(db)
    record = await repo.get_by_user_id(user.id)
    if record is None:
        return PersonalityResponse(style="calm_premium")
    return PersonalityResponse.model_validate(record)


@router.put("/personality", response_model=PersonalityResponse, summary="Set assistant personality")
async def set_personality(
    body: PersonalityUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PersonalityResponse:
    user = await _resolve_user(current_user, db)
    repo = AssistantPersonalityRepository(db)
    record = await repo.set_personality(user.id, body.style)
    return PersonalityResponse.model_validate(record)


# ── Onboarding State ──────────────────────────────────────────────────────────

@router.get("/state", response_model=OnboardingStateResponse, summary="Get onboarding state")
async def get_state(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStateResponse:
    user = await _resolve_user(current_user, db)
    repo = OnboardingStateRepository(db)
    state = await repo.get_or_create(user.id)
    return OnboardingStateResponse.model_validate(state)


@router.post("/state/advance", response_model=OnboardingStateResponse, summary="Advance onboarding step")
async def advance_step(
    body: OnboardingStepAdvance,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStateResponse:
    user = await _resolve_user(current_user, db)
    repo = OnboardingStateRepository(db)
    state = await repo.advance_step(user.id, body.next_step)
    return OnboardingStateResponse.model_validate(state)


@router.patch("/state/path", response_model=OnboardingStateResponse, summary="Set onboarding path")
async def set_path(
    body: OnboardingPathUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStateResponse:
    user = await _resolve_user(current_user, db)
    repo = OnboardingStateRepository(db)
    state = await repo.update_fields(user.id, chosen_path=body.chosen_path)
    return OnboardingStateResponse.model_validate(state)


@router.post("/state/complete", response_model=OnboardingStateResponse, summary="Mark onboarding complete")
async def complete_onboarding(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStateResponse:
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")

    # Mark step complete and flag user record
    repo = OnboardingStateRepository(db)
    state = await repo.advance_step(user.id, "complete")

    from sqlalchemy import update

    from app.models.user import User
    await db.execute(update(User).where(User.id == user.id).values(onboarding_complete=True))

    return OnboardingStateResponse.model_validate(state)
