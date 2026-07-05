from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.routine import ROUTINE_TYPES
from app.repositories.routine_repository import RoutineAssumptionRepository
from app.schemas.routine import RoutineAssumptionResponse, RoutineAssumptionUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/routines", tags=["routines"])


@router.get("", response_model=list[RoutineAssumptionResponse])
async def list_routines(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[RoutineAssumptionResponse]:
    """List the user's routine assumptions, seeding defaults on first access."""
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    repo = RoutineAssumptionRepository(db)
    routines = await repo.get_or_seed_defaults(user.id)
    return [RoutineAssumptionResponse.model_validate(r) for r in routines]


@router.patch("/{routine_type}", response_model=RoutineAssumptionResponse)
async def update_routine(
    routine_type: str,
    body: RoutineAssumptionUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> RoutineAssumptionResponse:
    if routine_type not in ROUTINE_TYPES:
        raise HTTPException(status_code=404, detail="Unknown routine_type")

    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    repo = RoutineAssumptionRepository(db)
    routine = await repo.update_one(user.id, routine_type, body.start_minute, body.end_minute)
    return RoutineAssumptionResponse.model_validate(routine)
