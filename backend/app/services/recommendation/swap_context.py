"""The context a swap is only meaningful inside of.

"Chose an errand over deep work" reads completely differently at 9am on good sleep than at 8pm when
depleted, and the surrounding state cannot be reconstructed after the fact — so it is snapshotted at
the moment the choice is expressed.

This lives on its own because there are now TWO ways a swap comes into being (TIME-316): the user
says so explicitly on the Now screen, or they simply finish a task while something else was
recommended. `_swap_signals` reads exact keys out of this dict, so the two sources building it
separately would eventually drift apart and silently stop being learned from.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.localtime import resolve_zone
from app.models.task import Task
from app.models.user import User
from app.repositories.user_location_repository import UserLocationRepository
from app.services.energy_service import EnergyService
from app.services.task_library import get_type

# How the pairing was learned. An explicit swap is a deliberate statement; a completion is inferred
# from behaviour. Both are real evidence, but they are not equally strong, and only a stored origin
# lets the learner weigh them differently (see `_swap_signals`).
ORIGIN_EXPLICIT = "explicit"
ORIGIN_COMPLETION = "completion"


def _category(task: Task | None) -> str | None:
    if task is None or not task.task_type:
        return None
    return get_type(task.task_type).category


async def build_swap_context(
    db: AsyncSession,
    user: User,
    rejected: Task | None,
    chosen: Task | None,
    now: datetime,
    user_timezone: str,
    origin: str = ORIGIN_EXPLICIT,
) -> dict:
    """The snapshot stored alongside a swap. `now` is the moment the CHOICE was expressed, not the
    moment the recommendation was made — `_swap_signals` buckets on `local_hour`, and the choice is
    what is being learned."""
    energy = await EnergyService(db).estimate(user.id, now=now, user_timezone=user_timezone)
    location = await UserLocationRepository(db).get_current(user.id, now)
    return {
        "local_hour": now.astimezone(resolve_zone(user_timezone)).hour,
        "energy": energy.level,
        # Named "category" historically; UserLocationState only carries a place name, and nothing
        # reads this key yet. Renaming it would fragment existing snapshots for no gain.
        "location_category": (location.place_name if location else None),
        "rejected_task_type": rejected.task_type if rejected else None,
        "rejected_category": _category(rejected),
        "chosen_task_type": chosen.task_type if chosen else None,
        "chosen_category": _category(chosen),
        "origin": origin,
    }
