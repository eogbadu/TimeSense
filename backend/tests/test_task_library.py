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
        ("Write chapter 3 of the thesis", "write_report", "the writing sense must still win"),
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
