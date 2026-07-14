"""
Subscription service — platform-agnostic entitlement logic.

Stripe is the web payment platform. Apple StoreKit and Google Play Billing
are handled on-device; this service receives their webhook payloads and
updates the unified Subscription record.
"""
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.subscription import Subscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository


class SubscriptionService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = SubscriptionRepository(db)
        self.user_repo = UserRepository(db)

    async def get_subscription(self, user_id: uuid.UUID) -> Subscription | None:
        return await self.repo.get_by_user_id(user_id)

    async def is_premium(self, user_id: uuid.UUID) -> bool:
        """Premium if there's an active/trialing subscription, OR the account is still inside its
        intro trial — everyone gets Premium free for their first `intro_trial_days`, no payment.
        Dev/testing: also premium if the account's email is in the `premium_test_emails` allowlist."""
        sub = await self.repo.get_by_user_id(user_id)
        if sub is not None and sub.is_premium:
            return True
        if await self.in_intro_trial(user_id):
            return True
        return await self._is_test_premium(user_id)

    async def _is_test_premium(self, user_id: uuid.UUID) -> bool:
        """Dev/testing override: emails listed in `premium_test_emails` are always Premium so
        premium features can be tested past the intro trial. Empty by default → no production effect."""
        allow = {e.strip().lower() for e in settings.premium_test_emails.split(",") if e.strip()}
        if not allow:
            return False
        user = await self.user_repo.get_by_id(user_id)
        return user is not None and (user.email or "").lower() in allow

    async def in_intro_trial(self, user_id: uuid.UUID) -> bool:
        """True while the account is younger than the intro-trial window."""
        end = await self.intro_trial_ends_at(user_id)
        return end is not None and datetime.now(timezone.utc) < end

    async def intro_trial_ends_at(self, user_id: uuid.UUID) -> datetime | None:
        """When this account's free intro trial ends (created_at + intro_trial_days), or None."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None or user.created_at is None:
            return None
        created = user.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return created + timedelta(days=settings.intro_trial_days)

    async def start_trial(
        self,
        user_id: uuid.UUID,
        email: str,
        platform: str = "stripe",
    ) -> Subscription:
        existing = await self.repo.get_by_user_id(user_id)
        if existing is not None:
            return existing

        stripe_customer_id: str | None = None
        if platform == "stripe" and settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key
            customer = stripe.Customer.create(email=email, metadata={"user_id": str(user_id)})
            stripe_customer_id = customer.id

        return await self.repo.start_trial(
            user_id=user_id,
            platform=platform,
            platform_customer_id=stripe_customer_id,
        )

    async def handle_stripe_event(self, event: dict) -> bool:
        """
        Process a verified Stripe webhook event and update subscription state.
        Returns True if the event was handled, False if skipped.
        """
        event_type = event.get("type", "")
        obj = event.get("data", {}).get("object", {})

        if event_type == "customer.subscription.updated":
            return await self._handle_stripe_subscription_updated(obj)
        if event_type == "customer.subscription.deleted":
            return await self._handle_stripe_subscription_deleted(obj)
        if event_type in ("invoice.payment_succeeded", "invoice.paid"):
            return await self._handle_invoice_paid(obj)
        if event_type == "invoice.payment_failed":
            return await self._handle_invoice_payment_failed(obj)
        return False

    async def _handle_stripe_subscription_updated(self, sub_obj: dict) -> bool:
        sub_id = sub_obj.get("id")
        if not sub_id:
            return False
        sub = await self.repo.get_by_platform_subscription_id(sub_id)
        if sub is None:
            # Try by customer ID
            customer_id = sub_obj.get("customer")
            if customer_id:
                sub = await self.repo.get_by_platform_customer_id(customer_id)
        if sub is None:
            return False

        stripe_status = sub_obj.get("status", "")
        status_map = {
            "trialing": "trialing",
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "unpaid": "past_due",
            "incomplete_expired": "expired",
        }
        new_status = status_map.get(stripe_status, sub.status)
        period_end = sub_obj.get("current_period_end")

        await self.repo.update(
            sub.user_id,
            status=new_status,
            platform_subscription_id=sub_id,
            current_period_end=str(period_end) if period_end else None,
            cancel_at_period_end=sub_obj.get("cancel_at_period_end", False),
        )
        return True

    async def _handle_stripe_subscription_deleted(self, sub_obj: dict) -> bool:
        sub_id = sub_obj.get("id")
        if not sub_id:
            return False
        sub = await self.repo.get_by_platform_subscription_id(sub_id)
        if sub is None:
            return False
        await self.repo.update(sub.user_id, status="canceled")
        return True

    async def _handle_invoice_paid(self, invoice: dict) -> bool:
        customer_id = invoice.get("customer")
        sub_id = invoice.get("subscription")
        if not customer_id:
            return False
        sub = await self.repo.get_by_platform_customer_id(customer_id)
        if sub is None:
            return False
        await self.repo.update(
            sub.user_id,
            status="active",
            platform_subscription_id=sub_id,
        )
        return True

    async def _handle_invoice_payment_failed(self, invoice: dict) -> bool:
        customer_id = invoice.get("customer")
        if not customer_id:
            return False
        sub = await self.repo.get_by_platform_customer_id(customer_id)
        if sub is None:
            return False
        await self.repo.update(sub.user_id, status="past_due")
        return True

    async def handle_apple_notification(self, notification: dict) -> bool:
        """Stub — Apple server-to-server notifications processed here."""
        notification_type = notification.get("notificationType", "")
        if notification_type in ("DID_RENEW", "SUBSCRIBED"):
            original_tx_id = notification.get("originalTransactionId")
            if original_tx_id:
                sub = await self.repo.get_by_platform_customer_id(original_tx_id)
                if sub:
                    await self.repo.update(sub.user_id, status="active")
                    return True
        if notification_type in ("DID_FAIL_TO_RENEW", "EXPIRED"):
            original_tx_id = notification.get("originalTransactionId")
            if original_tx_id:
                sub = await self.repo.get_by_platform_customer_id(original_tx_id)
                if sub:
                    await self.repo.update(sub.user_id, status="expired")
                    return True
        return False

    async def handle_google_notification(self, notification: dict) -> bool:
        """Stub — Google Play RTDN notifications processed here."""
        notification_type = notification.get("subscriptionNotification", {}).get("notificationType")
        purchase_token = notification.get("subscriptionNotification", {}).get("purchaseToken")
        if not purchase_token:
            return False
        sub = await self.repo.get_by_platform_customer_id(purchase_token)
        if sub is None:
            return False
        # 1 = RECOVERED, 2 = RENEWED, 4 = PURCHASED
        if notification_type in (1, 2, 4):
            await self.repo.update(sub.user_id, status="active")
            return True
        # 3 = CANCELED, 12 = EXPIRED
        if notification_type in (3, 12):
            await self.repo.update(sub.user_id, status="canceled")
            return True
        return False
