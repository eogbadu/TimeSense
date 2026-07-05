from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.user import (
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserProfileResponse,
    UserProfileUpdate,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user, _ = await service.get_or_create_user(
        current_user.uid, current_user.email or "", role=current_user.role
    )
    return UserResponse.model_validate(user)


@router.patch("/me/profile", response_model=UserProfileResponse, summary="Update profile")
async def update_profile(
    body: UserProfileUpdate,
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    user, _ = await service.get_or_create_user(current_user.uid, current_user.email or "")
    await service.update_profile(user.id, **body.model_dump(exclude_none=True))
    updated = await service.get_by_id(user.id)
    if updated is None or updated.profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return UserProfileResponse.model_validate(updated.profile)


@router.patch("/me/preferences", response_model=UserPreferencesResponse, summary="Update preferences")
async def update_preferences(
    body: UserPreferencesUpdate,
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
) -> UserPreferencesResponse:
    user, _ = await service.get_or_create_user(current_user.uid, current_user.email or "")
    await service.update_preferences(user.id, **body.model_dump(exclude_none=True))
    updated = await service.get_by_id(user.id)
    if updated is None or updated.preferences is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found.")
    return UserPreferencesResponse.model_validate(updated.preferences)
