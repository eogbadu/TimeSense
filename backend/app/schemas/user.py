import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    display_name: str | None
    timezone: str
    locale: str
    avatar_url: str | None
    onboarding_path: str | None

    model_config = {"from_attributes": True}


class UserPreferencesResponse(BaseModel):
    notification_mode: str
    capture_auto_create: str
    theme: str
    language: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    onboarding_complete: bool
    created_at: datetime
    profile: UserProfileResponse | None = None
    preferences: UserPreferencesResponse | None = None

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    timezone: str | None = None
    locale: str | None = None
    avatar_url: str | None = None
    onboarding_path: str | None = None


class UserPreferencesUpdate(BaseModel):
    notification_mode: Literal["gentle", "balanced", "active_coach"] | None = None
    capture_auto_create: Literal["auto", "ask"] | None = None
    theme: Literal["light", "dark", "system"] | None = None
    language: str | None = None
