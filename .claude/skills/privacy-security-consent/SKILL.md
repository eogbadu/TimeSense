# Skill: Privacy, Security, and Consent

## Purpose
Enforce TimeSense privacy, security, consent, and trust requirements. TimeSense works best with context, but the user stays in control.

## When to Use
- Adding any permission request (calendar, location, health, notifications, microphone)
- Storing or transmitting sensitive data
- Implementing voice or audio capture
- Implementing audio storage or model-improvement consent
- Implementing location signals
- Implementing health/wake signals
- Implementing admin-only access
- Implementing integration token storage
- Implementing data deletion or export
- Implementing audit logs
- Reviewing any feature that touches user data

## Core Privacy Principle
> TimeSense works best with context, but you stay in control.

Use this message throughout onboarding and settings.

## Permission Requirements

### Always required before requesting system permission:
1. Explain clearly WHY the permission helps
2. Show what TimeSense will do with it
3. Let users skip and add later
4. Respect permission denial — never force

### Calendar
Explain: "More calendar context helps TimeSense make better suggestions. Free/busy-only is also available if you prefer more privacy."

### Location
Explain: "Location helps detect commutes, errands, arrivals, and realistic transition times."

### Health / HealthKit
Explain: "Sleep and wake data helps TimeSense adjust your morning plan and understand your energy."

### Microphone / Audio
Explain: "Voice capture lets you quickly add thoughts to TimeSense hands-free."

### Audio Storage
Requires **separate explicit opt-in** (beyond just microphone permission):
- Store raw audio: explicit opt-in
- Use audio/transcripts for model improvement: separate, additional explicit opt-in
- Users can revoke audio consent and delete stored audio at any time

### Notifications
Explain: "Notifications help TimeSense check in during Learning Mode and suggest timely actions."

## Consent Records

Every consent decision must be stored in `consent_records`:
- `user_id`
- `consent_type` (audio_storage / model_training / location / health / calendar_details / etc.)
- `granted: bool`
- `granted_at`
- `revoked_at`
- `ip_address` (for legal compliance)

## Token Storage

Integration tokens (Google Calendar OAuth, Slack OAuth, etc.):
- Encrypted at rest in `integration_tokens` table
- Never returned to client apps
- Refreshed server-side
- Audit logged on first use and on revocation

## Admin Access

Admin routes:
- Protected by `require_admin` FastAPI dependency
- All admin actions logged to `admin_audit_logs`
- Normal users must never see or access admin routes
- Admin audit logs are append-only

## Security Requirements

- Firebase Auth JWTs verified server-side on every protected request
- Stripe webhook signature verified (`Stripe-Signature` header)
- Apple server notifications verified (signed JWS)
- Google Play notifications verified (OIDC token from Pub/Sub)
- Rate limiting on auth endpoints
- All secrets via environment variables — never hardcoded
- Sensitive data encrypted where feasible
- Audit logs for sensitive integration actions

## Data Deletion / Export

Users can:
- Delete their account and all stored data
- Export their data
- Revoke individual integration tokens
- Revoke audio consent and delete stored audio

Implement `DELETE /users/me` and `GET /users/me/export` with:
- All user data deleted or anonymized
- Integration tokens revoked and deleted
- Audio files deleted if revocated

## Files to Read First
- `backend/app/core/security.py`
- `backend/app/models/consent.py` (if exists)
- `backend/app/models/audit.py` (if exists)

## Files to Update
- `backend/app/models/consent.py`
- `backend/app/models/audit.py`
- `backend/app/api/v1/privacy.py`
- `backend/app/core/security.py`

## Commands / Checks
```bash
pytest backend/tests/test_auth.py -v
pytest backend/tests/test_consent.py -v
pytest backend/tests/test_admin_auth.py -v
pytest backend/tests/test_privacy.py -v
```

## Prohibited Actions
- Do not store raw audio without explicit opt-in
- Do not use audio for model training without a second explicit opt-in
- Do not return integration tokens to client apps
- Do not expose admin routes to normal users
- Do not skip audit logging for sensitive actions
- Do not write calendar events or enable DND without user approval
- Do not hardcode secrets

## End-of-Task Requirements
- Consent records stored for all permission decisions
- Sensitive data encrypted or on-device where feasible
- Admin routes protected and audit logged
- Data deletion/export path exists
- No secrets in code
