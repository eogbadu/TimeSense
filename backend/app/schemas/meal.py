from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

MealType = Literal["breakfast", "lunch", "dinner"]
MealStatus = Literal["eaten", "skipped", "eating_while_working"]


class MealLogRequest(BaseModel):
    meal_type: MealType
    status: MealStatus
    occurred_at: datetime | None = None


class MealEventResponse(BaseModel):
    id: uuid.UUID
    meal_type: str
    status: str
    occurred_at: datetime

    model_config = {"from_attributes": True}


class MealTodayResponse(BaseModel):
    breakfast: str
    lunch: str
    dinner: str
