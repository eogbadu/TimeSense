from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class WaitlistJoinIn(BaseModel):
    email: EmailStr
    referral_code: str | None = None


class WaitlistEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    status: str
    position: int
    created_at: datetime


class WaitlistPositionOut(BaseModel):
    email: str
    position: int | None
    status: str | None


class InviteCodeCreateIn(BaseModel):
    max_uses: int = 1
    expires_at: datetime | None = None
    note: str | None = None


class InviteCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    max_uses: int
    uses: int
    is_active: bool
    expires_at: datetime | None
    note: str | None


class InviteValidateIn(BaseModel):
    code: str


class InviteValidateOut(BaseModel):
    valid: bool
