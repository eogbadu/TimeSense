import json
import logging

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def _load_service_account(raw: str) -> dict | None:
    """Parse the FIREBASE_SERVICE_ACCOUNT_JSON env value into a service-account dict.

    Handles two storage forms:
    1. Compact, correctly-escaped JSON (json.loads works directly).
    2. Pretty-printed JSON flattened onto a single .env line, where every real newline —
       structural *and* those inside the private_key string — was replaced with the two-character
       literal ``\\n``. Plain json.loads() fails on the structural ``\\n``; a blanket ``\\n`` →
       newline replace then fails strict JSON because the private_key ends up with real newlines
       inside a string. Replacing ``\\n`` with real newlines and parsing with ``strict=False``
       (which tolerates control characters inside strings) recovers a valid dict with a
       well-formed PEM private_key.

    Returns None for an empty/blank value or an unparseable one (callers fall back to ADC).
    """
    if not raw or not raw.strip() or raw.strip() == "{}":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(raw.replace("\\n", "\n"), strict=False)
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse FIREBASE_SERVICE_ACCOUNT_JSON: %s", exc)
        return None


def init_firebase() -> None:
    global _firebase_app
    if _firebase_app is not None:
        return

    try:
        service_account = _load_service_account(settings.firebase_service_account_json)
        if service_account:
            cred = credentials.Certificate(service_account)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(
                "Firebase Admin SDK initialized with service account for project: %s",
                service_account.get("project_id", settings.firebase_project_id),
            )
        else:
            # Fallback: use project ID only (works with Application Default Credentials)
            _firebase_app = firebase_admin.initialize_app(
                options={"projectId": settings.firebase_project_id}
            )
            logger.info(
                "Firebase Admin SDK initialized (project ID / ADC) for project: %s",
                settings.firebase_project_id,
            )
    except Exception as exc:
        logger.warning("Firebase init failed (auth disabled): %s", exc)


def get_firebase_app() -> firebase_admin.App | None:
    return _firebase_app
