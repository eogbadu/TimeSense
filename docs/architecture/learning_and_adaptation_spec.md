# Learning and Adaptation

How TimeSense learns about one person and changes what it recommends — and, just as importantly,
what it still does **not** learn.

Written 2026-08-28, closing out the TIME-282..297 batch. This is the answer to two questions the
repo could not previously answer honestly:

> *"How exactly is TimeSense learning each user's habits and then adapting to them?"*
> *"Where is the data about how I've been using TimeSense, and how do we use it?"*

---

## 1. What it was before this batch

Worth recording, because the shape of the problem explains most of the design below.

| Mechanism | Keyed on | Fed back into scoring? |
|---|---|---|
| Duration EWMA | a coarse category, whose catch-all bucket swallowed ~30% of real titles | yes — and wrongly, see below |
| Acceptance rate | `action_type` only | yes, one number |
| "Learned Patterns" screen | 30-day live query | **no** |
| Behavioural patterns (Insights) | 28-day live query over HealthKit | **no** |

Two structural consequences:

1. **One learned number answered for most tasks.** Because most titles fell into the `general`
   bucket and the learned value was stored per bucket, a handful of coarse duration answers set the
   estimate for nearly everything the user captured. This is the "everything takes 23 minutes"
   report: `EWMA(0.3)` over 15, 30, 30 gives exactly 15 → 20 → 23.
2. **Most of the personalisation surface was inert.** Four of the eight weighted scoring factors
   were hard-coded identical for every task candidate, so **38%** of every score was a constant.
   (An early survey put this at 58%; that was wrong — it inverted the split. The real figure is
   38% inert / 62% varying, and `test_score_differentiation.py` pins it against `WEIGHTS`.)

---

## 2. Signals: what is stored, and where

Everything below is per-user and deletable through the existing privacy export/erase paths.

### Raw event tables — the ground truth

| Table | Holds | Written by |
|---|---|---|
| `recommendation_events` | every impression: surface, action type, domain, score, confidence, rank, explanation, and the eventual outcome | `/now`, push |
| `recommendation_feedback` | agree / disagree / done / snooze / not_now, plus the disagree **reason** | `/recommendations/feedback` |
| `recommendation_swaps` | **"not that — this instead"**: rejected task, chosen task, reason, and a context snapshot (local hour, energy, place, both tasks' types) | `/recommendations/swap` |
| `task_duration_observations` | raw "this actually took N minutes", with the estimate shown at the time | duration feedback, the in-app timer |
| `energy_checkins` | the user's own read on their energy, plus what the model inferred at that instant | `/energy/checkin` |
| `daily_activity`, `hourly_activity`, `workout_sessions`, `sleep_wake_events` | HealthKit ingest | iOS `HealthService` |
| `user_location_states` | the **current** place and position — one row, overwritten, never a history | iOS `LocationService` |
| `meal_events`, `commute_events`, `routine_assumptions` | day-shape signals | various |

### Derived tables — what has been concluded

| Table | Holds | Rebuilt by |
|---|---|---|
| `user_adaptation_profiles` | completion rate by local hour and weekday; acceptance by category and action type; estimate accuracy per task type; energy-at-completion; energy bias; typical wake / first-task / wind-down | nightly Celery job `timesense.rebuild_adaptation_profiles` |
| `task_duration_estimates` | per (user, task type) learned duration + sample count | on each observation |
| `weekly_insights` | the weekly summary, generated once per completed week and never recomputed | weekly Celery job |

**Rule: derived tables are never authoritative.** Everything in them can be rebuilt from the raw
tables. Dropping and regenerating them loses nothing.

---

## 3. How a signal becomes a different recommendation

```
capture ──► classify (library type + difficulty)
                │
                ▼
        estimate duration  ◄── learned per TYPE, shrunk toward the library baseline
                │
                ▼
   ┌──────── score the candidate ────────┐
   │  urgency        0.20   ← due date   │
   │  importance     0.20   ← priority   │
   │  context_fit    0.15   ← part of day × category × place × imminent commitment
   │  time_fit       0.12   ← duration vs free block
   │  energy_fit     0.10   ← required energy (difficulty) vs current energy
   │  location_fit   0.10   ← where the user actually is
   │  routine_fit    0.08   ← completion rate at this hour/weekday   [adaptation profile]
   │  user_pref_fit  0.05   ← acceptance by category                 [adaptation profile]
   └──────────────── minus penalties ────┘
                │
                ▼
        rank ──► recommend ──► impression logged
                │
                ▼
   agree / disagree(+reason) / swap(+pair) / done / duration observed
                │
                └──► raw tables ──► nightly rollup ──► next recommendation
```

### The energy model specifically

Energy is a **recovery budget that depletes**, not a reading of how active someone has been:

- last night's sleep sets a morning budget
- the day spends it: hours awake, exercise, meetings and deep work **already finished**, a long
  sedentary stretch
- a circadian shape applies on top (morning ramp, post-lunch dip, evening decline)
- a self-report check-in overrides all of it for four hours

Two honesty rules: with no health data it still answers from time of day (better than a constant),
but it will **never claim "high" without sleep evidence** — that claim invites starting something
demanding.

---

## 4. Rules that apply everywhere

These matter more than any individual metric, and every one of them is enforced by a test.

1. **Null, not zero, below a sample floor.** "No evidence" and "evidence of nothing" are different
   claims. A brand-new user's adaptation profile is entirely null, every learned fit sits at
   neutral 0.5, and ranking falls back to urgency and importance.
2. **Never learn on the catch-all.** An unclassified task teaches nothing transferable. Letting that
   bucket accumulate is precisely how one number came to answer for everything.
3. **Shrink toward the baseline.** A learned duration is blended with the library's typical value in
   proportion to the evidence behind it, so a single coarse tap nudges rather than replaces.
4. **Bucket in the user's timezone.** A UTC hour-of-day profile is meaningless outside UTC and
   silently re-buckets when the user travels.
5. **Adjustments relax, they don't tighten.** The per-user difficulty adjustment can make the engine
   *offer* something it would have suppressed (which the user can decline). It cannot *hide* work
   from someone whose data merely looks unusual.
6. **Absent data is neutral, not bad.** No location signal must not penalise every user who hasn't
   granted permission.
7. **Explain the mechanism.** Every scoring rule states something we could tell the user ("you can't
   run an errand from the sofa"), not a correlation.

---

## 5. What it still does NOT learn

Recorded deliberately, so nobody has to rediscover it.

- **The scoring weights are static.** They come from the build spec and are the same for everyone.
  Nothing tunes them per user.
- **The energy curve is not calibrated.** `energy_bias` — the signed gap between what the user
  reports and what the model infers — is collected and surfaced in the adaptation profile, but is
  **not yet applied**. Tuning a curve on a handful of points bakes in noise. This is the most
  obvious next step once there is real data.
- **No cross-user learning.** Nothing one user does affects another. The baseline library is the
  only shared prior, and it is hand-written.
- **No content understanding.** Learning is keyed on task TYPE, not on what a task is about. Two
  "write the report" tasks for different reports are indistinguishable.
- **Historical rows carry no timezone.** Behavioural time-series rows are bucketed with the user's
  *current* timezone, so patterns re-bucket after a relocation (`known_issues.md`).
- **Swap learning is category-level.** It learns "you prefer errands to deep work in the morning",
  not "you prefer THIS errand".
- **No forgetting curve.** Windows are hard cutoffs (30 / 42 days) rather than a decay, so evidence
  from day 41 counts exactly as much as evidence from yesterday.

---

## 6. Where to look in the code

| Concern | File |
|---|---|
| Baseline library (types, durations, difficulty) | `app/services/task_library.py` |
| Duration learning | `app/repositories/task_duration_repository.py`, `app/services/task_duration_service.py` |
| Energy | `app/services/energy_service.py` |
| The four fits | `app/services/recommendation/scoring/fits.py` |
| Weights and penalties | `app/services/recommendation/scoring/score.py`, `.../penalties.py` |
| Feedback → scoring | `app/services/recommendation/feedback/build_summary.py`, `.../apply_feedback.py` |
| Adaptation rollup | `app/services/user_adaptation_service.py`, `app/workers/adaptation_tasks.py` |
| Local-day boundaries | `app/core/localtime.py` |
