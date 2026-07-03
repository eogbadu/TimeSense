"""
Entitlement gate — FastAPI dependency that blocks non-premium users.

Usage in a route:
    @router.get("/some/premium/feature")
    async def premium_feature(
        _: PremiumUser,
        ...
    ):
        ...

PremiumUser resolves to the TokenUser if the user has an active subscription (trialing or active).
Non-premium users get 403 with a structured error pointing them to the upgrade flow.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, TokenUser
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService


async def require_premium(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TokenUser:
    """Dependency: raises 403 if the user is not on an active trial or subscription."""
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    sub_svc = SubscriptionService(db)
    if not await sub_svc.is_premium(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "SUBSCRIPTION_REQUIRED",
                "message": "A Premium subscription is required to access this feature.",
                "action": "upgrade",
            },
        )
    return current_user


PremiumUser = Annotated[TokenUser, Depends(require_premium)]


# ── Feature flag constants ────────────────────────────────────────────────────
# These are the gates that drive Premium vs Free Basic Mode feature access.
# Free Basic Mode allows limited captures/tasks; Premium unlocks everything.

PREMIUM_FEATURES = frozenset({
    "ai_suggestions",
    "calendar_write",
    "replan_suggestions",
    "insight_trends",
    "capture_unlimited",
    "notification_coaching",
    "integrations_calendar",
    "integrations_health",
    "integrations_location",
    "smart_scheduling",
    "focus_modes",
})

FREE_FEATURES = frozenset({
    "capture_basic",         # up to 5 captures/day
    "today_view",
    "manual_task_entry",
    "basic_reminders",
})


def feature_flags(is_premium: bool) -> dict[str, bool]:
    """Return a dict of all feature flags for the given entitlement state."""
    flags = {f: True for f in FREE_FEATURES}
    flags.update({f: is_premium for f in PREMIUM_FEATURES})
    return flags
