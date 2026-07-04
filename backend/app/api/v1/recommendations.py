from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskResponse
from app.services.recommendation_service import RecommendationService
from app.services.user_service import UserService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendationItem(BaseModel):
    task: TaskResponse
    why: str


class RecommendationResponse(BaseModel):
    best: RecommendationItem | None
    alternatives: list[TaskResponse]
    usable_minutes: int


@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> RecommendationResponse:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")

    repo = TaskRepository(db)
    now = datetime.now(timezone.utc)
    today = now.date()

    all_pending = await repo.list_by_user(user_id=user.id, status="pending", limit=500)
    today_tasks = await repo.list_by_user(user_id=user.id, for_date=today, limit=200)

    svc = RecommendationService(gateway)
    best_task, alternatives, usable_minutes, why = await svc.recommend(
        tasks=all_pending,
        scheduled_tasks=today_tasks,
        now=now,
    )

    return RecommendationResponse(
        best=RecommendationItem(
            task=TaskResponse.model_validate(best_task),
            why=why or "",
        ) if best_task else None,
        alternatives=[TaskResponse.model_validate(t) for t in alternatives],
        usable_minutes=usable_minutes,
    )
