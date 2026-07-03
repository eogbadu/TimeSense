# Mobile Android Agent

## Purpose
Build and maintain the native Android TimeSense app using Kotlin and Jetpack Compose.

## Inputs
- Active Jira ticket
- Screen or feature to implement
- API endpoints to consume
- Design direction from `.claude/skills/mobile-ux-premium/`

## Outputs
- Compose UI files in `android/app/src/main/kotlin/com/timesense/ui/[feature]/`
- Services in `android/.../services/`
- JUnit / Compose tests

## Allowed Files / Areas
- `android/` (all subdirectories)
- `docs/project_memory/` (memory updates)
- `CHANGELOG.md`

## Forbidden Actions
- Do not modify iOS or backend source files
- Do not use legacy Android Views unless forced
- Do not write calendar events without user approval UI
- Do not enable DND without user approval
- Do not store secrets in SharedPreferences unencrypted

## Required Tests
- JUnit tests for non-trivial logic
- Compose UI tests for critical flows

## Skills to Use
- `.claude/skills/native-android-compose/SKILL.md`
- `.claude/skills/mobile-ux-premium/SKILL.md`
