from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.commutes import router as commutes_router
from app.api.v1.consent import router as consent_router
from app.api.v1.health import router as health_router
from app.api.v1.insights import router as insights_router
from app.api.v1.invites import router as invites_router
from app.api.v1.meals import router as meals_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.referrals import router as referrals_router
from app.api.v1.capture import router as capture_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.now import router as now_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.routines import router as routines_router
from app.api.v1.slack import router as slack_router
from app.api.v1.sleep import router as sleep_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.timeline import router as timeline_router
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
api_router.include_router(commutes_router)
api_router.include_router(notifications_router)
api_router.include_router(referrals_router)
api_router.include_router(invites_router)
api_router.include_router(tasks_router)
api_router.include_router(timeline_router)
api_router.include_router(now_router)
api_router.include_router(recommendations_router)
api_router.include_router(routines_router)
api_router.include_router(meals_router)
api_router.include_router(sleep_router)
api_router.include_router(insights_router)
api_router.include_router(slack_router)
api_router.include_router(capture_router)
