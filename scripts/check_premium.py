"""Diagnose why an account is / isn't Premium. Run against the SAME DB the backend uses.

    python scripts/check_premium.py you@example.com

Prints: the loaded premium_test_emails allowlist, whether the user exists (and their exact stored
email), subscription + intro-trial state, and the final is_premium result — so you can see exactly
which check is (or isn't) granting Premium.
"""
from __future__ import annotations

import asyncio
import sys

# Run from repo root or backend/ — make `app` importable either way.
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402
from app.services.subscription_service import SubscriptionService  # noqa: E402


async def main(email: str) -> None:
    allow = {e.strip().lower() for e in settings.premium_test_emails.split(",") if e.strip()}
    print(f"premium_test_emails (loaded): {sorted(allow) or '(empty!)'}")
    print(f"looking up:                   {email.lower()}")
    print(f"in allowlist?                 {email.lower() in allow}")
    print(f"DB:                           {settings.database_url.split('@')[-1]}")  # host/db only, no creds

    async with AsyncSessionLocal() as db:
        user = await UserRepository(db).get_by_email(email)
        if user is None:
            print("\n✗ No user row with that exact email. The allowlist compares against the email on "
                  "your account (from your Firebase sign-in). Check the exact email below and match it.")
            # show a few emails to spot the right one
            from sqlalchemy import select
            from app.models.user import User
            rows = (await db.execute(select(User.email).limit(20))).all()
            print("  emails in this DB:", [r[0] for r in rows])
            return
        svc = SubscriptionService(db)
        print(f"\nuser found:  id={user.id}  email={user.email!r}  created_at={user.created_at}")
        print(f"has sub:     {(await svc.get_subscription(user.id)) is not None}")
        print(f"in trial:    {await svc.in_intro_trial(user.id)}")
        print(f"is_premium:  {await svc.is_premium(user.id)}   <-- what the app's entitlement returns")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python scripts/check_premium.py you@example.com")
        raise SystemExit(1)
    asyncio.run(main(sys.argv[1]))
