"""
Admin-only API endpoints. All routes require AdminUser dependency (role == "admin").
Normal users receive 403 Forbidden — the route existence is not hidden,
but the data is access-controlled at the dependency level.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AdminUser
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.calendar_repository import CalendarIntegrationRepository
from app.repositories.invite_repository import InviteCodeRepository, WaitlistRepository
from app.repositories.recommendation_feedback_repository import RecommendationFeedbackRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.admin import (
    AdminFeedbackListResponse,
    AdminFeedbackSummary,
    AdminIntegrationProviderStatus,
    AdminIntegrationStatusResponse,
    AdminMetricsResponse,
    AdminSubscriptionListResponse,
    AdminSubscriptionSummary,
    AdminUserListResponse,
    AdminUserSummary,
)
from app.schemas.invite import WaitlistEntryOut
from app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse, summary="List all users (admin)")
async def list_users(
    offset: int = 0,
    limit: int = 50,
    search: str | None = None,
    _admin: AdminUser = None,  # type: ignore[assignment]  # populated by Annotated[..., Depends]
    db: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    svc = UserService(db)
    limit = min(limit, 100)
    users = await svc.list_users(offset=offset, limit=limit, search=search)
    total = await svc.count_users(search=search)
    return AdminUserListResponse(
        users=[AdminUserSummary.model_validate(u) for u in users],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/subscriptions",
    response_model=AdminSubscriptionListResponse,
    summary="List all subscriptions (admin)",
)
async def list_subscriptions(
    offset: int = 0,
    limit: int = 50,
    _admin: AdminUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> AdminSubscriptionListResponse:
    limit = min(limit, 100)
    subs = await SubscriptionRepository(db).list_all(offset=offset, limit=limit)
    return AdminSubscriptionListResponse(
        subscriptions=[
            AdminSubscriptionSummary(
                user_id=sub.user_id,
                email=sub.user.email,
                platform=sub.platform,
                status=sub.status,
                plan=sub.plan,
                trial_end=sub.trial_end,
                current_period_end=sub.current_period_end,
                cancel_at_period_end=sub.cancel_at_period_end,
            )
            for sub in subs
        ],
        offset=offset,
        limit=limit,
    )


@router.get(
    "/feedback",
    response_model=AdminFeedbackListResponse,
    summary="Recent recommendation feedback across all users (admin)",
)
async def list_feedback(
    limit: int = 50,
    _admin: AdminUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> AdminFeedbackListResponse:
    rows = await RecommendationFeedbackRepository(db).list_recent_across_users(
        limit=min(limit, 200)
    )
    return AdminFeedbackListResponse(
        feedback=[
            AdminFeedbackSummary(
                id=fb.id,
                user_email=email,
                task_title=title,
                signal=fb.signal,
                created_at=fb.created_at,
            )
            for fb, email, title in rows
        ]
    )


@router.get(
    "/integrations",
    response_model=AdminIntegrationStatusResponse,
    summary="Calendar integration connection status (admin)",
)
async def integration_status(
    _admin: AdminUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> AdminIntegrationStatusResponse:
    counts = await CalendarIntegrationRepository(db).count_by_provider()
    return AdminIntegrationStatusResponse(
        providers=[
            AdminIntegrationProviderStatus(
                provider=provider,
                active_count=bucket["active"],
                inactive_count=bucket["inactive"],
            )
            for provider, bucket in sorted(counts.items())
        ]
    )


@router.get(
    "/metrics",
    response_model=AdminMetricsResponse,
    summary="Basic aggregate metrics (admin)",
)
async def metrics(
    _admin: AdminUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> AdminMetricsResponse:
    user_svc = UserService(db)
    sub_repo = SubscriptionRepository(db)
    calendar_counts = await CalendarIntegrationRepository(db).count_by_provider()
    connected = sum(bucket["active"] for bucket in calendar_counts.values())

    return AdminMetricsResponse(
        total_users=await user_svc.count_users(),
        active_subscriptions=await sub_repo.count_by_status(["active"]),
        trialing_subscriptions=await sub_repo.count_by_status(["trialing"]),
        waitlist_count=await WaitlistRepository(db).count_waiting(),
        active_invite_codes=await InviteCodeRepository(db).count_active(),
        calendar_integrations_connected=connected,
    )


@router.get(
    "/waitlist",
    response_model=list[WaitlistEntryOut],
    summary="List users still waiting for an invite (admin)",
)
async def list_waitlist(
    limit: int = 100,
    _admin: AdminUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> list[WaitlistEntryOut]:
    entries = await WaitlistRepository(db).list_waiting(limit=min(limit, 500))
    return [WaitlistEntryOut.model_validate(e) for e in entries]


@router.get("/analytics", summary="Product analytics event counts (admin)")
async def analytics_counts(
    _admin: AdminUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> dict:
    counts = await AnalyticsRepository(db).counts_by_event()
    return {"event_counts": counts, "total": sum(counts.values())}


@router.get("/health", summary="Admin health check (admin)")
async def admin_health(_admin: AdminUser = None) -> dict:  # type: ignore[assignment]
    return {"status": "ok", "role": "admin"}
