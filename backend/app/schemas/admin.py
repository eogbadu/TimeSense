import uuid
from datetime import datetime

from pydantic import BaseModel


class AdminUserSummary(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    is_active: bool
    onboarding_complete: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    users: list[AdminUserSummary]
    total: int
    offset: int
    limit: int


class AdminSubscriptionSummary(BaseModel):
    user_id: uuid.UUID
    email: str
    platform: str
    status: str
    plan: str | None
    trial_end: str | None
    current_period_end: str | None
    cancel_at_period_end: bool


class AdminSubscriptionListResponse(BaseModel):
    subscriptions: list[AdminSubscriptionSummary]
    offset: int
    limit: int


class AdminFeedbackSummary(BaseModel):
    id: uuid.UUID
    user_email: str
    task_title: str
    signal: str
    created_at: datetime


class AdminFeedbackListResponse(BaseModel):
    feedback: list[AdminFeedbackSummary]


class AdminIntegrationProviderStatus(BaseModel):
    provider: str
    active_count: int
    inactive_count: int


class AdminIntegrationStatusResponse(BaseModel):
    providers: list[AdminIntegrationProviderStatus]


class AdminMetricsResponse(BaseModel):
    total_users: int
    active_subscriptions: int
    trialing_subscriptions: int
    waitlist_count: int
    active_invite_codes: int
    calendar_integrations_connected: int
