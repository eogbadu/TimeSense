# Skill: Recommendation Engine

## Purpose
Build and maintain the core "What should I do next?" intelligence. The engine must distinguish empty time from usable time and recommend the right action at the right moment.

## When to Use
- Implementing usable time calculation
- Implementing focus window detection
- Implementing task scoring
- Implementing prep/transition time estimates
- Adding meal/routine/commute signals to recommendations
- Implementing energy-level matching
- Implementing replan suggestions
- Implementing the "Why this?" explanation
- Implementing feedback learning
- Implementing weekly insight generation

## Core Principle
**Empty calendar time ≠ available time.**

A 45-minute gap may include:
- Lunch (20 min)
- Meeting prep (10 min)
- Transition (5 min)
= Only ~10 minutes actually usable

The engine must calculate **usable time**, not just open calendar gaps.

## Recommendation Format (always)

```
1. Best recommendation
2. Reason summary (1–2 sentences)
3. "Why this?" — hidden by default, expandable
4. Two optional alternatives
5. Actions: Approve / Done / Snooze / Not Now / Replan / Ask TimeSense / Bad Suggestion
```

## Engine Architecture

```
Input signals:
  - Current time
  - Calendar events (next 3–6h)
  - Routine assumptions
  - Meal status (eaten / skipped / eating-while-working)
  - Commute risk
  - Location context
  - Sleep/wake data
  - Goals + deadlines
  - Energy level (from check-in or inferred)
  - Captured tasks with priority
  - User behavior history
  - Ignored suggestions
  - Feedback signals

Step 1: Calculate usable time windows
  - Strip calendar events
  - Strip routine blocks (meals, commute, hygiene, prep)
  - Apply prep/transition buffers around events
  - Classify remaining windows by type (deep work, light admin, recovery, etc.)

Step 2: Score task candidates
  Score = f(priority, deadline_urgency, fit_with_usable_time, energy_match,
             focus_window_type_match, goal_relevance, calendar_risk,
             commute_risk, meal_sleep_context, behavior_history, task_switching_cost)

Step 3: Select top candidate + 2 alternatives

Step 4: Generate LLM explanation
  - Call LLMGateway with context + top candidate
  - Generate natural-language "Best next action" and "Why this?" text
  - Keep it calm, useful, direct — not guilt-driven

Step 5: Return recommendation to API
```

## Focus Window Types

- Deep Work
- Light Admin
- Recovery
- Errands
- Creative
- Workout
- Meal / Reset
- Prep / Review

Match task types to focus window types.

## Replan Suggestions

- Always require user approval
- Show one best replan first
- Offer two alternatives
- Explain why the replan helps
- If rejected or ignored, do not nag

## Feedback Learning

Feedback signals: Helpful / Not helpful / Wrong timing / Wrong context / Don't suggest this again / Bad suggestion

Use feedback to:
- Adjust task scores
- Update routine assumptions
- Flag problematic recommendation types
- Feed weekly insight generation

## Files to Read First
- `docs/architecture/architecture_overview.md` → Recommendation Data Flow section
- `backend/app/services/usable_time.py` (if exists)
- `backend/app/services/task_scorer.py` (if exists)
- `backend/app/llm/gateway.py` (if exists)

## Files to Update
- `backend/app/services/usable_time.py`
- `backend/app/services/focus_windows.py`
- `backend/app/services/task_scorer.py`
- `backend/app/services/recommendation_service.py`
- `backend/app/llm/gateway.py`
- `backend/tests/test_recommendation*.py`

## Commands / Checks
```bash
pytest backend/tests/test_usable_time.py -v
pytest backend/tests/test_task_scorer.py -v
pytest backend/tests/test_recommendation_service.py -v
```

## Prohibited Actions
- Do not use LLM as the sole decision mechanism — it provides the explanation, not the decision
- Do not nag after ignored suggestions
- Do not auto-apply replans — always require approval
- Do not show "Why this?" by default in UI — it must be hidden and revealed on tap
- Do not make recommendation logic tightly coupled to any specific LLM provider (use LLMGateway)

## End-of-Task Requirements
- Scoring logic is unit-tested
- Usable time calculation is unit-tested
- LLM explanation uses the gateway abstraction
- Ignored suggestions do not trigger follow-ups
- Replans require approval
- Project memory updated
