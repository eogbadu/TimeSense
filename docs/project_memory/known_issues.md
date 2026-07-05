# Known Issues

## Issue: test_referrals.py intermittently fails on real Stripe network calls
- Date: 2026-07-05
- Area: `backend/tests/test_referrals.py` (`test_conversion_extends_subscriptions`, `test_no_double_conversion`)
- Symptom: These two tests occasionally fail with `stripe._error.APIConnectionError: ... No route to host` for `api.stripe.com`, then pass moments later on an identical rerun with no code changes.
- Root cause: These tests call through to the real Stripe SDK instead of mocking it, so they depend on outbound network access to `api.stripe.com` actually being available from wherever the suite runs. This sandbox environment's network access appears intermittent/restricted (unlike the `.devcontainer/` firewall setup documented below, which explicitly allowlists `api.stripe.com`).
- Fix: None applied — out of scope for TIME-040. If seen again, rerun the suite before assuming a regression; a real fix would mock the Stripe client in these two tests like the rest of `test_subscriptions.py` already does.
- Files changed: None.
- Verification: Reran `pytest tests/test_referrals.py` — failed once, passed immediately after with no changes.
- Follow-up needed: Mock Stripe calls in `test_conversion_extends_subscriptions`/`test_no_double_conversion` so the suite doesn't depend on network access.

## Issue: Alembic accumulated 4 divergent migration heads (TIME-030/033/036 era)
- Date: 2026-07-04
- Area: `backend/migrations/versions/`
- Symptom: Discovered while adding the TIME-038 `recommendation_feedback` migration — `alembic heads` showed 4 heads (`a1b2c3d4e5f7` tasks/reminders, `a7b8c9d0e1f2` referrals, `b8c9d0e1f2a3` waitlist/invite, plus the new one), all branching from the same parent `f6a7b8c9d0e1`. `alembic upgrade head` would have failed with "Multiple head revisions are present" — the standard `alembic upgrade head` command in CLAUDE.md was broken and had been broken since at least the referral/waitlist tickets, undetected because tests use in-memory SQLite with `Base.metadata.create_all` and never actually run the Alembic chain.
- Root cause: Several feature branches each wrote a migration with `down_revision = "f6a7b8c9d0e1"` without checking whether a sibling branch had already claimed that as its parent, and none of the merges added a merge migration afterward.
- Fix: Ran `alembic merge heads` to generate `e55970716568_merge_parallel_migration_heads.py`, a no-op migration whose `down_revision` is the tuple of all 4 heads. `alembic heads` now shows a single head.
- Files changed: `backend/migrations/versions/e55970716568_merge_parallel_migration_heads.py` (new)
- Verification: `alembic heads` → single head; `alembic upgrade head --sql` compiles the full chain cleanly in offline mode. Could not run a real `alembic upgrade head` against Postgres — no Docker/Postgres available in this session's environment.
- Follow-up needed: Verify `alembic upgrade head` against a real Postgres instance before this branch is deployed. Going forward, anyone adding a migration should run `alembic heads` first and rebase `down_revision` onto the current head rather than an old parent.

## Issue: `gh` CLI not authenticated in this environment — RESOLVED 2026-07-04
- Date: 2026-07-04
- Area: Session/environment setup, blocks the GitHub half of the required Jira/GitHub ticket workflow
- Symptom: `gh auth status` reports not logged into any GitHub hosts, so `gh pr create` cannot run. (Note: `git push` itself worked before this fix via a separate VS Code remote-container credential helper — only the `gh` CLI specifically was unauthenticated.)
- Root cause: This devcontainer/session was never authenticated against GitHub (`gh auth login` not run).
- Fix: User ran `gh auth login` (device code flow) mid-session; `gh auth status` now shows logged in as `eogbadu` with `repo` scope. PR #29 (TIME-038) was created successfully afterward.
- Files changed: None (auth is stored in `~/.config/gh/hosts.yml`, not in the repo).
- Verification: `gh auth status` → logged in; `gh pr create` succeeded for PR #29.
- Follow-up needed: None — resolved for this environment's lifetime. A fresh container/session would need `gh auth login` run again.

## Issue: RoutineAssumption data (TIME-039) is not yet subtracted from usable time
- Date: 2026-07-05
- Area: `backend/app/services/usable_time_service.py`
- Symptom: TIME-039 added a `routine_assumptions` table and API (sleep/meal/hygiene blocks), but `UsableTimeService.calculate()` still only looks at scheduled `Task` blocks — it has no awareness of routines yet, and recommendations can still be generated for e.g. 2am if a user has pending tasks.
- Root cause: `UsableTimeService.calculate()` computes its end-of-day cap from UTC midnight and has never taken a user timezone parameter, despite TIME-034's original ticket scope saying it should. Converting routine minute-of-day values (which are local-time) into UTC blocks correctly requires that timezone awareness to exist first — bolting it on per-signal (routines now, then meals, then commute) would mean rewriting the same timezone logic three times.
- Fix: Not applied — deliberately deferred (see TIME-039 ticket Non-Goals). Was correct to store the model/API now since meal/commute/sleep tickets (TIME-040–042) need it to exist, but the actual usable-time integration should happen once all Phase 9 signals exist, in one pass, alongside adding proper timezone handling to `UsableTimeService`.
- Files changed: None yet.
- Verification: N/A.
- Follow-up needed: Add a `user_timezone: str` param to `UsableTimeService.calculate()`, convert routine/meal/commute blocks to UTC via `zoneinfo`, and subtract them from the usable window — planned for a ticket after TIME-042 (Sleep/Wake Signal Integration) completes Phase 9's data model, per the recommendation-engine skill's "Empty calendar time ≠ available time" principle.

## Issue: Devcontainer firewall script breaks Docker Desktop for Mac embedded DNS
- Date: 2026-07-04
- Area: `.devcontainer/` (yolo-mode sandbox for `claude --dangerously-skip-permissions`)
- Symptom: `postStartCommand` (the egress-firewall init script) failed with `curl: (6) Could not resolve host` immediately when fetching GitHub's IP ranges, on a freshly created container.
- Root cause: Two distinct bugs stacked on top of each other. (1) The upstream `anthropics/claude-code` reference `init-firewall.sh` flushes the `nat` table (`iptables -t nat -F`) to selectively preserve Docker's embedded-DNS NAT rules; on Docker Desktop for Mac those rules don't textually contain `127.0.0.11` the way they do on Linux Docker Engine, so the grep-and-replay restore silently loses them and DNS breaks permanently for that container. (2) The `ghcr.io/anthropics/devcontainer-features/claude-code` devcontainer feature installs its own bundled copy of `init-firewall.sh` at `/usr/local/bin/init-firewall.sh` during the features build stage, which runs *after* our own Dockerfile's `COPY` — so a same-named custom script gets silently clobbered by the unmodified upstream one, no matter how the Dockerfile/image caching is handled.
- Fix: Our script only touches the `filter` table (no nat/mangle flush at all — a pure egress allowlist doesn't need them). It's installed as `/usr/local/bin/timesense-init-firewall.sh` (distinct name) to avoid the feature's install-time collision. Also added `-exist` to `ipset add` calls since two allowlisted domains can resolve to the same IP.
- Files changed: `.devcontainer/init-firewall.sh`, `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`
- Verification: `npx @devcontainers/cli up --workspace-folder .` then confirmed inside the container: DNS resolves, `https://example.com` is blocked, `https://api.github.com/zen` and `https://api.stripe.com` succeed, `claude --version` works, Postgres/Redis reachable.
- Follow-up needed: None currently. If the `claude-code` feature is ever bumped or the Dockerfile base image changes, re-verify the firewall still runs cleanly (rebuild with `docker compose -p timesense_devcontainer -f .devcontainer/docker-compose.yml build --no-cache devcontainer`).

## Format

```
## Issue: [short title]
- Date: 
- Area: 
- Symptom: 
- Root cause: 
- Fix: 
- Files changed: 
- Verification: 
- Follow-up needed: 
```
