# Skill: Project Memory

## Purpose
Maintain persistent project memory so Claude can continue after context resets, session compaction, crashes, or branch changes. The repository is the source of truth — not chat history.

## When to Use
- At the start of every session
- At the end of every session
- After completing a Jira ticket
- After fixing a bug
- After making a product or technical decision
- After discovering a known issue
- When human input is required
- Before compacting context
- When switching implementation areas

## Required Inputs
- Current Jira ticket number
- What was just completed
- Any new decisions made
- Any problems discovered
- Any open questions needing human input

## Required Process

### Session Start
1. Read `docs/project_memory/context_summary.md`
2. Read `docs/project_memory/phase_status.md`
3. Read `docs/project_memory/implementation_log.md`
4. Read `docs/project_memory/decision_log.md`
5. Read `docs/project_memory/known_issues.md`
6. Read `docs/project_memory/open_questions.md`
7. Read `tickets/implementation_sequence.md`
8. Continue from documented next step

### Session End / After Each Ticket
1. Update `docs/project_memory/implementation_log.md` with what was done
2. Update `docs/project_memory/phase_status.md` acceptance criteria checkboxes
3. Update `docs/project_memory/change_summary.md`
4. Rewrite `docs/project_memory/context_summary.md` to reflect current state
5. Update `docs/project_memory/decision_log.md` if a decision was made
6. Update `docs/project_memory/known_issues.md` if a problem was found
7. Update `docs/project_memory/open_questions.md` if human input is needed
8. Update `CHANGELOG.md`

## Required Outputs
- All memory files current and accurate
- `context_summary.md` answers: what exists, what was done, what's next, what warnings exist

## Files to Read First
- `docs/project_memory/context_summary.md`
- `docs/project_memory/phase_status.md`

## Files to Update
- `docs/project_memory/implementation_log.md`
- `docs/project_memory/phase_status.md`
- `docs/project_memory/change_summary.md`
- `docs/project_memory/context_summary.md`
- `docs/project_memory/decision_log.md` (when decisions made)
- `docs/project_memory/known_issues.md` (when issues found)
- `docs/project_memory/open_questions.md` (when human input needed)
- `CHANGELOG.md`

## Commands / Checks
None specific — this skill is about file maintenance.

## Prohibited Actions
- Do not rely on chat history as the source of truth
- Do not let `context_summary.md` grow beyond ~100 lines without rewriting it
- Do not delete settled decisions from `decision_log.md`
- Do not compact context without first updating all memory files

## End-of-Task Requirements
Every session must end with all project memory files updated. If memory files are not updated, the session is not complete.
