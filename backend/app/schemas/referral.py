from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReferralCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    uses: int
    is_active: bool


class ReferralConversionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    referred_user_id: uuid.UUID
    status: str
    rewarded_at: datetime | None


class ReferralValidateIn(BaseModel):
    code: str


class ReferralValidateOut(BaseModel):
    valid: bool
    code: str | None = None
