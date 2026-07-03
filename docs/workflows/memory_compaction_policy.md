# Memory Compaction Policy

## When to Compact

Compact context when:
- The active session is becoming very long and approaching context limits
- Switching to a significantly different implementation area
- Starting a new session after a crash or restart
- Completing a major phase (update all memory files, then clear chat)

Do NOT compact mid-task. Always finish or reach a clean checkpoint first.

---

## Before Compacting — Required Steps

Complete all of these before clearing or compacting context:

1. Finish current task or stop at a clean checkpoint
2. Update `docs/project_memory/implementation_log.md` with what was completed
3. Update `docs/project_memory/phase_status.md` with acceptance criteria progress
4. Update `docs/project_memory/change_summary.md`
5. Update `docs/project_memory/context_summary.md` with current state and exact next step
6. Update `docs/project_memory/decision_log.md` if any new decision was made
7. Update `docs/project_memory/known_issues.md` if any problem was discovered
8. Update `docs/project_memory/open_questions.md` if any question needs human input
9. Update `CHANGELOG.md`
10. Confirm `NEXT_STEPS.md` or `context_summary.md` has the exact next task

---

## What to Preserve in context_summary.md

The `context_summary.md` file must always answer:
- What currently exists and works?
- What was just completed?
- What is the current active task?
- What is the next recommended task?
- What decisions must not be revisited?
- What problems exist right now?
- What files were recently changed?
- Any warnings for the next agent session?

Keep this file **short** (under 100 lines). Move detail to implementation_log.md.

---

## After Compaction — Session Start Procedure

Read in this order before writing any code:

1. `docs/project_memory/context_summary.md`
2. `docs/project_memory/phase_status.md`
3. `docs/project_memory/implementation_log.md`
4. `docs/project_memory/decision_log.md`
5. `docs/project_memory/known_issues.md`
6. `docs/project_memory/open_questions.md`
7. `tickets/implementation_sequence.md`
8. `AGENTS.md`
9. `CLAUDE.md`
10. The relevant feature/area notes file for the active ticket

Then continue from the documented next step.

---

## Avoiding Repeated Failures

Before attempting a fix that was tried before:
- Check `docs/project_memory/known_issues.md`
- If a fix is listed with a "Failed" note, do not repeat it
- If a workaround is listed, use it

---

## Memory File Size Policy

- `context_summary.md` — max ~100 lines; rewrite rather than append
- `implementation_log.md` — append; archive old entries to `implementation_log_archive.md` if it exceeds 300 lines
- `decision_log.md` — append only; never delete settled decisions
- `known_issues.md` — append; mark resolved issues as `[RESOLVED]` rather than deleting
- `change_summary.md` — keep last 10 changes; archive older ones
- `open_questions.md` — mark answered questions as `[ANSWERED]` and keep for reference

---

## Repository is the Source of Truth

Chat history is ephemeral. The repository is permanent.

Every important fact — product decisions, technical decisions, integration limitations, bugs, fixes, files changed, commands run, tests run, next steps, deferred features, user approvals, known risks — must be stored in the appropriate project memory file.

Never rely on chat history alone.
