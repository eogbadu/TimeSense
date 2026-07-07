# Import all models here so Alembic autogenerate can detect them
from app.models.analytics_event import AnalyticsEvent  # noqa: F401
from app.models.calendar import CalendarIntegration, PendingCalendarAction  # noqa: F401
from app.models.commute import CommuteEvent  # noqa: F401
from app.models.consent import ConsentRecord  # noqa: F401
from app.models.insight import WeeklyInsight  # noqa: F401
from app.models.invite import InviteCode, WaitlistEntry  # noqa: F401
from app.models.meal import MealEvent  # noqa: F401
from app.models.notification import Notification, ReplanRequest  # noqa: F401
from app.models.notification_event import NotificationEvent  # noqa: F401
from app.models.notion import NotionImportItem, NotionIntegration  # noqa: F401
from app.models.onboarding import AssistantPersonality, OnboardingState  # noqa: F401
from app.models.recommendation_event import RecommendationEvent  # noqa: F401
from app.models.recommendation_feedback import RecommendationFeedback  # noqa: F401
from app.models.referral import ReferralCode, ReferralConversion  # noqa: F401
from app.models.routine import RoutineAssumption  # noqa: F401
from app.models.slack import SlackActionItem, SlackIntegration  # noqa: F401
from app.models.teams import TeamsActionItem, TeamsIntegration  # noqa: F401
from app.models.sleep_wake import SleepWakeEvent  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.task import InternalReminder, Task  # noqa: F401
from app.models.task_duration import TaskDurationEstimate  # noqa: F401
from app.models.user import User, UserPreferences, UserProfile  # noqa: F401
from app.models.user_location_state import UserLocationState  # noqa: F401
from app.models.user_place import UserPlace  # noqa: F401
