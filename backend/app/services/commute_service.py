from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commute import CommuteEvent
from app.repositories.commute_repository import CommuteRepository
from app.repositories.consent_repository import ConsentRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.commute import LocationPingIn

_MIN_DISPLACEMENT_METERS = 500.0
_MIN_ELAPSED_MINUTES = 5
_MAX_ELAPSED_MINUTES = 120
_EARTH_RADIUS_METERS = 6_371_000.0


class LocationConsentRequired(Exception):
    """Raised when the user hasn't granted location_tracking consent."""


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * _EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class CommuteService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.commute_repo = CommuteRepository(db)
        self.consent_repo = ConsentRepository(db)
        self.notif_repo = NotificationRepository(db)

    def detect_from_pings(
        self, pings: list[LocationPingIn]
    ) -> tuple[str, datetime, datetime, int] | None:
        """Pure heuristic: displacement + duration thresholds, direction from time of day.
        Returns (direction, start, end, estimated_minutes) or None if no commute qualifies."""
        ordered = sorted(pings, key=lambda p: p.timestamp)
        first, last = ordered[0], ordered[-1]
        start, end = _utc(first.timestamp), _utc(last.timestamp)

        elapsed_minutes = int((end - start).total_seconds() / 60)
        if not (_MIN_ELAPSED_MINUTES <= elapsed_minutes <= _MAX_ELAPSED_MINUTES):
            return None

        distance = _haversine_meters(first.lat, first.lng, last.lat, last.lng)
        if distance < _MIN_DISPLACEMENT_METERS:
            return None

        direction = "to_work" if start.hour < 14 else "to_home"
        return direction, start, end, elapsed_minutes

    async def propose_commute(
        self, user_id: uuid.UUID, pings: list[LocationPingIn]
    ) -> CommuteEvent | None:
        effective_consent = await self.consent_repo.get_effective(user_id)
        if not effective_consent.get("location_tracking"):
            raise LocationConsentRequired("location_tracking consent not granted")

        candidate = self.detect_from_pings(pings)
        if candidate is None:
            return None
        direction, start, end, minutes = candidate

        notification = await self.notif_repo.create(
            user_id=user_id,
            type="approval_needed",
            title="Commute detected",
            body=f"Looks like you're commuting {direction.replace('_', ' ')}. Confirm?",
            channel="in_app",
        )
        return await self.commute_repo.create(
            user_id=user_id,
            direction=direction,
            detected_start=start,
            detected_end=end,
            estimated_minutes=minutes,
            notification_id=notification.id,
        )

    async def confirm(self, user_id: uuid.UUID, commute_id: uuid.UUID) -> bool:
        return await self.commute_repo.set_status(commute_id, user_id, "confirmed")

    async def reject(self, user_id: uuid.UUID, commute_id: uuid.UUID) -> bool:
        return await self.commute_repo.set_status(commute_id, user_id, "rejected")

    async def list_pending(self, user_id: uuid.UUID) -> list[CommuteEvent]:
        return await self.commute_repo.list_pending(user_id)
