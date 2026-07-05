from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.integrations.google_assistant import (
    GoogleAssistantService,
    fulfillment_response,
    parse_intent,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/assistant", tags=["assistant"])


async def _get_user_id(current_user: CurrentUser, db: AsyncSession) -> uuid.UUID:
    user, _ = await UserService(db).get_or_create_user(current_user.uid, current_user.email or "")
    return user.id


@router.post("/webhook")
async def assistant_webhook(
    body: dict[str, Any],
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Dialogflow fulfillment webhook. Gated on the account-linked Firebase identity.

    Dispatches the recognized intent to a TimeSense action and returns spoken fulfillment text.
    """
    user_id = await _get_user_id(current_user, db)
    intent = parse_intent(body)
    text = await GoogleAssistantService(db).handle(intent, user_id)
    await db.commit()
    return fulfillment_response(text)
