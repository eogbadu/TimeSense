"""
Task duration knowledge — the seed "lookup table" the assistant starts with.

Every task gets a realistic time estimate from this table (via a category inferred from the title),
even when the LLM is unavailable. Per-user learned overrides (TaskDurationEstimate) refine these as
the assistant sees how long the user's tasks actually take — that per-user table is what makes the
estimates personal over time.
"""
from __future__ import annotations

# Seed estimate per category, in minutes. Deliberately conservative, round numbers.
DEFAULT_DURATIONS: dict[str, int] = {
    "appointment": 60,
    "meeting": 30,
    "call": 15,
    "email": 10,
    "message": 10,
    "shopping": 45,
    "errand": 30,
    "chore": 30,
    "exercise": 45,
    "cooking": 40,
    "writing": 45,
    "reading": 30,
    "admin": 20,
    "travel": 30,
    "general": 30,
}

# Ordered most-specific → most-general; the first category with a matching keyword wins.
CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("appointment", ("doctor", "dentist", "appointment", "checkup", "chiropractor", "therapy",
                     "haircut", "clinic", "vet", "physical")),
    ("meeting", ("meeting", "standup", "stand-up", "sync", "1:1", "one-on-one", "interview",
                 "zoom", "catch up", "catch-up")),
    ("call", ("call", "phone", "ring ", "dial", "facetime")),
    ("email", ("email", "e-mail", "reply", "respond", "inbox")),
    ("message", ("message", " text ", "dm ", "slack", "whatsapp", "imessage")),
    ("shopping", ("buy", "shop", "shopping", "groceries", "grocery", "store", "walmart", "target",
                  "costco", "mall", "home depot", "market", "ikea", "amazon", "order")),
    ("errand", ("errand", "pick up", "pickup", "drop off", "drop-off", "dropoff", "post office",
                "bank", "pharmacy", "gas station", "return", "deliver")),
    ("chore", ("clean", "tidy", "laundry", "dishes", "vacuum", "trash", "garbage", "mow", "wash",
               "organize", "declutter", "fold")),
    ("exercise", ("workout", "gym", "run", "jog", "exercise", "yoga", "walk", "bike", "swim",
                  "training", "lift", "stretch")),
    ("cooking", ("cook", "bake", "dinner", "lunch", "breakfast", "meal prep", "recipe", "grill")),
    ("writing", ("write", "draft", "report", "essay", "blog", "document", "proposal", "notes",
                 "outline", "summary")),
    ("reading", ("read", "book", "article", "study", "research", "review")),
    ("admin", ("pay", "bill", "invoice", "form", "paperwork", "taxes", "renew", "book ", "file ",
               "sign up", "cancel", "register")),
    ("travel", ("drive", "commute", "flight", "airport", "trip", "go to", "visit", "travel")),
]


def infer_category(title: str) -> str:
    """Map a task title to a duration category using keyword matching."""
    text = f" {title.lower().strip()} "
    for category, keywords in CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return "general"


def seed_duration(category: str) -> int:
    return DEFAULT_DURATIONS.get(category, DEFAULT_DURATIONS["general"])
