# Skill: Subscription Entitlements

## Purpose
Implement and maintain cross-platform subscription entitlement behavior across Stripe (web), Apple StoreKit (iOS), and Google Play Billing (Android). Maintain one unified backend entitlement system.

## When to Use
- Setting up Stripe products/prices for web
- Implementing Stripe checkout or customer portal
- Implementing Stripe webhook handlers
- Setting up Apple In-App Purchase / StoreKit on iOS
- Processing Apple App Store Server Notifications
- Setting up Google Play Billing on Android
- Processing Google Play Real-Time Developer Notifications
- Implementing trial logic
- Implementing Free Basic Mode
- Implementing premium feature gating
- Implementing referral rewards
- Building subscription admin views

## Payment Source Architecture

```
Stripe (web) ──────────────────────────────────────┐
Apple StoreKit (iOS) ──────────────────────────────┤──▶ Backend Entitlement System
Google Play Billing (Android) ─────────────────────┘
```

The backend is the authoritative source for whether a user has Premium access. Mobile apps may cache entitlement but must verify with backend.

## Key Rules

### Trial
- 14-day Premium trial
- Payment information required before trial starts
- Trial state: `trialing`
- After trial without subscription: downgrade to Free Basic Mode

### Pricing
- Monthly: $14.99/month
- Annual: $99/year
- Founder/Early Adopter: $79/year

### Entitlement States
- `trialing` — in free trial
- `active` — paid and current
- `grace_period` — payment failed, grace period active
- `canceled` — canceled but access until period end
- `expired` — no longer has Premium
- `refunded` — payment reversed

### Multi-Source Rule
- If any source grants active Premium, user has Premium
- Track all sources independently in `payment_sources` table
- Resolve effective entitlement from most favorable valid state

### Free Basic Mode
- Activates when no source grants Premium
- Pause premium background syncs
- Lock premium features (unlimited recommendations, learning mode, health/sleep intelligence, etc.)
- Keep integration connection tokens where secure/allowed
- Resume premium immediately when any source grants Premium again

### Referral
- Give 1 month free, get 1 month free
- Reward activates only when referred user becomes a paying subscriber
- No double-reward across multiple payment sources

## Webhook / Notification Handlers

All webhook and notification handlers must be:
- **Idempotent** — check for duplicate event_id before processing
- **Logged** — store raw event in `subscription_events` table
- **Secure** — verify signatures (Stripe: `Stripe-Signature` header; Apple: signed JWS; Google: Pub/Sub push with OIDC token)

## Files to Read First
- `docs/architecture/architecture_overview.md` → Subscription section
- `backend/app/models/subscription.py`
- `backend/app/services/entitlement_service.py`

## Files to Update
- `backend/app/models/subscription.py`
- `backend/app/services/stripe_service.py`
- `backend/app/services/apple_billing_service.py`
- `backend/app/services/google_billing_service.py`
- `backend/app/services/entitlement_service.py`
- `backend/app/api/v1/subscriptions.py`
- `backend/app/api/v1/webhooks/`
- `backend/tests/test_subscription_*.py`

## Commands / Checks
```bash
# Test subscription logic
pytest backend/tests/test_stripe.py -v
pytest backend/tests/test_apple_billing.py -v
pytest backend/tests/test_google_billing.py -v
pytest backend/tests/test_trial_entitlement.py -v
pytest backend/tests/test_referral.py -v

# Test Stripe webhooks locally
stripe listen --forward-to localhost:8000/stripe/webhooks
```

## Prohibited Actions
- Do not let mobile apps be the final authority on entitlement
- Do not skip idempotency checks on webhook handlers
- Do not expose Stripe secret keys or Apple/Google credentials to client apps
- Do not apply referral rewards before referred user becomes a paying subscriber
- Do not grant Premium access without a verified payment source

## End-of-Task Requirements
- Webhook handlers are idempotent and tested
- Entitlement resolves correctly across all state transitions
- Free Basic Mode activates on expiry
- Premium syncs pause/resume correctly
- Admin can view entitlement state
