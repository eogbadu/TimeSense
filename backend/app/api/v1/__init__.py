from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.consent import router as consent_router
from app.api.v1.health import router as health_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(onboarding_router)
api_router.include_router(consent_router)
api_router.include_router(admin_router)
api_router.include_router(subscriptions_router)
api_router.include_router(calendar_router)
api_router.include_router(notifications_router)
