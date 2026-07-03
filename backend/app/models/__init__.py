# Import all models here so Alembic autogenerate can detect them
from app.models.calendar import CalendarIntegration, PendingCalendarAction  # noqa: F401
from app.models.consent import ConsentRecord  # noqa: F401
from app.models.notification import Notification, ReplanRequest  # noqa: F401
from app.models.onboarding import AssistantPersonality, OnboardingState  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.user import User, UserPreferences, UserProfile  # noqa: F401
