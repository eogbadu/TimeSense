# TimeSense Product Brief

## Product Name
TimeSense

## Core Tagline
**Don't make managing your day another job.**

## Product Vision
TimeSense is a mobile-first, context-aware personal time assistant that helps users manage their real day, not their ideal calendar.

It learns how a person actually lives — moves, works, rests, eats, commutes, prepares, delays, and completes things — then uses that context to recommend what the user should do next, without forcing them to maintain another productivity system.

## Primary Product Rule
> **Do not make managing your day another job.**

Every feature must pass this test. If a feature requires the user to constantly maintain, drag, categorize, sort, tag, organize, or update things manually — remove it, simplify it, or hide it behind automation.

## Core Product Principle
**Empty time is not the same as available time.**

A calendar may show a 45-minute gap, but the user may need to eat, commute, prepare for a meeting, rest, or reset. TimeSense calculates realistic usable time — not just open calendar blocks.

## Primary Product
TimeSense is primarily a **native mobile application**.

- iOS: Native Swift / SwiftUI
- Android: Native Kotlin / Jetpack Compose

## Secondary Product
A companion web app (same backend/database) for:
- Account setup / login
- Subscription management
- Integration management
- Privacy / settings
- Deeper insights
- Admin dashboard

Mobile remains the primary daily-use interface.

---

## Launch Platforms
- iOS (primary)
- Android (primary)
- Web companion (secondary)

## Core Launch Scope
- Now screen (current context + usable time + best next action)
- Today screen (realistic vertical timeline)
- Capture (voice + text)
- Insights (weekly learning summaries)
- Settings (integrations, permissions, learned assumptions)
- Onboarding with Learning Mode
- Subscription/trial (14-day Premium trial, payment info required)
- Admin dashboard
- Waitlist / invite codes / referral system

## Launch Non-Goals
- Projects / milestones
- File / document upload
- Drag-and-drop schedule editor
- Full nutrition / macros tracking
- Family / shared household mode
- Full alarm clock replacement
- Social features / public profiles
- Enterprise / team product
- Notion replacement
- Calendar replacement
- Full smart home automation
- Tiny robot / desk device
- Gmail / Apple Mail (unless easy)

---

## Tech Stack
- Backend: FastAPI, PostgreSQL, Redis/Celery, Firebase Auth
- Payments: Stripe (web), Apple StoreKit (iOS), Google Play Billing (Android), unified backend entitlement
- LLM: Provider-agnostic abstraction, OpenAI default
- iOS: Swift / SwiftUI
- Android: Kotlin / Jetpack Compose
- Web: React or Next.js

## Subscription Model
- 14-day Premium trial (payment info required)
- Monthly: $14.99/month
- Annual: $99/year
- Founder/Early Adopter: $79/year
- Free Basic Mode after trial if unsubscribed

## Key UX Principles
1. Cards, buttons, quick taps — not chat-first
2. Recommendations are hidden; explanations shown only when user taps "Why this?"
3. Replans always require approval
4. No nagging; ignored suggestions are learned from silently
5. No guilt-driven copy
6. Assistant personality: Calm Premium (default), Friendly Companion, or High-Performance Coach

---

## Non-Negotiable Product Rules (preserve across all context resets)
- Product name: TimeSense
- Tagline: "Don't make managing your day another job."
- Native mobile apps: Swift/SwiftUI (iOS) + Kotlin/Jetpack Compose (Android)
- Web app is companion only
- Backend: FastAPI + PostgreSQL + Firebase Auth + Stripe + LLM abstraction + Redis/Celery
- Mobile bottom tabs: Now, Today, Capture, Insights, Settings
- No Projects at launch
- Goals included as simple list
- No file/document upload at launch
- Calendar changes require approval
- Replans require approval
- No drag/reorder schedule editor
- First few weeks: Active Coach / Learning Mode
- Learning period ends based on data, not fixed days
- Trial: 14 days, requires payment info
- Pricing: $14.99/month · $99/year · $79/year founder
- Free Basic Mode after trial
- Pause premium syncs in Free Basic Mode but keep connections where secure/allowed
- Waitlist, invite codes, referral system, and admin dashboard at launch
- Raw audio storage and training use require explicit opt-in
- Individual user first; no family/shared mode at launch
- Meal tracking: lightweight only
- Hygiene: grouped into simple routine blocks
- TimeSense learns habits over time; does not force work/personal modes
- The product must never become another job to manage
