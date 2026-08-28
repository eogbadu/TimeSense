"""Energy check-in — the user's own read on how they feel, which overrides what we inferred."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.localtime import user_timezone_of
from app.core.security import CurrentUser
from app.repositories.energy_checkin_repository import CHECKIN_VALID_FOR, EnergyCheckInRepository
from app.services.energy_service import EnergyService
from app.services.user_service import UserService

router = APIRouter(prefix="/energy", tags=["energy"])


class EnergyCheckInRequest(BaseModel):
    reported: Literal["low", "medium", "high"]


class EnergyResponse(BaseModel):
    level: str          # canonical: low | medium | high
    label: str          # display wording ("moderate" reads better than "medium")
    score: float
    reason: str
    source: str         # sleep | activity | time_of_day | checkin
    valid_for_minutes: int | None = None   # set when a self-report is in effect


@router.get("", response_model=EnergyResponse)
async def get_energy(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyResponse:
    """The current energy estimate — the same value the recommendation engine is using."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    estimate = await EnergyService(db).estimate(user.id, user_timezone=user_timezone_of(user))
    return _to_response(estimate)


@router.post("/checkin", response_model=EnergyResponse)
async def create_checkin(
    body: EnergyCheckInRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EnergyResponse:
    """Record how the user actually feels. Overrides the inferred value for a bounded window.

    The inferred value at this instant is stored alongside the report: the gap between them is the
    only real feedback the energy model has, and it's what would let the curve be calibrated on
    evidence later.
    """
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    tz = user_timezone_of(user)
    now = datetime.now(timezone.utc)
    svc = EnergyService(db)

    inferred = await svc.estimate(user.id, now=now, user_timezone=tz)
    await EnergyCheckInRepository(db).create(
        user_id=user.id,
        reported=body.reported,
        # Don't record a previous check-in as if it were the model's own reading.
        inferred=inferred.level if inferred.source != "checkin" else None,
        inferred_score=inferred.score if inferred.source != "checkin" else None,
        reported_at=now,
    )
    await db.commit()

    return _to_response(await svc.estimate(user.id, now=now, user_timezone=tz))


def _to_response(estimate) -> EnergyResponse:
    return EnergyResponse(
        level=estimate.level,
        label=estimate.display_label,
        score=estimate.score,
        reason=estimate.reason,
        source=estimate.source,
        valid_for_minutes=(int(CHECKIN_VALID_FOR.total_seconds() / 60)
                           if estimate.source == "checkin" else None),
    )
