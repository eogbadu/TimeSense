# Jira Ticket Template

Copy this template when creating a new TIME-### ticket.

---

```
Ticket Key:   TIME-###
Title:        Short descriptive title
Phase:        Phase # — Phase Name
Priority:     P1 / P2 / P3
Labels:       backend / ios / android / web / admin / infra / docs

---

Goal:
What this ticket achieves. One paragraph.

---

Scope:
- Item 1
- Item 2
- Item 3

---

Non-goals:
- Do NOT do X
- Do NOT do Y
- Do NOT implement the next ticket's scope

---

Files likely changed:
- path/to/file.py
- path/to/screen.swift
- docs/project_memory/...

---

Acceptance criteria:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

---

Verification commands:
```bash
# Run tests
pytest backend/tests/

# Build check
xcodebuild build -project ios/TimeSense.xcodeproj

# etc.
```

---

Project memory updates required:
- [ ] docs/project_memory/implementation_log.md
- [ ] docs/project_memory/phase_status.md
- [ ] docs/project_memory/change_summary.md
- [ ] docs/project_memory/context_summary.md
- [ ] docs/project_memory/decision_log.md (if decision made)
- [ ] docs/project_memory/known_issues.md (if issue found)
- [ ] CHANGELOG.md

---

Dependencies:
- TIME-### must be complete before this ticket

---

Next ticket after this:
TIME-###
```
