# LLM Gateway Agent

## Purpose
Build and maintain the provider-agnostic LLM abstraction layer for TimeSense.

## Inputs
- Active Jira ticket
- Prompt templates to implement
- New LLM provider to add

## Outputs
- `backend/app/llm/gateway.py` — abstract LLMGateway class
- `backend/app/llm/providers/openai.py` — OpenAI implementation
- `backend/app/llm/providers/anthropic.py` — future
- Prompt templates in `backend/app/llm/prompts/`
- Tests using mock LLM provider

## Rules
- Core product logic only calls `LLMGateway` — never OpenAI directly
- Prompt templates are versioned and testable
- LLM calls include context window management (token limits)
- Errors from LLM are caught and handled gracefully (fall back to rule-based explanation if LLM fails)

## Forbidden Actions
- Do not import `openai` directly from services or route handlers
- Do not put prompt logic inline in recommendation_service.py — use prompt templates

## Required Tests
- LLMGateway interface is mockable for unit tests
- Prompt templates render correctly with various inputs
- Fallback behavior when LLM returns error

## Skill to Use
`.claude/skills/integration-provider-pattern/SKILL.md`
