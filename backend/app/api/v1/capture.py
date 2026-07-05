from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import capture_rate_limit
from app.core.security import CurrentUser
from app.llm.gateway import LLMGateway, get_llm_gateway
from app.schemas.task import TaskResponse
from app.services.analytics_service import AnalyticsService
from app.services.capture_service import CaptureService
from app.services.task_service import TaskService
from app.services.user_service import UserService

router = APIRouter(prefix="/capture", tags=["capture"])


class CaptureRequest(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=2000)
    user_timezone: str = Field(default="UTC", max_length=64)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(capture_rate_limit)],
)
async def capture(
    body: CaptureRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> TaskResponse:
    user, _ = await UserService(db).get_or_create_user(
        current_user.uid, current_user.email or ""
    )
    parser = CaptureService(gateway)
    task_create = await parser.parse(body.raw_input, user_timezone=body.user_timezone)
    task = await TaskService(db).create_task(user.id, task_create)
    await AnalyticsService(db).track(
        "task_captured", user_id=user.id, properties={"source": task_create.source}
    )
    return TaskResponse.model_validate(task)
