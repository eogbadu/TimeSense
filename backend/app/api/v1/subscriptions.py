import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.subscription import EntitlementResponse, StartTrialRequest, SubscriptionResponse
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession):
    svc = UserService(db)
    user, _ = await svc.get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.get("/me", response_model=SubscriptionResponse | None, summary="Get current subscription")
async def get_my_subscription(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse | None:
    user_id = await _get_user_id(current_user, db)
    svc = SubscriptionService(db)
    sub = await svc.get_subscription(user_id)
    if sub is None:
        return None
    return SubscriptionResponse.model_validate(sub)


@router.get("/me/entitlement", response_model=EntitlementResponse, summary="Check premium entitlement")
async def get_entitlement(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EntitlementResponse:
    user_id = await _get_user_id(current_user, db)
    svc = SubscriptionService(db)
    sub = await svc.get_subscription(user_id)
    if sub is None:
        return EntitlementResponse(is_premium=False, status=None, platform=None)
    return EntitlementResponse(is_premium=sub.is_premium, status=sub.status, platform=sub.platform)


@router.post("/trial", response_model=SubscriptionResponse, status_code=201, summary="Start 14-day trial")
async def start_trial(
    body: StartTrialRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    user_id = await _get_user_id(current_user, db)
    svc = SubscriptionService(db)
    sub = await svc.start_trial(
        user_id=user_id,
        email=current_user.email or "",
        platform=body.platform,
    )
    return SubscriptionResponse.model_validate(sub)


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Stripe webhook — validates signature then dispatches to SubscriptionService.
    All subscription state changes (renewals, cancellations, payment failures) flow through here.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    webhook_secret = settings.stripe_webhook_secret

    if not webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook not configured.")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature.") from exc

    svc = SubscriptionService(db)
    await svc.handle_stripe_event(dict(event))
    return {"received": True}


@router.post("/webhooks/apple", include_in_schema=False)
async def apple_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Apple App Store Server Notifications — signature validation handled by StoreKit on-device."""
    payload = await request.json()
    svc = SubscriptionService(db)
    await svc.handle_apple_notification(payload)
    return {"received": True}


@router.post("/webhooks/google", include_in_schema=False)
async def google_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Google Play RTDN via Pub/Sub push."""
    payload = await request.json()
    svc = SubscriptionService(db)
    await svc.handle_google_notification(payload)
    return {"received": True}
