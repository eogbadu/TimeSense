import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ConsentType = Literal[
    "audio_storage",
    "audio_training",
    "location_tracking",
    "health_data",
    "calendar_details",
    "analytics",
]


class ConsentGrantRequest(BaseModel):
    consent_type: ConsentType
    granted: bool
    source: str | None = None


class ConsentRecordResponse(BaseModel):
    id: uuid.UUID
    consent_type: str
    granted: bool
    source: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EffectiveConsentResponse(BaseModel):
    consents: dict[str, bool]
