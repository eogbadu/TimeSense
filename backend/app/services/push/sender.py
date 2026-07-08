"""Push sender abstraction. NullPushSender is used when APNs isn't configured (no-op), so the
decision logic runs everywhere and only real delivery is gated. ApnsPushSender does token-based
(JWT/ES256) auth over HTTP/2; it never raises — a delivery failure returns False."""

from __future__ import annotations

import time
from typing import Protocol

import httpx

try:  # HTTP/2 is required by APNs; degrade gracefully if unavailable.
    import h2  # noqa: F401
    _H2_AVAILABLE = True
except ImportError:  # pragma: no cover
    _H2_AVAILABLE = False


class PushSender(Protocol):
    @property
    def available(self) -> bool: ...
    async def send(
        self, token: str, title: str, body: str, collapse_id: str | None = None,
        data: dict | None = None,
    ) -> bool: ...


class NullPushSender:
    @property
    def available(self) -> bool:
        return False

    async def send(
        self, token: str, title: str, body: str, collapse_id: str | None = None,
        data: dict | None = None,
    ) -> bool:
        return False


class ApnsPushSender:
    def __init__(self, key_id: str, team_id: str, private_key: str, bundle_id: str,
                 use_sandbox: bool = True, timeout: float = 10.0) -> None:
        self._key_id = key_id
        self._team_id = team_id
        self._private_key = private_key.replace("\\n", "\n")
        self._bundle_id = bundle_id
        self._host = "api.sandbox.push.apple.com" if use_sandbox else "api.push.apple.com"
        self._timeout = timeout
        self._jwt: str | None = None
        self._jwt_iat = 0

    @property
    def available(self) -> bool:
        return bool(self._key_id and self._team_id and self._private_key and self._bundle_id) and _H2_AVAILABLE

    def _auth_token(self) -> str:
        import jwt
        now = int(time.time())
        # APNs JWTs are valid up to 1h and reusable; refresh well before expiry.
        if self._jwt is None or now - self._jwt_iat > 3000:
            self._jwt = jwt.encode(
                {"iss": self._team_id, "iat": now}, self._private_key,
                algorithm="ES256", headers={"kid": self._key_id},
            )
            self._jwt_iat = now
        return self._jwt

    async def send(
        self, token: str, title: str, body: str, collapse_id: str | None = None,
        data: dict | None = None,
    ) -> bool:
        if not self.available:
            return False
        headers = {
            "authorization": f"bearer {self._auth_token()}",
            "apns-topic": self._bundle_id,
            "apns-push-type": "alert",
        }
        if collapse_id:
            headers["apns-collapse-id"] = collapse_id[:64]
        # Custom keys (type/task_id/…) ride alongside `aps` so the app can deep-link on tap.
        payload = {"aps": {"alert": {"title": title, "body": body}, "sound": "default"}}
        if data:
            payload.update(data)
        try:
            async with httpx.AsyncClient(http2=True, timeout=self._timeout) as client:
                resp = await client.post(
                    f"https://{self._host}/3/device/{token}", headers=headers, json=payload
                )
            return resp.status_code == 200
        except Exception:
            return False
