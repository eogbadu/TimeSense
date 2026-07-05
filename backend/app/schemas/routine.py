from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RoutineAssumptionResponse(BaseModel):
    id: uuid.UUID
    routine_type: str
    start_minute: int
    end_minute: int
    is_customized: bool

    model_config = {"from_attributes": True}


class RoutineAssumptionUpdate(BaseModel):
    start_minute: int = Field(..., ge=0, le=1439)
    end_minute: int = Field(..., ge=0, le=1439)
