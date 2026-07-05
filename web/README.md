# TimeSense Web

The TimeSense web companion — currently just the admin dashboard (`app/admin/`). Not the
primary product; iOS/Android are. See the root `AGENTS.md`/`CLAUDE.md` for full project context.

## Getting Started

```bash
cp .env.local.example .env.local   # fill in Firebase config once a real project exists
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The admin dashboard is at `/admin`
(role-protected — the signed-in Firebase user must have `role: "admin"` on the backend).

## Structure

```
app/
  admin/
    layout.tsx        # auth + role gate, nav
    page.tsx           # metrics + integration status
    users/              # searchable user list
    invites/             # invite codes + waitlist
    subscriptions/        # subscription/trial status
    feedback/              # recommendation feedback review
lib/
  firebase.ts     # Firebase app + lazy Auth getter (no real project configured yet)
  auth.tsx         # auth context/hook
  api.ts            # fetch wrapper attaching the Firebase ID token
```

## Commands

```bash
npm run dev      # local dev server
npm run build    # production build (this is what CI/verification runs)
npm run lint     # ESLint
```
