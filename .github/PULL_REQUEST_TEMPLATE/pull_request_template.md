# Pull Request

## Jira Ticket

TIME-###: [Ticket title]

Link: [Jira ticket URL]

---

## Summary of Changes

Brief description of what this PR does and why.

---

## Files Changed

- `path/to/file.py` — what changed and why
- `path/to/screen.swift` — what changed and why
- `docs/project_memory/...` — memory updates

---

## Commands Run

```bash
# List commands run during implementation
pytest backend/tests/
xcodebuild build -project ios/TimeSense.xcodeproj
./gradlew test
```

If no commands were run, state that explicitly and explain why.

---

## Tests / Verification

- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Manual verification steps completed
- [ ] iOS build succeeds (if iOS changes)
- [ ] Android build succeeds (if Android changes)

Describe what was tested and what was observed.

If tests were not run, explain why.

---

## Screenshots / Recordings

For UI changes, include screenshots or simulator notes.

---

## Project Memory Updates

- [ ] `docs/project_memory/implementation_log.md` updated
- [ ] `docs/project_memory/phase_status.md` updated
- [ ] `docs/project_memory/change_summary.md` updated
- [ ] `docs/project_memory/context_summary.md` updated
- [ ] `docs/project_memory/decision_log.md` updated (if decision made)
- [ ] `docs/project_memory/known_issues.md` updated (if issue found)
- [ ] `CHANGELOG.md` updated

---

## Known Issues

List any known issues, limitations, or follow-up tasks.

If none, write "None."

---

## Security / Privacy Notes

Does this PR:
- [ ] Touch auth or token handling?
- [ ] Store or transmit sensitive data?
- [ ] Change consent or permission flows?
- [ ] Modify admin access controls?
- [ ] Add new integration token storage?

Notes:

---

## Next Recommended Step

The next Jira ticket to work on after this PR merges:

`TIME-###: [next ticket title]`
