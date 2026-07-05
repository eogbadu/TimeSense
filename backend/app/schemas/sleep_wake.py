from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SleepWakeEventIn(BaseModel):
    wake_time: datetime
    sleep_start: datetime | None = None
    source: Literal["healthkit", "manual"] = "manual"


class SleepWakeEventResponse(BaseModel):
    id: uuid.UUID
    wake_time: datetime
    sleep_start: datetime | None
    source: str
    replan_suggested: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_event(cls, event) -> "SleepWakeEventResponse":
        return cls(
            id=event.id,
            wake_time=event.wake_time,
            sleep_start=event.sleep_start,
            source=event.source,
            replan_suggested=event.replan_request_id is not None,
        )
