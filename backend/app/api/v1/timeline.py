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
    """Today's tasks: everything scheduled for the day, plus (when viewing today) untimed pending
    to-dos — e.g. just-captured tasks with no time — so the user sees their full list, not just
    scheduled blocks. Sorted by scheduled_start ascending (untimed tasks sort last)."""
    user_svc = UserService(db)
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")

    today = datetime.now(timezone.utc).date()
    for_date = target_date or today

    repo = TaskRepository(db)
    tasks = await repo.list_by_user(user_id=user.id, for_date=for_date, limit=200)

    if for_date == today:
        scheduled_ids = {t.id for t in tasks}
        all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=200)
        untimed = [t for t in all_pending if t.scheduled_start is None and t.id not in scheduled_ids]
        tasks = tasks + untimed

    tasks.sort(key=lambda t: t.scheduled_start or datetime.max.replace(tzinfo=timezone.utc))
    return [TaskResponse.model_validate(t) for t in tasks]
