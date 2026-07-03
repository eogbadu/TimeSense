"""
Admin-only API endpoints. All routes require AdminUser dependency (role == "admin").
Normal users receive 403 Forbidden — the route existence is not hidden,
but the data is access-controlled at the dependency level.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AdminUser
from app.schemas.admin import AdminUserListResponse, AdminUserSummary
from app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse, summary="List all users (admin)")
async def list_users(
    offset: int = 0,
    limit: int = 50,
    _admin: AdminUser = None,  # type: ignore[assignment]  # populated by Annotated[..., Depends]
    db: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    svc = UserService(db)
    users = await svc.list_users(offset=offset, limit=min(limit, 100))
    return AdminUserListResponse(
        users=[AdminUserSummary.model_validate(u) for u in users],
        total=len(users),
        offset=offset,
        limit=limit,
    )


@router.get("/health", summary="Admin health check (admin)")
async def admin_health(_admin: AdminUser = None) -> dict:  # type: ignore[assignment]
    return {"status": "ok", "role": "admin"}
