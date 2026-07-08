"""Return the configured push sender — real APNs when credentials (and h2) are present, else a
no-op NullPushSender."""

from __future__ import annotations

from app.core.config import settings
from app.services.push.sender import ApnsPushSender, NullPushSender, PushSender


def get_push_sender() -> PushSender:
    if settings.apns_key_id and settings.apns_team_id and settings.apns_private_key:
        sender = ApnsPushSender(
            key_id=settings.apns_key_id, team_id=settings.apns_team_id,
            private_key=settings.apns_private_key, bundle_id=settings.apns_bundle_id,
            use_sandbox=settings.apns_use_sandbox,
        )
        if sender.available:
            return sender
    return NullPushSender()
