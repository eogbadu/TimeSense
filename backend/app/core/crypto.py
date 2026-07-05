"""
Encryption at rest for integration OAuth tokens (TIME-056).

`EncryptedString` is a SQLAlchemy TypeDecorator over Text: values are Fernet-encrypted on write and
decrypted on read, so token columns are ciphertext at rest but plaintext to the app. impl=Text means
no schema migration is needed. The key comes from settings.token_encryption_key, or is derived
deterministically from secret_key when unset (works in dev; set a real key in production).
`decrypt_token` tolerates legacy plaintext (returns it unchanged) so pre-encryption values never
break a read.
"""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _derive_key() -> bytes:
    """A valid Fernet key (32 url-safe base64 bytes) from config."""
    configured = settings.token_encryption_key.strip()
    if configured:
        # Accept a real Fernet key as-is; otherwise fold arbitrary text into a valid one.
        try:
            Fernet(configured.encode())
            return configured.encode()
        except Exception:
            digest = hashlib.sha256(configured.encode()).digest()
            return base64.urlsafe_b64encode(digest)
    digest = hashlib.sha256(f"timesense-tokens:{settings.secret_key}".encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_key())
    return _fernet


def encrypt_token(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(value: str) -> str:
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        # Legacy plaintext (pre-encryption) — return as-is so reads never break.
        return value


class EncryptedString(TypeDecorator):
    """Transparently Fernet-encrypts a string column at rest."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt_token(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return decrypt_token(value)
