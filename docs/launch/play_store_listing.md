# Play Store Listing — TimeSense (Android)

Application ID: `com.timesense.app`
Character limits are Google's; entries below are within them. Bracketed items need your input.

---

## Store listing

**App name (≤30):**
`TimeSense: Day Planner`

**Short description (≤80):**
`Plans your day around real life and tells you the one best thing to do next.`

**Full description (≤4000):**
```
Don't make managing your day another job.

TimeSense is a context-aware personal time assistant. Instead of another endless to-do list, it
looks at your real day — calendar, sleep, meals, commute, and routines — and tells you the single
best thing to do next in the time you actually have.

WHAT YOU GET
• Now: your best next action for the time and energy you have
• Today: a realistic view of your usable time
• Capture: type anything in plain language and TimeSense turns it into a task

PLANS AROUND YOUR REAL LIFE
• Learns your routines (sleep, meals, hygiene) and plans around them
• Reserves travel time from your commute (with your permission)

GENTLE, NOT NAGGING
• Choose a Calm, Friendly, or High-Performance coaching style
• Notifications that respect your mode

WORKS WITH YOUR TOOLS
• Connect Google Calendar, Slack, Microsoft Teams, or Notion
• Suggests tasks from them — nothing is added without your approval

HOME-SCREEN WIDGETS
• Usable time and your next action, at a glance

YOUR DATA, YOUR CALL
• Sensitive signals (location, calendar, analytics) are off until you turn them on
• Export or delete all your data anytime
• Integration tokens are encrypted

SUBSCRIPTION
• 14-day Premium trial (payment info required)
• $14.99/month or $99/year (Founder: $79/year)
• Free Basic Mode after the trial if you don't subscribe

Privacy Policy: [URL]
```

**App category:** Productivity
**Tags:** planner, productivity, tasks, schedule, focus
**Contact email:** [support@yourdomain]
**Privacy Policy URL:** [https://yourdomain/privacy]  ← host `docs/launch/privacy_policy.md`

**Content rating:** Everyone (complete Google's IARC questionnaire; no mature content)

---

## Data Safety form answers — Play Console

Overall: TimeSense **collects** the data below, **does not sell/share** it with third parties for
their own use (processors act on our behalf only), encrypts data **in transit** and encrypts
integration tokens **at rest**, and provides a way to **request deletion**.

| Data type | Collected | Shared | Purpose | Optional? |
|---|---|---|---|---|
| Email address | Yes | No | Account management, App functionality | Required |
| User IDs | Yes | No | App functionality | Required |
| Approximate/Precise location | Yes | No | App functionality (commute) | **Optional (consent)** |
| Health & fitness (sleep) | Yes | No | App functionality (planning) | **Optional (consent)** |
| Calendar events | Yes | No | App functionality (planning) | **Optional (consent)** |
| Messages (from connected Slack/Teams) | Yes | No | App functionality (task suggestions) | **Optional (consent)** |
| Other user-generated content (tasks, notes, Notion pages) | Yes | No | App functionality | Required for the feature used |
| Purchase history | Yes | No | App functionality (subscription) | Required for purchases |
| App interactions / analytics | Yes | No | Analytics | **Optional (consent)** |
| Crash logs / diagnostics | Yes | No | App functionality (stability) | Required |
| Audio | Only if user opts in | No | App functionality | **Optional (opt-in)** |

**Security practices to check:**
- ☑ Data is encrypted in transit
- ☑ Integration tokens encrypted at rest
- ☑ Users can request that their data be deleted (in-app: Settings → Delete My Data)
- ☑ You have a way for users to request data export

**Third-party processors:** Firebase (auth), OpenAI (LLM processing of captured text), Stripe /
Google Play (payments), and the integrations the user connects (Google/Slack/Microsoft/Notion).

---

## Pre-launch notes
- Declare Health/sleep and location usage in-console and ensure the runtime permission prompts match
  the declared purposes.
- If targeting families, complete the additional Play policy requirements (not currently targeted).
- Provide a demo/test account for review, same as the App Store notes.
