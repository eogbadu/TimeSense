# App Store Listing — TimeSense (iOS)

Bundle ID: `com.aetheranalytics.timesense` · Team: `WB5NV894N5`
Character limits are Apple's; entries below are within them. Bracketed items need your input.

---

## Metadata

**App Name (≤30):**
`TimeSense: Day Planner`

**Subtitle (≤30):**
`Not another to-do app`

**Promotional Text (≤170, editable anytime):**
`Your day, planned around real life — sleep, meals, commute, and calendar. TimeSense tells you the
one best thing to do next, so managing your day never becomes another job.`

**Keywords (≤100, comma-separated, no spaces):**
`planner,time,schedule,focus,productivity,tasks,calendar,routine,assistant,day,ai,plan,todo,habits`

**Description (≤4000):**
```
Don't make managing your day another job.

TimeSense is a context-aware personal time assistant. Instead of another endless to-do list, it
looks at your real day — your calendar, sleep, meals, commute, and routines — and tells you the one
best thing to do next in the time you actually have.

NOW, TODAY, CAPTURE
• Now: the single best next action for the time and energy you have
• Today: a realistic view of your usable time
• Capture: jot anything in plain language; TimeSense turns it into a task

PLANS AROUND YOUR REAL LIFE
• Learns your routines (sleep, meals, hygiene) and plans around them
• Reads recent sleep from Apple Health to suggest a better morning (with your permission)
• Reserves travel time from your commute (with your permission)

GENTLE, NOT NAGGING
• Choose your assistant's style: Calm, Friendly Companion, or High-Performance Coach
• Notifications that respect your mode — never a firehose

WORKS WITH YOUR TOOLS
• Connect Google Calendar, Slack, Microsoft Teams, or Notion
• TimeSense suggests tasks from them — nothing is added without your approval

SIRI & WIDGETS
• "What should I do next?", "Log lunch", "Mark done" via Siri Shortcuts
• Home-screen widgets for usable time and your next action

YOUR DATA, YOUR CALL
• Sensitive signals (health, location, calendar, analytics) are off until you turn them on
• Export or delete all your data anytime
• Integration tokens are encrypted

SUBSCRIPTION
• 14-day Premium trial (payment info required)
• $14.99/month or $99/year (Founder: $79/year)
• Free Basic Mode after the trial if you don't subscribe

Privacy Policy: [URL]   Terms of Use: [URL]
```

**What's New (version notes, ≤4000):**
`First release. Now/Today/Capture, routine-aware planning, Apple Health sleep sync, calendar/Slack/
Teams/Notion suggestions, Siri Shortcuts, widgets, and full data export/delete.`

**Support URL:** [https://yourdomain/support]
**Marketing URL (optional):** [https://yourdomain]
**Privacy Policy URL:** [https://yourdomain/privacy]  ← host `docs/launch/privacy_policy.md`

**Primary Category:** Productivity  ·  **Secondary:** Lifestyle
**Age Rating:** 4+ (no objectionable content)

---

## App Review Notes (paste into "Notes for Reviewer")

```
Sign-in: TimeSense uses Firebase Authentication (email/password + Sign in with Apple).
Demo account: [email] / [password]   (please create one before submission)

Getting to core features:
1. Sign in with the demo account.
2. The Now / Today / Capture / Insights / Settings tabs are along the bottom.
3. Capture: type any task in plain language; it is parsed into a structured task.

Permissions (all optional and off by default):
- Apple Health (sleep, read-only): Settings → Connect Apple Health. Reads recent sleep to suggest a
  morning plan. We never write to Health.
- Location: used only for commute detection if enabled.
- Notifications: gentle daily check-ins.

Subscription: a 14-day Premium trial (StoreKit). Basic Mode remains free after the trial. Use the
sandbox tester [email] to exercise purchase flows.

Integrations (Calendar/Slack/Teams/Notion) require the user's own third-party account; detected
items become tasks only after explicit in-app confirmation.

Data rights: Settings exposes full data Export and Delete My Data.
```

---

## App Privacy ("nutrition label") answers — App Store Connect

For each type: whether collected, linked to identity, used for tracking, and purpose. TimeSense does
**no** cross-app tracking and does **not** use data for third-party advertising.

| Data type | Collected? | Linked to user? | Tracking? | Purpose |
|---|---|---|---|---|
| Email address | Yes | Yes | No | App functionality, account |
| User ID | Yes | Yes | No | App functionality |
| Health & Fitness (sleep) | Yes (opt-in) | Yes | No | App functionality (morning planning) |
| Precise/Coarse Location | Yes (opt-in) | Yes | No | App functionality (commute) |
| Calendar events | Yes (opt-in) | Yes | No | App functionality (planning) |
| User content (tasks/notes) | Yes | Yes | No | App functionality |
| Other user content (messages from connected Slack/Teams/Notion) | Yes (opt-in) | Yes | No | App functionality (task suggestions) |
| Purchase history | Yes | Yes | No | App functionality (subscription) |
| Product interaction / analytics | Yes (opt-in) | Yes | No | Analytics, product improvement |
| Crash / diagnostics | Yes | No | No | App functionality (stability) |
| Audio data | Only if user opts in | Yes | No | App functionality |

**Third-party processors to disclose:** Firebase (auth), OpenAI (LLM processing of captured text),
Stripe/Apple (payments), and the integrations the user connects.

**Data deletion:** In-app account deletion is available (App Store requires this for apps with
account creation) — Settings → Delete My Data.
