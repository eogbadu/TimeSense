"""Tests for security hardening (TIME-056): token encryption, headers, rate limiting."""
import pytest
from sqlalchemy import text

from app.core.crypto import EncryptedString, decrypt_token, encrypt_token
from app.core.rate_limit import RateLimiter
from app.services.calendar_service import CalendarService


# ── Token encryption ──────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    ct = encrypt_token("xoxb-super-secret")
    assert ct != "xoxb-super-secret"
    assert decrypt_token(ct) == "xoxb-super-secret"


def test_decrypt_tolerates_legacy_plaintext():
    # A pre-encryption plaintext value must read back unchanged, not raise.
    assert decrypt_token("legacy-plain-token") == "legacy-plain-token"


def test_encrypted_string_type_impl_is_text():
    # impl=Text means the DB column type is unchanged → no migration needed.
    assert EncryptedString().impl.__class__.__name__ == "Text"


@pytest.mark.anyio
async def test_integration_token_encrypted_at_rest(db_session):
    import uuid
    from app.models.user import User
    user = User(firebase_uid="uid-sec-1", email="sec@example.com")
    db_session.add(user)
    await db_session.flush()

    svc = CalendarService(db_session)
    await svc.connect(user_id=user.id, provider="google", access_token="plaintext-token-xyz")
    await db_session.flush()

    # Raw column value (bypasses the TypeDecorator) is ciphertext...
    raw = (await db_session.execute(text("SELECT access_token FROM calendar_integrations"))).scalar_one()
    assert raw != "plaintext-token-xyz"
    assert "plaintext-token-xyz" not in raw

    # ...but the ORM read decrypts transparently.
    integration = await svc.get_integration(user.id, "google")
    assert integration.access_token == "plaintext-token-xyz"


# ── Security headers ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_security_headers_present(client):
    r = await client.get("/api/v1/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "no-referrer"
    assert "content-security-policy" in r.headers


# ── Rate limiting ─────────────────────────────────────────────────────────────

class _FakeRequest:
    def __init__(self, token: str = "Bearer t"):
        self.headers = {"authorization": token}
        self.client = type("C", (), {"host": "1.2.3.4"})()


@pytest.mark.anyio
async def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(times=2, seconds=60, name="test")
    req = _FakeRequest()
    await limiter(req)  # 1
    await limiter(req)  # 2
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await limiter(req)  # 3 → blocked
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


@pytest.mark.anyio
async def test_rate_limiter_is_per_caller():
    limiter = RateLimiter(times=1, seconds=60, name="test2")
    await limiter(_FakeRequest("Bearer user-a"))
    # A different caller isn't affected by user-a's usage.
    await limiter(_FakeRequest("Bearer user-b"))
