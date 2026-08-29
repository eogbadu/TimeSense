"""
Audit how well the baseline task library classifies REAL captured task titles.

    python scripts/audit_task_classification.py

Why this exists: the library's coverage was originally measured against a corpus written by the
same author as the library, which reported 0% fall-through. Run against real captures it was 13%,
and it also silently MISCLASSIFIED — "Buy a textbook" matched the `text` keyword and became a
5-minute message task. Self-graded coverage is not evidence, so this makes the measurement
repeatable against whatever data you point it at.

Read-only. Runs against whatever DATABASE_URL is configured, so it can be pointed at production.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from collections import Counter

# Run from repo root or backend/ — make `app` importable either way.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.task import Task  # noqa: E402
from app.services.task_library import (  # noqa: E402
    GENERAL_KEY,
    TASK_TYPES,
    classify,
)


def _suspicious_match(title: str) -> tuple[str, str] | None:
    """Detect the "textbook" signature: the title matched on a keyword that is a strict SUBSTRING
    of a longer word in the title, rather than matching a word.

    This is the failure mode that matters most, because a wrong type is worse than no type — the
    catch-all is never learned against, whereas a wrong type actively teaches the wrong duration
    bucket.
    """
    text = (title or "").lower()
    matched = classify(title)
    if matched.key == GENERAL_KEY:
        return None
    for keyword in matched.keywords:
        kw = keyword.strip()
        if not kw or " " in kw:
            continue
        # The keyword appears, but every occurrence is inside a longer word.
        if kw in text and not re.search(rf"\b{re.escape(kw)}\b", text):
            for word in re.findall(r"[a-z0-9']+", text):
                if kw in word and word != kw:
                    return kw, word
    return None


def report(titles: list[str]) -> int:
    """Print the audit for a list of titles. Returns the fall-through count.

    Kept separate from the database read so it can be exercised directly — including the empty
    case, which is the one most likely to blow up in front of someone running this for the first
    time against a fresh database.
    """
    unique = sorted({t for t in titles if t and t.strip()})
    if not unique:
        print("No task titles found — nothing to audit.")
        return 0

    fell_through: list[str] = []
    suspicious: list[tuple[str, str, str, str]] = []
    used: Counter[str] = Counter()

    for title in unique:
        matched = classify(title)
        used[matched.key] += 1
        if matched.key == GENERAL_KEY:
            fell_through.append(title)
        elif (hit := _suspicious_match(title)) is not None:
            keyword, inside = hit
            suspicious.append((title, matched.key, keyword, inside))

    total = len(unique)
    print(f"unique titles      : {total}")
    print(f"fell through       : {len(fell_through)}  ({len(fell_through) / total:.0%})")
    print(f"suspicious matches : {len(suspicious)}")
    print(f"distinct types used: {len([k for k in used if k != GENERAL_KEY])}\n")

    if fell_through:
        print("FELL THROUGH TO THE CATCH-ALL — candidates for new types.")
        print("(Genuinely unclassifiable captures, e.g. a bare name, SHOULD stay here.)")
        for t in fell_through:
            print(f"   - {t}")
        print()

    if suspicious:
        print("SUSPICIOUS — matched on a keyword found only INSIDE a longer word.")
        print("These are worse than a fall-through: a wrong type teaches the wrong duration.")
        for title, key, keyword, inside in suspicious:
            print(f"   - {title!r}\n       -> {key}  (keyword {keyword!r} matched inside {inside!r})")
        print()

    print("MOST-USED TYPES")
    for key, n in used.most_common(10):
        label = f"{key} (CATCH-ALL)" if key == GENERAL_KEY else key
        print(f"   {n:>3}  {label}")

    return len(fell_through)


async def main() -> None:
    print(f"DB: {settings.database_url.split('@')[-1]}")  # host/db only, no creds
    print(f"library: {len(TASK_TYPES)} types (+ catch-all)\n")
    async with AsyncSessionLocal() as db:
        titles = [row[0] for row in (await db.execute(select(Task.title))).all()]
    report(titles)


if __name__ == "__main__":
    asyncio.run(main())
