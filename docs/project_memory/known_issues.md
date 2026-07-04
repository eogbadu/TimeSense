# Known Issues

## Issue: Alembic accumulated 4 divergent migration heads (TIME-030/033/036 era)
- Date: 2026-07-04
- Area: `backend/migrations/versions/`
- Symptom: Discovered while adding the TIME-038 `recommendation_feedback` migration — `alembic heads` showed 4 heads (`a1b2c3d4e5f7` tasks/reminders, `a7b8c9d0e1f2` referrals, `b8c9d0e1f2a3` waitlist/invite, plus the new one), all branching from the same parent `f6a7b8c9d0e1`. `alembic upgrade head` would have failed with "Multiple head revisions are present" — the standard `alembic upgrade head` command in CLAUDE.md was broken and had been broken since at least the referral/waitlist tickets, undetected because tests use in-memory SQLite with `Base.metadata.create_all` and never actually run the Alembic chain.
- Root cause: Several feature branches each wrote a migration with `down_revision = "f6a7b8c9d0e1"` without checking whether a sibling branch had already claimed that as its parent, and none of the merges added a merge migration afterward.
- Fix: Ran `alembic merge heads` to generate `e55970716568_merge_parallel_migration_heads.py`, a no-op migration whose `down_revision` is the tuple of all 4 heads. `alembic heads` now shows a single head.
- Files changed: `backend/migrations/versions/e55970716568_merge_parallel_migration_heads.py` (new)
- Verification: `alembic heads` → single head; `alembic upgrade head --sql` compiles the full chain cleanly in offline mode. Could not run a real `alembic upgrade head` against Postgres — no Docker/Postgres available in this session's environment.
- Follow-up needed: Verify `alembic upgrade head` against a real Postgres instance before this branch is deployed. Going forward, anyone adding a migration should run `alembic heads` first and rebase `down_revision` onto the current head rather than an old parent.

## Issue: `gh` CLI not authenticated in this environment
- Date: 2026-07-04
- Area: Session/environment setup, blocks the GitHub half of the required Jira/GitHub ticket workflow
- Symptom: `gh auth status` reports not logged into any GitHub hosts, so `gh pr create` cannot run.
- Root cause: This devcontainer/session was never authenticated against GitHub (`gh auth login` not run).
- Fix: None applied — needs the user to authenticate (`gh auth login` or set `GH_TOKEN`) or push/PR manually.
- Files changed: None.
- Verification: N/A.
- Follow-up needed: Authenticate `gh` before the next ticket that needs a PR opened from this environment, or push manually and open the PR via the GitHub UI.

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
