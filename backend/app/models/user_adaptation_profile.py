from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# JSONB on Postgres, plain JSON on SQLite. The tests build their schema with Base.metadata
# .create_all against SQLite (see known_issues.md), and a bare JSONB column can't be rendered
# there — which surfaces as a deadlock inside aiosqlite rather than a clean error.
_JSONMap = JSON().with_variant(JSONB(), "postgresql")


class UserAdaptationProfile(UUIDMixin, TimestampMixin, Base):
    """What TimeSense has actually learned about one person.

    Asked "how does TimeSense learn my habits and adapt to them?", the honest answer before this
    table was: a duration average, an acceptance rate keyed on action type, and two read-only
    "what we learned" screens that fed nothing back into scoring. Everything else was recomputed
    live, per request, over 28- or 30-day windows — too expensive to consult on every /now call,
    which is exactly why scoring didn't consult it.

    This is the first table whose PURPOSE is adaptation. A nightly job derives it; the engine reads
    one indexed row.

    Every field is nullable ON PURPOSE. Null means "not enough evidence yet", which is different
    from zero, and lets every consumer stay neutral for a new user instead of scoring them on noise.
    """

    __tablename__ = "user_adaptation_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # How many days of history fed this, so consumers can judge how much to trust it.
    days_observed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- when this person actually gets things done -------------------------------------------
    # {"9": 0.71, "14": 0.32, ...} — completion rate by LOCAL hour of day.
    completion_by_hour: Mapped[dict | None] = mapped_column(_JSONMap, nullable=True)
    # {"0": 0.6, ... "6": 0.2} — by weekday, Monday = 0.
    completion_by_weekday: Mapped[dict | None] = mapped_column(_JSONMap, nullable=True)

    # --- what they say yes to ------------------------------------------------------------------
    # {"errand": 0.8, "deep_work": 0.3} — acceptance rate by task CATEGORY. The pre-existing
    # learning was keyed on action_type only, which is far coarser than what the user rejects.
    acceptance_by_category: Mapped[dict | None] = mapped_column(_JSONMap, nullable=True)
    acceptance_by_action_type: Mapped[dict | None] = mapped_column(_JSONMap, nullable=True)

    # --- how good our estimates are ------------------------------------------------------------
    # {"shop_groceries": 1.4} — actual / predicted, per task type. >1 means we under-estimate.
    estimate_ratio_by_type: Mapped[dict | None] = mapped_column(_JSONMap, nullable=True)

    # --- energy ---------------------------------------------------------------------------------
    # {"low": 3, "medium": 12, "high": 20} — energy level at the moment work was completed.
    completions_by_energy: Mapped[dict | None] = mapped_column(_JSONMap, nullable=True)
    # How much the user's own check-ins differ from what we inferred, as a signed mean of ranks.
    # Negative = we consistently overestimate their energy. Calibration input (TIME-289).
    energy_bias: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- rhythm ----------------------------------------------------------------------------------
    typical_wake_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_first_task_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_wind_down_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The user's timezone when this was computed — bucketing is only meaningful against it.
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
