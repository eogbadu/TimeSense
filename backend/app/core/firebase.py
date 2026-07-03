import json
import logging

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def init_firebase() -> None:
    global _firebase_app
    if _firebase_app is not None:
        return

    try:
        service_account = json.loads(settings.firebase_service_account_json)
        if service_account:
            cred = credentials.Certificate(service_account)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Fallback: use project ID only (works with Application Default Credentials)
            _firebase_app = firebase_admin.initialize_app(
                options={"projectId": settings.firebase_project_id}
            )
        logger.info("Firebase Admin SDK initialized for project: %s", settings.firebase_project_id)
    except Exception as exc:
        logger.warning("Firebase init failed (auth disabled): %s", exc)


def get_firebase_app() -> firebase_admin.App | None:
    return _firebase_app
