# Subscription Billing Agent

## Purpose
Implement and maintain cross-platform subscription entitlement across Stripe (web), Apple StoreKit (iOS), and Google Play Billing (Android).

## Inputs
- Active Jira ticket
- Payment event or entitlement state to handle

## Outputs
- Stripe service in `backend/app/services/stripe_service.py`
- Apple billing service in `backend/app/services/apple_billing_service.py`
- Google billing service in `backend/app/services/google_billing_service.py`
- Unified entitlement service in `backend/app/services/entitlement_service.py`
- Webhook handlers in `backend/app/api/v1/webhooks/`
- StoreKit code in `ios/TimeSense/Services/SubscriptionService.swift`
- Google Play Billing code in `android/.../services/BillingService.kt`
- Tests for all state transitions

## Forbidden Actions
- Do not expose Stripe/Apple/Google credentials to client apps
- Do not skip idempotency checks on webhook handlers
- Do not apply referral rewards before referred user is a paying subscriber
- Do not let mobile apps be the final entitlement authority

## Required Tests
- Stripe webhook handling (use Stripe CLI test events)
- Apple notification handling
- Google notification handling
- Trial → active → canceled → expired state transitions
- Free Basic Mode activation
- Multi-source entitlement resolution

## Skill to Use
`.claude/skills/subscription-entitlements/SKILL.md`
