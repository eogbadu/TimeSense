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
