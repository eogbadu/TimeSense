from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.user_service import UserService

if TYPE_CHECKING:
    pass

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("/today", response_model=list[TaskResponse])
async def get_today_timeline(
    current_user: CurrentUser,
    target_date: date | None = Query(default=None, alias="date", description="ISO date, defaults to today UTC"),
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    """Return tasks scheduled for today, sorted by scheduled_start ascending."""
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    for_date = target_date or datetime.now(timezone.utc).date()

    repo = TaskRepository(db)
    tasks = await repo.list_by_user(
        user_id=user.id,
        for_date=for_date,
        limit=200,
    )

    tasks.sort(key=lambda t: t.scheduled_start or datetime.max.replace(tzinfo=timezone.utc))
    return [TaskResponse.model_validate(t) for t in tasks]
