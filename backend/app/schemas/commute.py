from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LocationPingIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    timestamp: datetime


class CommuteDetectRequest(BaseModel):
    pings: list[LocationPingIn] = Field(..., min_length=2)


class CommuteEventResponse(BaseModel):
    id: uuid.UUID
    direction: str
    detected_start: datetime
    detected_end: datetime
    estimated_minutes: int
    status: str

    model_config = {"from_attributes": True}
