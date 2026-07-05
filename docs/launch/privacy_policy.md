# TimeSense Privacy Policy

**Last updated: July 5, 2026**

TimeSense ("TimeSense," "we," "us") is a context-aware personal time assistant. This policy explains
what we collect, why, how it's protected, and the choices and rights you have. Our guiding principle
— *"Don't make managing your day another job"* — extends to your data: we collect only what makes
the assistant useful, gate sensitive signals behind explicit consent, and let you export or delete
everything at any time.

> **Draft note (remove before publishing):** This is an accurate draft grounded in TimeSense's
> implementation. Have it reviewed by legal counsel and fill in the bracketed company/contact
> details before publishing.

---

## 1. Who we are

- Provider: [Aether Analytics / legal entity name]
- Contact: [privacy@yourdomain] · [postal address]
- Data Protection Contact: [name/email]

## 2. The data we collect

### 2.1 Account & authentication
Authentication is handled by **Google Firebase Authentication**. When you sign in we receive your
account identifier (UID), email address, and email-verification status. We store your email and a
role flag. We never receive or store your Google/Apple password.

### 2.2 Content you create
- **Tasks** you capture (typed text; the assistant may parse it into a title, estimate, and due
  date).
- **Meals, sleep/wake times, commute events, and daily routines** you log or that are inferred to
  build your schedule.
- **Preferences** (assistant personality, notification mode, learned assumptions).

### 2.3 Sensitive signals — collected only with your explicit consent
Each of the following is gated behind a separate, revocable consent and is off by default:

| Consent | What it enables |
|---|---|
| `health_data` | Reading recent **sleep** data from Apple Health (HealthKit) to suggest a better morning plan. Read-only; we never write to Health. |
| `location_tracking` | **Commute detection** from device location to reserve travel time. |
| `calendar_details` | Reading calendar event details to plan around them. |
| `analytics` | Anonymous product-usage analytics (see §2.6). |
| `audio_storage` | Storing raw audio you record (off unless you opt in). |
| `audio_training` | Using your audio to improve models (off unless you opt in). |

### 2.4 Connected integrations
If you connect **Google Calendar, Slack, Microsoft Teams, or Notion**, we store an OAuth access
token to read the data you authorize (calendar events; recent messages for action-item suggestions;
Notion database pages). **These tokens are encrypted at rest.** We never post or write back to these
services without your explicit approval, and detected action items become tasks only after you
confirm them.

### 2.5 Payment data
Subscriptions are processed by **Stripe** (web), **Apple StoreKit** (iOS), and **Google Play
Billing** (Android). We receive subscription status and identifiers from these processors; we do
**not** receive or store your full card number.

### 2.6 Analytics & diagnostics
- **Product analytics** (e.g., "task captured") are recorded **only if you grant the `analytics`
  consent**, and contain product signals — not the content of your tasks or messages.
- **Crash/error diagnostics** may be collected to keep the service reliable.

### 2.7 AI processing
To turn what you capture into structured tasks and recommendations, the **text you capture and
relevant schedule context** are sent to our large-language-model provider (**OpenAI by default**)
for processing. This is used to provide the feature, not to train third-party models. We do not send
your raw audio or connected-service content to the LLM except as needed to deliver a feature you
invoked.

## 3. How we use your data
- Provide the core assistant: plan your day, recommend a next action, send timely nudges.
- Learn your routines to make better suggestions.
- Process payments and manage your subscription/trial.
- Maintain security, prevent abuse, and debug problems.
- With your consent, measure product usage to improve TimeSense.

We do **not** sell your personal data, and we do not use your content for advertising.

## 4. Legal bases (EEA/UK)
Performance of our contract (providing the assistant), your consent (sensitive signals, analytics,
integrations), our legitimate interests (security, reliability), and legal obligations.

## 5. Sharing
We share data only with service providers acting on our behalf: Firebase (auth), our cloud hosting/
database, Stripe/Apple/Google (payments), OpenAI (LLM processing), and — only for the integrations
you connect — Google/Slack/Microsoft/Notion. We may disclose data if required by law.

## 6. Security
- Integration OAuth tokens are **encrypted at rest**.
- Traffic is encrypted in transit (TLS).
- Access to sensitive actions is authenticated; account-deletion and other sensitive endpoints are
  rate-limited; standard response security headers are applied.
- No method is perfectly secure, but we take reasonable measures to protect your data.

## 7. Data retention
We keep your data while your account is active. When you delete your account (see §8) we erase your
personal data promptly. Aggregate, de-identified analytics may be retained.

## 8. Your rights and choices
- **Export:** download a portable copy of all your data (Settings → Export, or `GET /privacy/export`).
- **Delete:** permanently delete your account and all associated data (Settings → Delete My Data, or
  `DELETE /privacy/account`). This is irreversible and also removes your authentication record.
- **Revoke consent:** turn off any consent (health, location, calendar, analytics, audio) at any
  time in Settings.
- **Disconnect integrations:** remove a connected service; we delete its stored token.
- Depending on your region you may also have rights to access, correct, restrict, or object; contact
  us to exercise them.

## 9. Raw audio
Raw audio recording, storage, and any training use are **off by default** and require your explicit,
separate opt-in. You can withdraw at any time.

## 10. Children
TimeSense is not directed to children under 13 (or the minimum age in your region). We do not
knowingly collect data from children.

## 11. International transfers
Your data may be processed in countries other than yours; we use appropriate safeguards for such
transfers.

## 12. Changes
We'll update this policy as the product evolves and revise the "Last updated" date; material changes
will be communicated in-app.

## 13. Contact
[privacy@yourdomain] · [postal address]
