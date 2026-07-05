"""
Privacy: self-service data export and account deletion (TIME-055).

Export gathers everything the user owns into a portable JSON bundle (secrets like OAuth tokens are
redacted). Deletion removes the user row — DB-level ON DELETE CASCADE erases all their related rows
— plus an explicit purge of analytics events (SET NULL would merely anonymize them) and the Firebase
Auth user. Both operate only on the authenticated user's own data.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent
from app.models.calendar import CalendarIntegration, PendingCalendarAction
from app.models.commute import CommuteEvent
from app.models.consent import ConsentRecord
from app.models.insight import WeeklyInsight
from app.models.invite import InviteCode
from app.models.meal import MealEvent
from app.models.notification import Notification, ReplanRequest
from app.models.notification_event import NotificationEvent
from app.models.notion import NotionImportItem, NotionIntegration
from app.models.onboarding import AssistantPersonality, OnboardingState
from app.models.recommendation_feedback import RecommendationFeedback
from app.models.referral import ReferralCode, ReferralConversion
from app.models.routine import RoutineAssumption
from app.models.slack import SlackActionItem, SlackIntegration
from app.models.sleep_wake import SleepWakeEvent
from app.models.subscription import Subscription
from app.models.task import InternalReminder, Task
from app.models.teams import TeamsActionItem, TeamsIntegration
from app.models.user import User, UserPreferences, UserProfile

logger = logging.getLogger(__name__)

# Never export secrets even for the owner (they're server-only; the client already can't see them).
_REDACTED_COLUMNS = {"access_token", "refresh_token"}

# (label, model, user-referencing column). Drives the export bundle; deletion uses DB cascade.
_USER_DATA: list[tuple[str, type, object]] = [
    ("profile", UserProfile, UserProfile.user_id),
    ("preferences", UserPreferences, UserPreferences.user_id),
    ("onboarding", OnboardingState, OnboardingState.user_id),
    ("assistant_personality", AssistantPersonality, AssistantPersonality.user_id),
    ("tasks", Task, Task.user_id),
    ("internal_reminders", InternalReminder, InternalReminder.user_id),
    ("meals", MealEvent, MealEvent.user_id),
    ("sleep_wake_events", SleepWakeEvent, SleepWakeEvent.user_id),
    ("commute_events", CommuteEvent, CommuteEvent.user_id),
    ("routine_assumptions", RoutineAssumption, RoutineAssumption.user_id),
    ("consent_records", ConsentRecord, ConsentRecord.user_id),
    ("subscriptions", Subscription, Subscription.user_id),
    ("notifications", Notification, Notification.user_id),
    ("replan_requests", ReplanRequest, ReplanRequest.user_id),
    ("notification_events", NotificationEvent, NotificationEvent.user_id),
    ("recommendation_feedback", RecommendationFeedback, RecommendationFeedback.user_id),
    ("weekly_insights", WeeklyInsight, WeeklyInsight.user_id),
    ("calendar_integrations", CalendarIntegration, CalendarIntegration.user_id),
    ("pending_calendar_actions", PendingCalendarAction, PendingCalendarAction.user_id),
    ("slack_integrations", SlackIntegration, SlackIntegration.user_id),
    ("slack_action_items", SlackActionItem, SlackActionItem.user_id),
    ("teams_integrations", TeamsIntegration, TeamsIntegration.user_id),
    ("teams_action_items", TeamsActionItem, TeamsActionItem.user_id),
    ("notion_integrations", NotionIntegration, NotionIntegration.user_id),
    ("notion_import_items", NotionImportItem, NotionImportItem.user_id),
    ("analytics_events", AnalyticsEvent, AnalyticsEvent.user_id),
    ("invite_codes", InviteCode, InviteCode.created_by_id),
    ("referral_codes", ReferralCode, ReferralCode.owner_id),
    ("referral_conversions", ReferralConversion, ReferralConversion.referred_user_id),
]


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _serialize(row) -> dict:
    return {
        c.name: ("[redacted]" if c.name in _REDACTED_COLUMNS else _json_safe(getattr(row, c.name)))
        for c in row.__table__.columns
    }


class PrivacyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def export_data(self, user_id: uuid.UUID) -> dict:
        """Return a portable JSON bundle of everything the user owns (tokens redacted)."""
        user = await self.db.get(User, user_id)
        bundle: dict = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user": _serialize(user) if user is not None else None,
        }
        for label, model, column in _USER_DATA:
            result = await self.db.execute(select(model).where(column == user_id))
            bundle[label] = [_serialize(row) for row in result.scalars().all()]
        return bundle

    async def delete_account(self, user_id: uuid.UUID) -> bool:
        """Erase the user and all their data. Returns False if the user doesn't exist.

        DB-level ON DELETE CASCADE removes every user_id-owned row when the user is deleted;
        analytics_events (SET NULL) are explicitly purged for full erasure rather than anonymized.
        The Firebase Auth user is deleted best-effort.
        """
        user = await self.db.get(User, user_id)
        if user is None:
            return False

        firebase_uid = user.firebase_uid
        await self.db.execute(delete(AnalyticsEvent).where(AnalyticsEvent.user_id == user_id))
        await self.db.delete(user)  # cascades to all user_id-owned tables
        await self.db.flush()

        _delete_firebase_user(firebase_uid)
        return True


def _delete_firebase_user(firebase_uid: str) -> None:
    try:
        from firebase_admin import auth

        auth.delete_user(firebase_uid)
    except Exception as exc:  # noqa: BLE001 — Firebase optional/unconfigured in dev + tests
        logger.warning("Firebase user delete skipped/failed for %s: %s", firebase_uid, exc)
