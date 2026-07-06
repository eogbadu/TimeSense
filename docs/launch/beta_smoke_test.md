# TimeSense — Beta Smoke Test

Run this before every beta build to confirm the core loop works end-to-end. ~10 minutes.

## 0. Prep
- [ ] Backend running with LAN access: `cd backend && python run_dev.py`
- [ ] Automated smoke: `BASE=http://<your-mac>.local:8000 python scripts/smoke_test.py` → all PASS
- [ ] Full test suite green: `cd backend && pytest -q`
- [ ] iOS builds: `xcodebuild build -project ios/TimeSense.xcodeproj -scheme TimeSense -destination 'platform=iOS Simulator,name=iPhone 16'`
- [ ] Phone and Mac on the same Wi-Fi (for on-device runs)

## 1. Auth
- [ ] Fresh launch shows the sign-in screen (Apple / Google / Email)
- [ ] Sign in with email works; you land on **Now**
- [ ] Force-quit + relaunch stays signed in (no "session expired" dead-end)
- [ ] Settings ▸ **Sign Out** returns to sign-in

## 2. Capture → the brain
- [ ] Capture "Buy groceries today" → success confirmation
- [ ] Task gets a **duration estimate** (not blank)
- [ ] Task is **auto-scheduled** — appears on **Today** with a time + "Scheduled by TimeSense · Undo"
- [ ] **Undo** on Today makes it untimed again
- [ ] Capture "call the dentist tomorrow at 2pm" → parses a due time (LLM) or a sensible fallback

## 3. Now
- [ ] **Greeting** matches your local time of day
- [ ] Best task shows with priority + estimate; **"Or consider"** shows up to 2 alternatives
- [ ] **"Why this?"** expands and explains the pick (justifies it, doesn't suggest resting)
- [ ] **Done / Snooze / Not now** all work and change the best task
- [ ] Completing a task (while still learning) prompts **"How long did that take?"** chips
- [ ] "Usable minutes" looks right for your day (local midnight, not UTC)
- [ ] Late at night with nothing urgent → gentle **wind-down** card appears
- [ ] Feasibility: a task that can't fit before its due time shows a warning + next slot

## 4. Today
- [ ] Scheduled items appear in time order; untimed to-dos listed below
- [ ] Pull-to-refresh updates after a new capture

## 5. Settings
- [ ] Profile (email + editable name), Subscription (status), Notifications (mode), Appearance
      (light/dark applies instantly), **Working Hours** (edit + save), Privacy, About all open/work
- [ ] Delete My Data → confirm → account erased → returns to sign-in (use a throwaway account)

## 6. Web companion (optional)
- [ ] `cd web && npm run dev` → sign in as an admin → dashboard shows live data

## Sign-off
- [ ] No crashes, no dead-end errors, core loop (sign in → capture → Now → complete) feels smooth
- [ ] Build: __________  Date: __________  Tester: __________
