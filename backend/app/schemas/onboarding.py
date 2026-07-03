import json
from typing import Literal

from pydantic import BaseModel, field_validator

VALID_STYLES = ("calm_premium", "friendly_companion", "high_performance_coach")
VALID_PATHS = (
    "busy_professional", "working_parent", "student", "entrepreneur",
    "adhd", "athlete", "creator", "celebrity",
)
ONBOARDING_STEPS = (
    "welcome", "path_selection", "personality", "learning_mode",
    "calendar", "health", "location", "notifications", "alarms",
    "tasks", "optional_integrations", "goals", "capture_preference",
    "audio_consent", "subscription", "complete",
)


class PersonalityResponse(BaseModel):
    style: str

    model_config = {"from_attributes": True}


class PersonalityUpdate(BaseModel):
    style: Literal["calm_premium", "friendly_companion", "high_performance_coach"]


class OnboardingStateResponse(BaseModel):
    current_step: str
    chosen_path: str | None
    completed_steps: dict
    skipped_integrations: bool
    skipped_health: bool
    skipped_location: bool
    skipped_goals: bool

    model_config = {"from_attributes": True}

    @field_validator("completed_steps", mode="before")
    @classmethod
    def parse_completed_steps(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v


class OnboardingStepAdvance(BaseModel):
    next_step: Literal[
        "welcome", "path_selection", "personality", "learning_mode",
        "calendar", "health", "location", "notifications", "alarms",
        "tasks", "optional_integrations", "goals", "capture_preference",
        "audio_consent", "subscription", "complete",
    ]


class OnboardingPathUpdate(BaseModel):
    chosen_path: Literal[
        "busy_professional", "working_parent", "student", "entrepreneur",
        "adhd", "athlete", "creator", "celebrity",
    ]
