import uuid

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    platform: str
    status: str
    plan: str | None
    trial_start: str | None
    trial_end: str | None
    current_period_end: str | None
    cancel_at_period_end: bool
    is_premium: bool

    model_config = {"from_attributes": True}


class StartTrialRequest(BaseModel):
    platform: str = "stripe"


class EntitlementResponse(BaseModel):
    is_premium: bool
    status: str | None
    platform: str | None


class FeatureFlagsResponse(BaseModel):
    is_premium: bool
    flags: dict[str, bool]
