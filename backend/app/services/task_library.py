"""The baseline task library — what TimeSense assumes about a task before it knows the user.

This is the "sensible defaults" layer the assistant starts from: a catalogue of the kinds of task
people actually capture, each carrying a typical duration AND a difficulty. Per-user learning
(TIME-286) refines the duration from real observations; difficulty stays as the honest starting
point for how much capacity a task needs.

Why it exists (TIME-284):

1. The previous seed table had 15 broad categories, and its matcher fell through to a catch-all
   "general" bucket for most real titles. Because learned durations were stored per category, one
   learned number ended up serving every unmatched task — the "everything takes 23 minutes" bug.
   Finer types mean a learned value only ever applies to tasks genuinely like it.

2. Nothing in the codebase modelled DIFFICULTY. Required energy was inferred purely from duration
   (>= 45 min counted as "high energy"), so a 90-minute podcast was treated as demanding and a
   10-minute difficult phone call as trivial. Difficulty is a property of the work, not its length.

Difficulty levels:
  light    — little focus needed; fine when depleted, or as filler between commitments
  moderate — ordinary working attention
  deep     — sustained concentration; the thing to protect good energy for

Keep entries ordered specific → general within their category: the matcher takes the first hit, so
"book a flight" must be reachable before the generic "book" admin entry.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

LIGHT, MODERATE, DEEP = "light", "moderate", "deep"

VALID_DIFFICULTIES = frozenset({LIGHT, MODERATE, DEEP})

# Ranked most-capable first — used when comparing a task's demand to the user's current energy.
DIFFICULTY_RANK: dict[str, int] = {LIGHT: 0, MODERATE: 1, DEEP: 2}


@dataclass(frozen=True)
class TaskType:
    key: str
    display_name: str
    category: str
    typical_minutes: int
    difficulty: str
    keywords: tuple[str, ...] = field(default=())


def _t(key, name, category, minutes, difficulty, *keywords) -> TaskType:
    return TaskType(key, name, category, minutes, difficulty, tuple(keywords))


# The catch-all. Deliberately NEVER learned against (see TIME-286): a task we couldn't classify must
# not contribute its duration to a bucket that then answers for every other unclassified task.
GENERAL_KEY = "general"

# Common English inflections a keyword is allowed to match, so "order" also matches "ordered" and
# "orders" without the keyword being able to start inside another word. Irregular forms that double
# a consonant (run -> running) cannot be derived this way and are listed explicitly in the library.
_INFLECTION_SUFFIX = r"(?:s|es|ed|d|ing)?"

TASK_TYPES: list[TaskType] = [
    # ── health & medical appointments ───────────────────────────────────────────────────
    _t("appt_doctor", "Doctor appointment", "appointment", 60, LIGHT,
       "doctor", "physician", "gp appointment", "clinic", "checkup", "check-up", "physical exam"),
    _t("appt_dentist", "Dentist appointment", "appointment", 60, LIGHT,
       "dentist", "dental", "teeth cleaning", "orthodontist"),
    _t("appt_therapy", "Therapy session", "appointment", 55, MODERATE,
       "therapy", "therapist", "counseling", "counselling", "psychiatrist"),
    _t("appt_optician", "Eye appointment", "appointment", 45, LIGHT,
       "optician", "optometrist", "eye exam", "eye test"),
    _t("appt_specialist", "Specialist appointment", "appointment", 60, LIGHT,
       "chiropractor", "dermatologist", "physio", "physical therapy", "podiatrist", "specialist"),
    _t("appt_vet", "Vet appointment", "appointment", 45, LIGHT, "vet", "veterinar"),
    _t("appt_haircut", "Haircut", "appointment", 45, LIGHT,
       "haircut", "barber", "salon", "hair appointment"),
    _t("appt_scan", "Scan or test", "appointment", 45, LIGHT,
       "x-ray", "xray", "mri", "ultrasound", "blood test", "bloods", "scan appointment", "biopsy"),
    _t("appt_vaccine", "Vaccination", "appointment", 20, LIGHT,
       "vaccine", "vaccination", "jab", "flu shot", "booster", "immunisation", "immunization"),
    _t("health_medication", "Medication", "health", 5, LIGHT,
       "medication", "meds", "take my pill", "pills", "tablet", "inhaler", "prescription refill"),
    _t("health_physio_exercises", "Physio exercises", "health", 20, MODERATE,
       "physio exercises", "rehab exercises", "stretches", "stretching", "mobility"),
    _t("health_mental", "Mental health time", "health", 30, MODERATE,
       "journal", "journalling", "journaling", "gratitude", "reflect on", "check in with myself"),
    _t("appt_generic", "Appointment", "appointment", 60, LIGHT, "appointment"),

    # ── meetings & calls ────────────────────────────────────────────────────────────────
    _t("meeting_standup", "Standup", "meeting", 15, LIGHT,
       "standup", "stand-up", "scrum", "daily sync"),
    _t("meeting_one_on_one", "1:1", "meeting", 30, MODERATE,
       "1:1", "1-1", "one-on-one", "one on one", "check-in with", "checkin with"),
    _t("meeting_interview", "Interview", "meeting", 60, DEEP,
       "interview", "screening call", "panel"),
    _t("meeting_review", "Review meeting", "meeting", 60, MODERATE,
       "retro", "retrospective", "review meeting", "performance review", "sprint planning"),
    _t("meeting_client", "Client meeting", "meeting", 60, DEEP,
       "client meeting", "customer meeting", "stakeholder", "pitch", "demo to"),
    _t("meeting_generic", "Meeting", "meeting", 30, MODERATE,
       "meeting", "sync", "catch up", "catch-up", "zoom", "google meet", "teams call", "huddle"),
    _t("call_quick", "Quick call", "call", 15, LIGHT,
       "quick call", "ring", "give a call", "call back", "callback"),
    _t("call_generic", "Phone call", "call", 20, MODERATE,
       "call", "phone", "facetime", "dial"),

    # ── correspondence ──────────────────────────────────────────────────────────────────
    _t("email_triage", "Clear inbox", "email", 25, LIGHT,
       "inbox", "clear email", "email triage", "check email", "unread"),
    _t("email_reply", "Reply to email", "email", 10, LIGHT,
       "email", "e-mail", "reply to", "respond to", "follow up with", "follow-up with"),
    _t("email_write", "Write an email", "email", 20, MODERATE,
       "write an email", "draft an email", "compose", "send an email"),
    _t("email_unsubscribe", "Tidy the inbox", "email", 15, LIGHT,
       "unsubscribe", "spam", "archive email", "delete emails"),
    _t("message_reply", "Reply to a message", "message", 5, LIGHT,
       "reply to", "respond to the message", "get back to"),
    _t("message_group", "Post to a group", "message", 10, LIGHT,
       "group chat", "post in", "announce", "share with the team"),
    _t("message_send", "Send a message", "message", 5, LIGHT,
       "message", "text", "dm", "slack", "whatsapp", "imessage", "ping"),

    # ── deep / knowledge work ───────────────────────────────────────────────────────────
    _t("write_report", "Write a report", "writing", 90, DEEP,
       "report", "whitepaper", "dissertation", "thesis", "case study"),
    _t("write_proposal", "Write a proposal", "writing", 90, DEEP,
       "proposal", "pitch deck", "business plan", "grant", "rfp"),
    _t("write_essay", "Write an essay", "writing", 90, DEEP,
       "essay", "blog post", "article draft", "newsletter", "write chapter", "chapter draft"),
    _t("write_notes", "Write up notes", "writing", 20, LIGHT,
       "notes", "write up", "write-up", "minutes", "recap"),
    _t("write_outline", "Outline something", "writing", 30, MODERATE,
       "outline", "brainstorm", "storyboard", "mind map"),
    _t("write_generic", "Writing", "writing", 45, DEEP,
       "write", "draft", "document", "documentation"),
    _t("code_feature", "Build a feature", "engineering", 120, DEEP,
       "implement", "build the", "feature", "refactor", "migrate", "integrate"),
    _t("code_bugfix", "Fix a bug", "engineering", 60, DEEP,
       "bug", "fix the", "debug", "hotfix", "regression", "broken"),
    _t("code_review", "Code review", "engineering", 30, DEEP,
       "code review", "review pr", "review the pr", "pull request", "pr", "merge request"),
    _t("code_deploy", "Deploy / release", "engineering", 45, DEEP,
       "deploy", "release", "ship the", "rollout", "roll out"),
    _t("study_research", "Research something", "reading", 60, DEEP,
       "research", "look into", "investigate", "compare options", "evaluate"),
    _t("study_course", "Study / course", "reading", 60, DEEP,
       "study", "course", "lecture", "revise", "revision", "practice problems", "homework"),
    _t("read_article", "Read an article", "reading", 20, MODERATE,
       "read the article", "read article", "blog", "newsletter read"),
    # "book" is far more often the VERB in a task list ("book a table", "book the dentist") than the
    # noun, so the noun sense has to carry its own context or it steals every reservation task.
    _t("read_book", "Read a book", "reading", 45, MODERATE,
       "read", "chapter", "my book", "the book", "book club", "finish the novel"),
    _t("teach_someone", "Teach or tutor someone", "teaching", 60, DEEP,
       "teach", "tutor", "tutoring", "coach", "mentor", "walk through", "show them how",
       "explain to", "onboard"),
    _t("help_someone", "Help someone with something", "teaching", 45, MODERATE,
       "help with", "give a hand", "assist", "support with", "sort out for"),
    _t("study_assignment", "Assignment or coursework", "education", 90, DEEP,
       "assignment", "coursework", "essay due", "problem set", "lab report", "submit the paper"),
    _t("study_exam", "Exam or test", "education", 120, DEEP,
       "exam", "final", "midterm", "sit the test", "take the test"),
    _t("study_enrol", "School or course admin", "education", 30, MODERATE,
       "enrol", "enroll", "registration for", "tuition", "school forms", "parent portal"),
    _t("plan_review", "Weekly review", "planning", 30, MODERATE,
       "weekly review", "review the week", "retrospective on", "look back at the week"),
    _t("plan_day", "Plan the day", "planning", 15, MODERATE,
       "plan my day", "plan the day", "plan tomorrow", "daily plan", "prioritise", "prioritize"),
    _t("plan_project", "Plan a project", "planning", 60, DEEP,
       "plan the", "planning", "roadmap", "scope out", "spec out"),
    _t("finance_budget", "Budgeting", "admin", 45, DEEP,
       "budget", "finances", "expenses", "accounting", "reconcile"),
    _t("finance_taxes", "Taxes", "admin", 120, DEEP,
       "taxes", "tax return", "hmrc", "irs", "vat"),

    # ── admin & life logistics ──────────────────────────────────────────────────────────
    _t("admin_pay_bill", "Pay a bill", "admin", 10, LIGHT,
       "pay the", "pay bill", "bill", "invoice", "rent", "utility"),
    _t("admin_book", "Book something", "admin", 20, MODERATE,
       "book a", "book flight", "book appointment", "booking", "rebook",
       "reserve", "reservation"),
    _t("admin_form", "Fill in a form", "admin", 30, MODERATE,
       "form", "paperwork", "application", "register for", "sign up for", "renew"),
    _t("admin_cancel", "Cancel something", "admin", 15, LIGHT,
       "cancel", "unsubscribe", "close account"),
    _t("admin_insurance", "Insurance / claims", "admin", 45, MODERATE,
       "insurance", "claim", "policy"),
    _t("finance_invest", "Investments or savings", "admin", 45, DEEP,
       "invest", "investment", "portfolio", "savings", "pension", "401k", "isa", "stocks"),
    _t("finance_expenses", "Expenses or reimbursement", "admin", 25, MODERATE,
       "expenses", "expense report", "reimbursement", "receipts", "timesheet"),
    _t("admin_subscription", "Review a subscription", "admin", 15, LIGHT,
       "subscription", "renew the plan", "downgrade", "upgrade the plan"),
    _t("admin_appointment_book", "Make an appointment", "admin", 10, LIGHT,
       "make an appointment", "schedule an appointment", "call to book"),
    _t("admin_generic", "Admin task", "admin", 20, MODERATE,
       "admin", "sort out", "deal with", "chase up"),

    # ── errands & shopping ──────────────────────────────────────────────────────────────
    _t("shop_groceries", "Grocery shopping", "shopping", 45, LIGHT,
       "groceries", "grocery", "supermarket", "food shop", "tesco", "walmart", "aldi", "costco"),
    _t("shop_pharmacy", "Pharmacy", "errand", 20, LIGHT,
       "pharmacy", "chemist", "prescription", "medicine", "boots", "walgreens", "cvs"),
    _t("errand_return", "Return a purchase", "errand", 25, LIGHT,
       "return the", "send back", "returns"),
    _t("shop_online", "Order online", "shopping", 15, LIGHT,
       "order online", "add to cart", "order a", "order the", "order new", "order some",
       "reorder", "amazon"),
    _t("shop_generic", "Shopping", "shopping", 45, LIGHT,
       "buy", "shop", "shopping", "store", "mall", "ikea", "home depot", "target"),
    _t("errand_pickup", "Pick something up", "errand", 25, LIGHT,
       "pick up", "pickup", "collect", "fetch"),
    _t("errand_dropoff", "Drop something off", "errand", 25, LIGHT,
       "drop off", "drop-off", "dropoff", "post office", "mail the", "ship the"),
    _t("errand_bank", "Bank errand", "errand", 30, LIGHT, "bank", "atm", "deposit"),
    _t("errand_fuel", "Fuel / charge the car", "errand", 15, LIGHT,
       "gas station", "petrol", "fuel", "charge the car", "car wash"),
    _t("pet_walk", "Walk the dog", "pet", 30, LIGHT,
       "walk the dog", "dog walk", "take the dog out"),
    _t("pet_care", "Look after a pet", "pet", 15, LIGHT,
       "feed the dog", "feed the cat", "feed the pet", "litter", "clean the tank", "groom the dog"),
    _t("pet_groomer", "Pet grooming or boarding", "pet", 60, LIGHT,
       "groomer", "kennel", "cattery", "pet sitter", "boarding"),
    _t("vehicle_service", "Car service or MOT", "vehicle", 120, LIGHT,
       "car service", "mot", "service the car", "mechanic", "garage appointment", "inspection"),
    _t("vehicle_tyres", "Tyres or repairs", "vehicle", 60, LIGHT,
       "tyre", "tire", "puncture", "brakes", "oil change", "battery replace"),
    _t("vehicle_admin", "Vehicle admin", "vehicle", 25, MODERATE,
       "road tax", "car insurance", "registration renewal", "dvla", "dmv", "license plate"),
    _t("errand_generic", "Errand", "errand", 30, LIGHT, "errand", "drop by", "stop by", "swing by"),

    # ── home & chores ───────────────────────────────────────────────────────────────────
    _t("chore_laundry", "Laundry", "chore", 30, LIGHT, "laundry", "washing", "ironing", "fold"),
    _t("chore_dishes", "Dishes", "chore", 15, LIGHT, "dishes", "dishwasher", "washing up"),
    _t("chore_clean", "Clean the house", "chore", 60, LIGHT,
       "clean", "tidy", "vacuum", "hoover", "mop", "dust", "declutter", "organize", "organise"),
    _t("chore_bins", "Take out the bins", "chore", 5, LIGHT, "bin", "bins", "trash", "garbage", "recycling"),
    _t("chore_garden", "Garden / yard", "chore", 60, LIGHT,
       "garden", "mow", "lawn", "yard", "weeding", "plants"),
    _t("chore_repair", "Fix something at home", "chore", 60, MODERATE,
       "repair", "fix the sink", "diy", "assemble", "install the", "handyman"),
    _t("home_tradesperson", "Arrange a tradesperson", "home", 30, MODERATE,
       "plumber", "electrician", "handyman", "boiler", "hvac", "contractor", "get a quote"),
    _t("home_decorate", "Decorating", "home", 120, LIGHT,
       "paint the", "painting the room", "wallpaper", "decorate", "put up shelves"),
    _t("home_beds", "Change the bedding", "chore", 15, LIGHT,
       "change the sheets", "bedding", "make the bed", "strip the bed"),
    _t("home_admin", "Household admin", "home", 25, MODERATE,
       "utility bill", "council tax", "mortgage", "landlord", "meter reading", "broadband"),
    _t("chore_generic", "Household chore", "chore", 30, LIGHT, "chore", "housework"),

    # ── cooking & meals ─────────────────────────────────────────────────────────────────
    _t("cook_meal", "Cook a meal", "cooking", 40, LIGHT,
       "cook", "dinner", "lunch", "breakfast", "recipe", "grill", "bake"),
    _t("cook_meal_prep", "Meal prep", "cooking", 90, LIGHT, "meal prep", "batch cook"),

    # ── exercise & self-care ────────────────────────────────────────────────────────────
    _t("exercise_run", "Run", "exercise", 40, MODERATE,
       # "running"/"jogging" double the final consonant, so the inflection rule can't derive them.
       "run", "running", "jog", "jogging", "5k", "10k", "marathon"),
    _t("exercise_gym", "Gym session", "exercise", 60, MODERATE,
       "gym", "workout", "lift", "weights", "training", "crossfit"),
    _t("exercise_class", "Fitness class", "exercise", 60, MODERATE,
       "yoga", "pilates", "spin class", "class at"),
    _t("exercise_walk", "Walk", "exercise", 30, LIGHT, "walk", "stroll", "steps"),
    _t("exercise_cycle", "Cycle", "exercise", 45, MODERATE, "bike", "cycle", "cycling", "ride"),
    _t("exercise_swim", "Swim", "exercise", 45, MODERATE, "swim", "swimming", "pool"),
    _t("hobby_practice", "Practise a skill", "hobby", 45, MODERATE,
       "practice", "practise", "rehearse", "piano", "guitar", "instrument", "drills"),
    _t("hobby_creative", "Creative project", "hobby", 60, MODERATE,
       "paint", "draw", "sketch", "knit", "sew", "woodwork", "photography", "edit the video"),
    _t("care_teeth", "Brush teeth", "personal_care", 5, LIGHT,
       "brush my teeth", "brush teeth", "floss", "mouthwash"),
    _t("care_shower", "Shower or bath", "personal_care", 20, LIGHT,
       "shower", "bath", "wash my hair"),
    _t("care_skincare", "Skincare or grooming", "personal_care", 10, LIGHT,
       "skincare", "shave", "moisturise", "moisturize", "nails", "makeup"),
    _t("care_getready", "Get ready", "personal_care", 25, LIGHT,
       "get ready", "get dressed", "getting ready"),
    _t("selfcare_rest", "Rest / recharge", "health", 20, LIGHT,
       "rest", "nap", "break", "recharge", "meditate", "meditation", "breathe"),

    # ── social & family ─────────────────────────────────────────────────────────────────
    _t("social_meetup", "See someone", "social", 90, LIGHT,
       "coffee with", "lunch with", "dinner with", "drinks with", "meet up", "meetup",
       "hang out", "visit"),
    _t("social_event", "Event", "social", 120, LIGHT,
       "party", "wedding", "birthday", "concert", "game night", "dinner party"),
    _t("family_childcare", "Kids / childcare", "social", 45, LIGHT,
       "school run", "pick up the kids", "daycare", "nursery", "playdate", "parents evening"),
    _t("family_partner_time", "Time with my partner", "family", 90, LIGHT,
       "with my wife", "with my husband", "with my partner", "with my girlfriend",
       "with my boyfriend", "date night", "time together", "spend time with my"),
    _t("family_time", "Family time", "family", 90, LIGHT,
       "family time", "with the family", "with my kids", "with the kids", "with my son",
       "with my daughter", "with my mum", "with my mom", "with my dad"),
    _t("family_homework", "Help with homework", "family", 45, MODERATE,
       "homework", "reading practice", "spellings", "help them with school"),
    _t("family_bedtime", "Bedtime routine", "family", 45, LIGHT,
       "bedtime", "bath and bed", "put the kids to bed", "bedtime story"),
    _t("family_appointment", "Appointment for someone else", "family", 60, LIGHT,
       "kids appointment", "kids cut", "take them to", "drop them at"),
    _t("social_call_family", "Call family", "social", 30, LIGHT,
       "call mum", "call mom", "call dad", "call grandma", "call my"),

    # ── travel ──────────────────────────────────────────────────────────────────────────
    _t("travel_commute", "Commute", "travel", 30, LIGHT, "commute", "drive to work"),
    _t("travel_flight", "Flight", "travel", 180, LIGHT, "flight", "airport", "fly to"),
    _t("travel_pack", "Pack", "travel", 45, LIGHT, "pack", "packing", "suitcase"),
    _t("travel_generic", "Travel", "travel", 45, LIGHT, "drive", "trip", "travel", "go to"),
]

# Every task the matcher can't place. Its duration is intentionally middling and it is never learned.
GENERAL_TYPE = _t(GENERAL_KEY, "Task", "general", 30, MODERATE)

_BY_KEY: dict[str, TaskType] = {t.key: t for t in TASK_TYPES} | {GENERAL_KEY: GENERAL_TYPE}


def all_type_keys() -> list[str]:
    """Every valid key, including the catch-all — the allowed set for LLM classification."""
    return list(_BY_KEY.keys())


def get_type(type_key: str | None) -> TaskType:
    """Look up a type, falling back to the catch-all for unknown/missing keys.

    Unknown keys degrade rather than raise: a model returning something invented must not break
    task creation, and a type removed from the library must not break existing rows.
    """
    if not type_key:
        return GENERAL_TYPE
    return _BY_KEY.get(type_key.strip().lower(), GENERAL_TYPE)


def is_known_type(type_key: str | None) -> bool:
    return bool(type_key) and type_key.strip().lower() in _BY_KEY


def normalize_difficulty(value: str | None) -> str | None:
    """Accept a difficulty only if it's one we model; anything else becomes None so the library's
    own value is used instead of a guess."""
    if not value:
        return None
    v = value.strip().lower()
    return v if v in VALID_DIFFICULTIES else None


@lru_cache(maxsize=1)
def _compiled_patterns() -> tuple[list[tuple[re.Pattern[str], TaskType]],
                                  list[tuple[re.Pattern[str], TaskType]]]:
    """One whole-word pattern per keyword, in library order.

    EVERY keyword is anchored at both ends. The previous rule anchored by LENGTH — only keywords of
    three characters or fewer got a closing boundary — and that was backwards in effect:

      * short keywords, where tolerating inflection would be relatively safe, were locked to whole
        words, so `run` missed "running";
      * long keywords, where a false substring match is most likely, were left open at the end, so
        `text` matched "textbook" and `book` matched "booklet".

    Real captured titles hit both. A wrong type is worse than no type, because the catch-all is
    never learned against (TIME-286) whereas a wrong type actively teaches the wrong duration
    bucket — "Buy a textbook" was training a 5-minute message bucket with a shopping trip.

    Inflection is now handled EXPLICITLY rather than by leaving the end open: a keyword may match a
    common English suffix (plural, gerund, past tense). Forms that double a final consonant
    ("run" -> "running") can't be derived by rule and are listed in the library instead.
    """
    phrases: list[tuple[re.Pattern[str], TaskType]] = []
    words: list[tuple[re.Pattern[str], TaskType]] = []
    for task_type in TASK_TYPES:
        for keyword in task_type.keywords:
            kw = keyword.strip()
            if not kw:
                continue
            is_phrase = " " in kw
            # A multi-word phrase is already specific enough that suffixing it adds nothing.
            suffix = "" if is_phrase else _INFLECTION_SUFFIX
            compiled = re.compile(rf"\b{re.escape(kw)}{suffix}\b")
            (phrases if is_phrase else words).append((compiled, task_type))
    return phrases, words


def classify(title: str) -> TaskType:
    """Best-effort type for a task title, by keyword. Deterministic and LLM-free — this is the
    fallback whenever the model is unavailable or returns something unusable.

    A multi-word PHRASE beats a single-word keyword; within each class, library order decides.

    It used to be plain first-match-wins, which meant a type's position in the file decided the
    answer. That held while the library was small and broke as soon as it grew (TIME-302): "Submit
    the expense report" matched `report` before `expense report`, and "Book the car service" matched
    a generic booking keyword before `car service`, purely because the writing and admin sections
    appear earlier in the file.

    Ranking by keyword LENGTH was tried and is worse: it makes "appointment" (11 chars, generic)
    beat "dentist" (7 chars, specific), so "Book dentist appointment" stops resolving to the dentist
    type. Length measures verbosity, not specificity.

    A multi-word phrase, though, is a genuinely more specific claim about the title than a single
    word — it had to match more of it. So phrases are tried first, in library order, and single
    words second. That keeps the deliberate specific-before-general ordering within each section
    working exactly as before, while letting a cross-domain phrase win over an unrelated section's
    generic word.
    """
    text = (title or "").lower().strip()
    if not text:
        return GENERAL_TYPE
    phrases, words = _compiled_patterns()
    for group in (phrases, words):
        for pattern, task_type in group:
            if pattern.search(text):
                return task_type
    return GENERAL_TYPE


def baseline_minutes(title: str) -> int:
    return classify(title).typical_minutes


def baseline_difficulty(title: str) -> str:
    return classify(title).difficulty


def resolve_classification(
    title: str,
    llm_type: str | None = None,
    llm_difficulty: str | None = None,
) -> tuple[str, str]:
    """The single place that decides a task's (task_type, difficulty).

    The deterministic matcher always produces an answer, so classification never depends on the LLM
    being reachable or well-behaved. An LLM suggestion is layered on top only when it is actually
    valid:

      * an unknown/invented type key is discarded — it must not reach the DB and become a learning
        bucket of its own (TIME-286 keys learned durations on this value);
      * an unrecognised difficulty is discarded in favour of the library's own value for the type.

    When the LLM does pick a type, that type's library difficulty becomes the default, so an
    LLM-chosen "code_review" doesn't silently keep the keyword match's difficulty.
    """
    if is_known_type(llm_type):
        chosen = get_type(llm_type)
    else:
        chosen = classify(title)
    return chosen.key, (normalize_difficulty(llm_difficulty) or chosen.difficulty)
