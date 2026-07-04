from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService
from app.services.user_service import UserService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_service(db: AsyncSession = Depends(get_db)) -> TaskService:
    return TaskService(db)


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> TaskResponse:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.create_task(user.id, body)
    return TaskResponse.model_validate(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
    date_filter: date | None = Query(default=None, alias="date"),
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> list[TaskResponse]:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    tasks = await task_svc.list_tasks(user.id, status=status_filter, for_date=date_filter)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> TaskResponse:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.get_task(task_id, user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> TaskResponse:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    task = await task_svc.update_task(task_id, user.id, body)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: CurrentUser,
    task_svc: TaskService = Depends(get_task_service),
    user_svc: UserService = Depends(get_user_service),
) -> None:
    user, _ = await user_svc.get_or_create_user(current_user.uid, current_user.email or "")
    deleted = await task_svc.delete_task(task_id, user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
