# Skill: Native Android — Kotlin / Jetpack Compose

## Purpose
Build the native Android TimeSense app with Kotlin and Jetpack Compose. Maintain premium native Android UX throughout.

## When to Use
- Creating or modifying any Android screen
- Building Compose components
- Implementing Android navigation (NavController)
- Implementing Calendar Provider integration
- Implementing health/wake signals (Health Connect where supported)
- Implementing Android widgets (AppWidget)
- Implementing persistent notifications / notification action buttons
- Implementing location permissions
- Implementing Google Play Billing
- Implementing Google Assistant integration
- Running Android builds or tests

## Required Inputs
- Active Jira ticket
- Screen or feature to implement
- API endpoints it will consume

## Required Process

1. Read `docs/architecture/architecture_overview.md` → Android section
2. Follow feature folder structure: `android/app/src/main/kotlin/com/timesense/ui/[feature]/`
3. Use Kotlin and Jetpack Compose exclusively
4. Use the shared ApiClient for backend calls
5. Use shared design tokens / theme for colors, spacing, typography
6. Show loading / empty / error / permission-denied / paywall states on every screen
7. Request permissions with explanations before triggering system dialogs
8. Never write calendar events without user approval
9. Never enable DND without user approval
10. Add JUnit/Compose tests for non-trivial logic

## Required Outputs
- Compose UI files in `android/.../ui/[feature]/`
- Service files in `android/.../services/` (if new service)
- Tests in `android/.../test/`

## Files to Read First
- `docs/architecture/architecture_overview.md`
- `android/app/src/main/kotlin/com/timesense/services/ApiClient.kt`

## Commands / Checks
```bash
# Build
./gradlew assembleDebug

# Test
./gradlew test

# Lint
./gradlew lint
```

## Design Rules
- Default: light mode
- Premium native Android UX
- Material You / Compose Material 3 as baseline, customized to TimeSense design system
- No cluttered productivity dashboard
- No drag-and-drop schedule editor
- No guilt-driven copy
- Empty states must be beautiful, not blank
- "Why this?" hidden by default

## Prohibited Actions
- Do not use legacy View system unless Google forces it
- Do not write calendar events without explicit approval UI
- Do not enable DND without approval
- Do not store secrets in SharedPreferences unencrypted
- Do not make network calls directly from Composable functions — use ViewModels and Services

## End-of-Task Requirements
- App builds without errors
- UI follows premium direction
- Permission flows include explanations
- Project memory updated with Android notes
