# Recommendation Engine Agent

## Purpose
Build and maintain the "What should I do next?" intelligence: usable time calculation, focus window detection, task scoring, LLM explanation, and feedback learning.

## Inputs
- Active Jira ticket
- Context signals available (calendar, routines, meals, energy, etc.)
- Scoring or weighting changes approved in decision log

## Outputs
- Usable time service in `backend/app/services/usable_time.py`
- Focus window service in `backend/app/services/focus_windows.py`
- Task scorer in `backend/app/services/task_scorer.py`
- Recommendation service in `backend/app/services/recommendation_service.py`
- LLM gateway in `backend/app/llm/`
- Tests with high coverage for scoring logic

## Forbidden Actions
- Do not use LLM as the sole decision mechanism
- Do not nag after ignored suggestions
- Do not auto-apply replans — approval required
- Do not expose "Why this?" by default in UI (that's a UI rule enforced in mobile code)
- Do not hardcode OpenAI directly in recommendation logic — use LLMGateway

## Required Tests
- Usable time calculation with various calendar/routine inputs
- Task scoring with edge cases (empty task list, all tasks snoozed, etc.)
- Recommendation service integration tests
- Feedback signal effects on scores

## Skill to Use
`.claude/skills/recommendation-engine/SKILL.md`
