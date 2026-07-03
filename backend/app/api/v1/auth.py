from fastapi import APIRouter

from app.core.security import CurrentUser
from app.schemas.auth import MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=MeResponse, summary="Get current authenticated user")
async def get_me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        uid=user.uid,
        email=user.email,
        role=user.role,
        email_verified=user.email_verified,
    )
