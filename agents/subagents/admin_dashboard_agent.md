# Admin Dashboard Agent

## Purpose
Build and maintain the TimeSense admin web dashboard at `/admin`.

## Inputs
- Active Jira ticket
- Metrics or management features to implement

## Outputs
- Web admin pages in `web/app/admin/`
- Backend admin API endpoints in `backend/app/api/v1/admin.py`
- Admin audit log entries

## Required Features
- User search
- Invite code creation/disabling
- Waitlist review
- Subscription/trial status per user
- Referral tracking
- Integration connection/failure status
- Feedback review
- Error/log status
- Background job status
- Ability to disable problematic integration or notification types
- Metrics: active users, trial users, paid users, churn, referral conversions, notification engagement, recommendation acceptance rate

## Forbidden Actions
- Admin routes must be inaccessible to normal users
- Do not let admin pages reveal raw integration tokens or secrets
- All admin actions must be audit logged

## Required Tests
- Admin route rejects non-admin users (401/403)
- Admin audit log records all sensitive actions
- Metrics endpoints return correct counts

## Skill to Use
`.claude/skills/privacy-security-consent/SKILL.md`
