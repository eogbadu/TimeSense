"""
Google Assistant fulfillment (Dialogflow webhook).

A Dialogflow agent (configured out-of-band) maps spoken phrases to intents and calls
POST /api/v1/assistant/webhook. This module parses the Dialogflow WebhookRequest, dispatches the
intent to the matching TimeSense action, and builds the WebhookResponse spoken back to the user.

Exposes the same 5 actions as the iOS App Intents (TIME-052). Read-only / simple-write actions run
here; ReplanDay only tells the user to open the app, since replans require in-app approval.

Note: Google shut down conversational Actions on Google Assistant in June 2023 — this implements the
Dialogflow-webhook contract (request/response shapes + intent→action mapping) rather than a live
Assistant round-trip. Account linking (which would supply the user identity) is out of scope; the
endpoint is gated on the existing Firebase identity as the account-linked stand-in.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.meal_repository import MealRepository
from app.repositories.task_repository import TaskRepository
from app.services.task_scorer import TaskScorer
from app.services.usable_time_service import UsableTimeService


def parse_intent(body: dict) -> str:
    """Extract the Dialogflow intent display name from a WebhookRequest body."""
    return (
        (body or {})
        .get("queryResult", {})
        .get("intent", {})
        .get("displayName", "")
    )


def fulfillment_response(text: str) -> dict:
    """Build a Dialogflow ES WebhookResponse from spoken text."""
    return {
        "fulfillmentText": text,
        "fulfillmentMessages": [{"text": {"text": [text]}}],
    }


def _normalize(intent: str) -> str:
    return "".join(ch for ch in intent.lower() if ch.isalnum())


class GoogleAssistantService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.task_repo = TaskRepository(db)
        self.meal_repo = MealRepository(db)

    async def handle(self, intent: str, user_id: uuid.UUID) -> str:
        """Dispatch a Dialogflow intent to an action; returns spoken fulfillment text."""
        handler = _INTENT_HANDLERS.get(_normalize(intent))
        if handler is None:
            return (
                "Sorry, I didn't catch that. You can ask what to do next, log lunch, "
                "start focus, mark done, or replan your day."
            )
        return await handler(self, user_id)

    # ── Intent handlers ───────────────────────────────────────────────────────

    async def _what_to_do_next(self, user_id: uuid.UUID) -> str:
        best, usable = await self._best_task(user_id)
        if best is None:
            return "You're all caught up — nothing on your plate right now."
        return f"Do {best.title} next. You have {usable} minutes of usable time."

    async def _start_focus(self, user_id: uuid.UUID) -> str:
        best, _ = await self._best_task(user_id)
        if best is None:
            return "Nothing to focus on right now — you're all caught up."
        return f"Focusing on {best.title}. Let's go."

    async def _log_lunch(self, user_id: uuid.UUID) -> str:
        await self.meal_repo.log(user_id=user_id, meal_type="lunch", status="eaten")
        return "Logged your lunch."

    async def _mark_done(self, user_id: uuid.UUID) -> str:
        best, _ = await self._best_task(user_id)
        if best is None:
            return "There's nothing to mark done right now."
        await self.task_repo.update(best.id, user_id, status="done")
        return f"Nice — marked {best.title} as done."

    async def _replan_day(self, user_id: uuid.UUID) -> str:
        # Replans require explicit in-app approval — never applied from a voice command.
        return "Open TimeSense to review and approve your new plan."

    # ── Shared best-task selection (mirrors GET /now) ─────────────────────────

    async def _best_task(self, user_id: uuid.UUID):
        now = datetime.now(timezone.utc)
        tasks = await self.task_repo.list_by_user(user_id, limit=200)
        active = [t for t in tasks if t.status in ("pending", "in_progress")]
        usable = UsableTimeService().calculate(tasks, anchor=now)
        if not active:
            return None, usable
        ranked = TaskScorer().rank(active, usable, now)
        return (ranked[0] if ranked else None), usable


_INTENT_HANDLERS = {
    "whattodonext": GoogleAssistantService._what_to_do_next,
    "startfocus": GoogleAssistantService._start_focus,
    "loglunch": GoogleAssistantService._log_lunch,
    "markdone": GoogleAssistantService._mark_done,
    "replanday": GoogleAssistantService._replan_day,
}
