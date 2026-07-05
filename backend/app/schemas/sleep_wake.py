from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SleepWakeSource = Literal["healthkit", "manual"]


class SleepWakeLogRequest(BaseModel):
    wake_time: datetime
    sleep_start: datetime | None = None
    source: SleepWakeSource = "healthkit"


class SleepWakeEventResponse(BaseModel):
    id: uuid.UUID
    sleep_start: datetime | None
    wake_time: datetime
    source: str

    model_config = {"from_attributes": True}
