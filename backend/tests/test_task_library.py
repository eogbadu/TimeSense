"""TIME-284 — the baseline task library.

The point of these tests is not that any single title maps to any particular key — keyword matching
will always have judgement calls. It's the two properties that caused real bugs:

  1. Realistic titles must not pile into the catch-all bucket. They did (~1 in 3), and because
     learned durations were stored per bucket, that one bucket's learned number ended up answering
     for most tasks — the "everything takes 23 minutes" report.
  2. Difficulty must be independent of duration. It wasn't modelled at all; required energy was
     inferred from length, so a long easy task looked demanding and a short hard one looked trivial.
"""
from __future__ import annotations

import pytest

from app.services.task_duration import infer_category
from app.services.task_library import (
    DIFFICULTY_RANK,
    GENERAL_KEY,
    TASK_TYPES,
    VALID_DIFFICULTIES,
    all_type_keys,
    baseline_difficulty,
    baseline_minutes,
    classify,
    get_type,
    is_known_type,
    normalize_difficulty,
)

# A spread of how people actually phrase captures — work, home, admin, health, social, errands.
REALISTIC_TITLES = [
    "Book dentist appointment", "Call mum", "Reply to Sarah's email", "Finish the quarterly report",
    "Buy groceries", "Pick up dry cleaning", "Go for a run", "Take out the bins",
    "Pay the electricity bill", "Review Tom's PR", "Deploy the new release", "Standup",
    "1:1 with manager", "Plan my day", "Write blog post about onboarding", "Research CRM options",
    "Clean the kitchen", "Do the laundry", "Meal prep for the week", "Renew car insurance",
    "Cancel gym membership", "Fill in visa application", "Drop off package at post office",
    "Pick up the kids from school", "Coffee with James", "Dinner with the in-laws",
    "Book flights to Lisbon", "Pack for the trip", "Fix the leaking sink", "Mow the lawn",
    "Study for the exam", "Read chapter 4", "Meditate", "Physio appointment", "Get a haircut",
    "Vet appointment for the dog", "Order new laptop charger", "Fix the login bug",
    "Refactor the auth module", "Write up meeting notes", "Outline Q4 roadmap", "Do my taxes",
    "Reconcile the accounts", "Chase up the invoice", "Send Slack message to design team",
    "Clear inbox", "Interview candidate for backend role", "Client meeting with Acme", "Retro",
    "Sprint planning", "Swim at the leisure centre", "Cycle to the office", "Walk the dog", "Nap",
    "Yoga class", "Gym session", "Grocery shopping at Aldi", "Prescription pickup at pharmacy",
    "Deposit cheque at bank", "Fill up with petrol", "Wash the dishes", "Vacuum the living room",
    "Assemble the IKEA shelf", "Cook dinner", "Bake a birthday cake", "Attend Ana's wedding",
    "Parents evening", "Commute to office", "Flight to Berlin", "Visit grandma",
    "Reserve a table for Friday", "Unsubscribe from newsletters", "Register for the conference",
    "Draft the proposal", "Investigate the slow query", "Prioritize backlog", "Therapy session",
    "Eye test", "Doctor checkup", "Quick call with Ben", "Tidy the bedroom",
    "Return the Amazon order", "Buy a birthday present", "Practice piano", "Revise for finals",
    "Update documentation", "Ship the hotfix", "Debug the failing test", "Budget for next month",
]

CATCH_ALL_BUDGET = 0.10   # at most 1 in 10 may fall through


def test_library_is_internally_consistent():
    keys = [t.key for t in TASK_TYPES]
    assert len(keys) == len(set(keys)), "duplicate type keys"
    for t in TASK_TYPES:
        assert t.difficulty in VALID_DIFFICULTIES, f"{t.key} has difficulty {t.difficulty!r}"
        assert t.typical_minutes > 0, f"{t.key} has a non-positive duration"
        assert t.keywords, f"{t.key} has no keywords, so it can never be matched"
        assert t.key == t.key.lower(), f"{t.key} should be lower-case"


def test_realistic_titles_do_not_fall_into_the_catch_all():
    missed = [t for t in REALISTIC_TITLES if classify(t).key == GENERAL_KEY]
    rate = len(missed) / len(REALISTIC_TITLES)
    assert rate <= CATCH_ALL_BUDGET, f"{rate:.0%} fell through: {missed}"


def test_new_library_is_a_large_improvement_on_the_old_seed_table():
    """The regression this ticket exists to prevent. The old 15-category table sent about a third of
    realistic titles to 'general'; since learning was keyed on that bucket, one number answered for
    most tasks."""
    old_missed = [t for t in REALISTIC_TITLES if infer_category(t) == "general"]
    new_missed = [t for t in REALISTIC_TITLES if classify(t).key == GENERAL_KEY]
    assert len(new_missed) < len(old_missed) / 3, (
        f"expected a big improvement; old={len(old_missed)} new={len(new_missed)}"
    )


def test_titles_spread_across_many_distinct_buckets():
    """Granularity is the actual fix — a low catch-all rate would mean nothing if everything landed
    in two or three types instead."""
    old_buckets = {infer_category(t) for t in REALISTIC_TITLES}
    new_buckets = {classify(t).key for t in REALISTIC_TITLES}
    assert len(new_buckets) > 3 * len(old_buckets), (
        f"old={len(old_buckets)} new={len(new_buckets)}"
    )


@pytest.mark.parametrize(
    "title,expected_key",
    [
        ("Book dentist appointment", "appt_dentist"),
        ("Standup", "meeting_standup"),
        ("Review Tom's PR", "code_review"),
        ("Take out the bins", "chore_bins"),
        ("Do my taxes", "finance_taxes"),
        ("Grocery shopping at Aldi", "shop_groceries"),
        ("Practice piano", "hobby_practice"),
        ("Return the Amazon order", "errand_return"),
        ("Drop off package at post office", "errand_dropoff"),
    ],
)
def test_specific_keywords_beat_general_ones(title, expected_key):
    """Ordering is load-bearing: the first matching entry wins, so a specific type has to sit above
    the general one that would also match."""
    assert classify(title).key == expected_key


@pytest.mark.parametrize(
    "title,expected_key,why",
    [
        # Found by these tests during TIME-284 — each one was a real mis-classification.
        ("Grocery shopping at Aldi", "shop_groceries",
         "'ping' matched inside 'shop-PING at' under plain substring matching"),
        ("Practice piano", "hobby_practice",
         "'pr' (code review) start-anchored matches 'PRactice'"),
        ("Booking a table", "admin_book", "'book a' does not cover the -ing form"),
        ("Read chapter 4", "read_book", "'chapter' read as writing, not reading"),
        ("Write chapter 3 of the thesis", "write_essay",
         "the WRITING sense must win over reading; write_essay and write_report are both 90 min "
         "deep work, so which of the two wins does not change the estimate"),
        ("Book a table for Friday", "admin_book", "'book' as a verb, not a noun"),
        ("Read a book", "read_book", "'book' as a noun"),
        ("Book dentist appointment", "appt_dentist", "the appointment is more specific than booking"),
    ],
)
def test_keyword_matching_is_word_anchored_not_substring(title, expected_key, why):
    """Regression guard for the matcher itself. Unanchored substring matching quietly produced
    absurd results; short keywords additionally need both-side anchoring."""
    assert classify(title).key == expected_key, why


def test_difficulty_is_independent_of_duration():
    """The concrete failure of inferring effort from length: a long easy task and a short hard one."""
    long_and_light = classify("Flight to Berlin")
    short_and_deep = classify("Review Tom's PR")
    assert long_and_light.typical_minutes > short_and_deep.typical_minutes
    assert DIFFICULTY_RANK[long_and_light.difficulty] < DIFFICULTY_RANK[short_and_deep.difficulty]


def test_library_contains_both_long_light_and_short_deep_work():
    """If every long task were also deep, difficulty would be a redundant restatement of duration."""
    long_light = [t for t in TASK_TYPES if t.typical_minutes >= 60 and t.difficulty == "light"]
    short_deep = [t for t in TASK_TYPES if t.typical_minutes <= 30 and t.difficulty == "deep"]
    assert long_light, "no long-but-light types"
    assert short_deep, "no short-but-deep types"


def test_unknown_and_missing_types_degrade_to_the_catch_all():
    """A model inventing a key, or a type later removed from the library, must not break anything."""
    for bad in [None, "", "   ", "not_a_real_type", "APPT_DENTIST_TYPO"]:
        assert get_type(bad).key == GENERAL_KEY
        assert is_known_type(bad) is False


def test_known_types_are_case_and_whitespace_tolerant():
    assert get_type("  Appt_Dentist ").key == "appt_dentist"
    assert is_known_type(" appt_dentist ") is True


def test_catch_all_is_offered_as_a_valid_classification_key():
    """The LLM must be able to say "I don't know" rather than being forced into a wrong type."""
    assert GENERAL_KEY in all_type_keys()
    assert len(all_type_keys()) == len(TASK_TYPES) + 1


def test_normalize_difficulty_rejects_anything_unmodelled():
    assert normalize_difficulty("Deep") == "deep"
    assert normalize_difficulty("  LIGHT ") == "light"
    for bad in [None, "", "extreme", "very hard", "3"]:
        assert normalize_difficulty(bad) is None


def test_baseline_helpers_agree_with_classify():
    for title in REALISTIC_TITLES[:20]:
        t = classify(title)
        assert baseline_minutes(title) == t.typical_minutes
        assert baseline_difficulty(title) == t.difficulty


def test_empty_or_junk_titles_do_not_raise():
    for title in ["", "   ", None, "!!!", "🙂"]:
        t = classify(title)  # type: ignore[arg-type]
        assert t.key == GENERAL_KEY
        assert t.typical_minutes > 0


# ── TIME-301: the matcher, checked against REAL captured titles ──────────────────────────
#
# The cases below are not invented. They come from titles actually captured in the app, run
# through the audit script (TIME-300). That distinction matters: the library's original 0%
# fall-through was measured against a corpus written by the same author as the library, and
# against real data it was 13% with a silent misclassification.


@pytest.mark.parametrize(
    "title,expected,why",
    [
        # The reported bug. "text" is 4 chars, so the old length rule left it open at the end and
        # it matched inside "textbook" — turning a shopping trip into a 5-minute message task.
        ("Buy a textbook", "shop_generic", "'text' must not match inside 'textbook'"),
        # ...while the genuine word match still works.
        ("Text rita my love about tax strategy", "message_send", "'text' as a word still matches"),
        # The mirror failure: short keywords were locked to whole words, so inflections missed.
        ("Go running", "exercise_run", "'running' doubles the consonant; listed explicitly"),
        ("Went for a jog", "exercise_run", "the base form still matches"),
        ("Go swimming", "exercise_swim", "same doubling case"),
        # Inflection derived by rule rather than by leaving the keyword open-ended.
        ("Cleaned the kitchen", "chore_clean", "'clean' + 'ed' via the suffix rule"),
        ("Cleaning the kitchen", "chore_clean", "'clean' + 'ing' via the suffix rule"),
        # Ordering must still hold: a more specific type wins over a general one.
        ("Buy running shoes", "shop_generic", "shopping beats exercise for a purchase"),
    ],
)
def test_real_capture_regressions(title, expected, why):
    assert classify(title).key == expected, why


def test_no_keyword_can_begin_inside_another_word():
    """The structural guarantee, asserted directly against every compiled pattern rather than by
    sampling titles — a keyword must never match starting mid-word."""
    from app.services.task_library import _compiled_patterns

    phrases, words = _compiled_patterns()
    for pattern, task_type in phrases + words:
        assert pattern.pattern.startswith(r"\b"), f"{task_type.key}: {pattern.pattern}"
        assert pattern.pattern.endswith(r"\b"), (
            f"{task_type.key}: {pattern.pattern} is open at the end, so it can match inside a "
            "longer word (this is the 'textbook' bug)"
        )


def test_inflections_match_without_opening_the_keyword_up():
    """Both halves of the fix in one assertion: a keyword matches its common inflections, and still
    cannot match as a prefix of an unrelated word."""
    from app.services.task_library import _compiled_patterns

    # A real single-word keyword from the library (chore_clean), not an invented one.
    _phrases, words = _compiled_patterns()
    pattern = next(p for p, t in words if p.pattern == r"\bclean(?:s|es|ed|d|ing)?\b")
    for should in ("clean", "cleans", "cleaned", "cleaning"):
        assert pattern.search(should), f"{should!r} should match"
    for should_not in ("cleanser", "cleanliness", "unclean"):
        assert not pattern.search(should_not), f"{should_not!r} must not match"


# ── TIME-302: coverage of the domains real captures actually hit ─────────────────────────


@pytest.mark.parametrize(
    "title,expected_category",
    [
        # The three classifiable titles that fell through before the expansion.
        ("Brush my teeth", "personal_care"),
        ("Spend time with my wife today.", "family"),
        ("Teach Leanne and Jordyn to make apps", "teaching"),
        # Domains that were entirely absent.
        ("Walk the dog", "pet"),
        ("Book the car service", "vehicle"),
        ("Boiler service on Tuesday", "home"),
        # "help with" is a phrase and beats the single word "homework" — helping someone IS the
        # task here, which is a fairer reading than filing it as the child's study session.
        ("Help with homework", "teaching"),
        ("Take my medication", "health"),
        ("Submit the expense report", "admin"),
    ],
)
def test_previously_uncovered_domains_now_classify(title, expected_category):
    assert classify(title).category == expected_category


def test_a_bare_name_stays_in_the_catch_all():
    """"Ekele/Cynthia" is a real capture and is genuinely not classifiable. Guessing at it would be
    worse than admitting we don't know — the catch-all exists for exactly this, and is never
    learned against (TIME-286)."""
    assert classify("Ekele/Cynthia").key == GENERAL_KEY
    assert classify("Thing").key == GENERAL_KEY


def test_the_expansion_did_not_collapse_difficulty_into_duration():
    """Guard against the library drifting toward 'long = hard' as it grows, which would make
    difficulty a redundant restatement of duration."""
    long_light = [t for t in TASK_TYPES if t.typical_minutes >= 60 and t.difficulty == "light"]
    short_deep = [t for t in TASK_TYPES if t.typical_minutes <= 30 and t.difficulty == "deep"]
    assert len(long_light) >= 5, "no meaningful set of long-but-light types"
    assert short_deep, "no short-but-deep types"


def test_the_library_is_large_enough_to_be_a_real_prior():
    """TIME-284 specified 120-150 and shipped 79 without flagging the reduction; TIME-302 restores
    it. The floor matters more than the exact number — a thin library silently degrades every
    estimate in the domains it misses."""
    assert len(TASK_TYPES) >= 110, f"only {len(TASK_TYPES)} types"


def test_a_phrase_beats_an_unrelated_sections_single_word():
    """The ordering rule the expansion forced (TIME-302). With plain first-match-wins these all
    resolved to whichever section happened to appear earlier in the file."""
    assert classify("Submit the expense report").key == "finance_expenses"   # not write_report
    assert classify("Book the car service").key == "vehicle_service"          # not admin_book


def test_specific_types_still_win_within_a_section():
    """Phrase-first must not disturb the deliberate specific-before-general ordering. Ranking by
    keyword LENGTH broke exactly this — "appointment" (11 chars, generic) beat "dentist" (7)."""
    assert classify("Book dentist appointment").key == "appt_dentist"
    assert classify("Grocery shopping at Aldi").key == "shop_groceries"


# --- TIME-312: deliberate practice is its own kind of work -------------------------------------------
# "Solve 10+ Leetcode problems daily for a month" fell to the catch-all. The library had engineering
# types for building, fixing, reviewing and shipping, but nothing for practising — which is neither
# building a feature nor attending a lecture, and has its own honest duration.

@pytest.mark.parametrize("title", [
    "Solve 10+ Leetcode problems daily for a month",
    "leetcode grind",
    "do a kata",
    "advent of code day 3",
    "algorithm practice",
    "hackerrank problems",
    "codewars session",
    "coding challenge",
])
def test_coding_practice_is_recognised(title):
    assert classify(title).key == "code_practice"


@pytest.mark.parametrize("title", [
    "interview prep",
    "mock interview Friday",
    "practice system design",
    "technical interview practice",
    "coding interview prep",
])
def test_interview_preparation_is_recognised(title):
    assert classify(title).key == "interview_prep"


@pytest.mark.parametrize("title", [
    "follow the FastAPI tutorial",
    "work through the codelab",
    "code along with the video",
])
def test_tutorial_follow_along_is_recognised(title):
    assert classify(title).key == "study_tutorial"


def test_the_reported_title_no_longer_falls_to_the_catch_all():
    """The exact title the user was shown, with a 23-minute estimate on it."""
    t = classify("Solve 10+ Leetcode problems daily for a month")
    assert t.key != GENERAL_KEY
    assert t.typical_minutes >= 45, "deliberate practice is not a 20-minute job"
    assert t.difficulty == "deep"


@pytest.mark.parametrize("title,expected", [
    ("build the export feature", "code_feature"),
    ("fix the login bug", "code_bugfix"),
    ("review pr 42", "code_review"),
    ("deploy to production", "code_deploy"),
    ("study for the exam", "study_course"),
    ("do my homework", "study_course"),
    ("research pricing options", "study_research"),
])
def test_the_neighbouring_engineering_and_study_types_are_unchanged(title, expected):
    """New types must not steal from the ones already working — the failure mode of every previous
    matcher change (TIME-301, TIME-302)."""
    assert classify(title).key == expected


def test_practice_problems_belongs_to_exactly_one_type():
    """It was a keyword on study_course as well. A duplicate makes the winner depend on library
    ORDER rather than on meaning, which is how a matcher becomes unpredictable."""
    owners = [t.key for t in TASK_TYPES if "practice problems" in t.keywords]
    assert owners == ["code_practice"], f"claimed by {owners}"
