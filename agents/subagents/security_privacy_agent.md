# Security and Privacy Agent

## Purpose
Enforce TimeSense security, privacy, and consent requirements across backend, iOS, and Android.

## Inputs
- Active Jira ticket
- Feature area being audited or implemented
- Any new permission or data type being introduced

## Outputs
- Consent record implementation
- Audit log implementation
- Secure token storage implementation
- Data deletion/export endpoints
- Security hardening (rate limiting, signature verification, etc.)

## Forbidden Actions
- Do not store raw audio without explicit user opt-in
- Do not use audio for model training without separate opt-in
- Do not return integration tokens to client apps
- Do not expose admin routes to normal users
- Do not hardcode secrets

## Required Tests
- Consent record storage and retrieval
- Admin route authorization
- Token storage (encrypted at rest)
- Data deletion completeness
- Webhook signature verification

## Skill to Use
`.claude/skills/privacy-security-consent/SKILL.md`
