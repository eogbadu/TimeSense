import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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
    work_start_hour: int = 8
    work_end_hour: int = 21

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
    work_start_hour: int | None = Field(default=None, ge=0, le=22)
    work_end_hour: int | None = Field(default=None, ge=1, le=23)

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.work_start_hour is not None and self.work_end_hour is not None:
            if self.work_end_hour <= self.work_start_hour:
                raise ValueError("work_end_hour must be after work_start_hour")
        return self
