# SAHYOG — Role 4 Handoff: Flutter Android Frontend

**Project:** SAHYOG — Detect. Verify. Respond.  
**Role:** Role 4 — Aditya, Flutter Android frontend  
**Authorized branch for Aditya’s work:** `frontend` only  
**Repository HEAD at last validation:** `c41c70f` (`Merge branch 'main' into frontend`)  
**Status:** `TESTED` for the local preview UI and Android debug APK; integration with the shared simulator and backend remains pending.

## 1. Task IDs

- **M4.1:** Establish the canonical Flutter project under `mobile/`.
- **M4.2:** Restore Role 4 presentation components, state controller, and navigation shell.
- **M4.3:** Resolve package configuration and remove the invalid `material_ui` dependency.
- **M4.4:** Establish Android project configuration and launcher activity.
- **M4.5:** Consolidate Flutter files under one maintained project root.

## 2. Current Project State

- `mobile/` is the canonical Flutter project root. The root-level Flutter project files were removed after their contents were accounted for under `mobile/`.
- Package name: `sahyog_mobile`; version: `1.0.0+1`; Dart SDK constraint: `^3.14.0`.
- Android namespace and application ID: `com.sahyog.sahyog_mobile`.
- Android INTERNET permission is enabled. MainActivity uses the matching package. Java and Kotlin targets are 17.
- `mobile/.gitignore` excludes Flutter build output and caches, Gradle caches, machine-specific `android/local.properties`, and the generated plugin registrant.
- No `material_ui` dependency is declared. The Flutter Material UI is imported with `package:flutter/material.dart`.
- The current mobile UI is a clearly labelled local preview. It does not connect to real sensors or claim that local preview activity is backend state.

## 3. Implemented Role 4 Behavior

- Three-tab navigation: Monitor, Verify, Incident.
- NORMAL, TRUE_ANOMALY, and FALSE_ALARM scenario preview controls with a shared 60-second local preview timer, one active preview at a time, reset, and replay.
- Sample reading marked `NOT LIVE DATA`, with a disclaimer that it is an example and not a sensor or simulator reading.
- Loading, error, retry, connection, reading, and invalid-reading presentation states.
- Verification action is labelled `Preview only: I'm okay`; acknowledgment is local and explicitly does not send a reply or change incident state.
- Incident screen reports unavailable status in this isolated preview and identifies escalation and resolution as backend-supplied states. It does not invent an emergency outcome.
- Responsive monitoring and incident layouts were adjusted for narrow screens and increased text scaling.

These scenarios currently exercise only the local preview timer. They do **not** generate health samples, run anomaly detection, or create incidents.

## 4. Files in the Local Change Set

The initial implementation and seven root-level deletions were present before the final review. The changes remain local and uncommitted.

### Canonical Flutter project and UI

- `mobile/pubspec.yaml`
- `mobile/pubspec.lock`
- `mobile/analysis_options.yaml`
- `mobile/.gitignore`
- `mobile/lib/main.dart`
- `mobile/lib/app/sahyog_app.dart`
- `mobile/lib/features/monitoring/presentation/monitoring_screen.dart`
- `mobile/lib/features/monitoring/presentation/monitoring_reading_panel.dart`
- `mobile/lib/features/monitoring/presentation/preview_session_controller.dart`
- `mobile/lib/features/verification/presentation/verification_screen.dart`
- `mobile/lib/features/incident/presentation/incident_screen.dart`
- `mobile/lib/shared/widgets/async_state_panel.dart`
- `mobile/test/widget_test.dart` — 20 widget tests and 1 preview-controller unit test (21 test cases total).

### Android project

- `mobile/android/settings.gradle.kts`
- `mobile/android/build.gradle.kts`
- `mobile/android/gradle.properties`
- `mobile/android/gradle/wrapper/gradle-wrapper.properties`
- `mobile/android/gradle/wrapper/gradle-wrapper.jar`
- `mobile/android/gradlew` and `mobile/android/gradlew.bat`
- `mobile/android/app/build.gradle.kts`
- `mobile/android/app/src/main/AndroidManifest.xml`
- `mobile/android/app/src/debug/AndroidManifest.xml`
- `mobile/android/app/src/main/kotlin/com/sahyog/sahyog_mobile/MainActivity.kt`
- `mobile/android/app/src/main/res/values/styles.xml`
- `mobile/android/app/src/main/res/values-night/styles.xml`
- `mobile/android/app/src/main/res/drawable/launch_background.xml`
- `mobile/android/app/src/main/res/drawable-v21/launch_background.xml`

### Root-level Flutter files deleted as part of consolidation

- `AndroidManifest.xml`
- `analysis_options.yaml`
- `build.gradle.kts`
- `main.dart`
- `pubspec.lock`
- `pubspec.yaml`
- `widget_test.dart`

The canonical equivalents are in `mobile/`. The old root `pubspec.lock` was replaced by the lockfile generated for `mobile/pubspec.yaml`.

## 5. Flutter SDK and Validation

Flutter SDK used: `/Users/adityagupta/Documents/Codex/2026-11-24/explain-me-this-page-i-have/work/flutter-sdk/bin/flutter`  
Version: **Flutter 3.50.1**, **Dart 3.14.0**. Commands were run from `mobile/`.

| Command | Result |
| --- | --- |
| `flutter pub get` | Passed, exit 0. Generated `mobile/pubspec.lock`. |
| `flutter test` | Passed, exit 0. All 20 widget tests and the 1 preview-controller unit test passed (21 test cases total). |
| `flutter build apk --debug` | Passed, exit 0. APK: `mobile/build/app/outputs/flutter-apk/app-debug.apk`. |
| `flutter analyze` | Exit 1 with 11 info-level notices and no analyzer errors. Details below. |

### Analyzer notices

**Role 4 — 8 Material import deprecation notices (`deprecated_member_use`):**

- `mobile/lib/app/sahyog_app.dart:1`
- `mobile/lib/features/incident/presentation/incident_screen.dart:1`
- `mobile/lib/features/monitoring/presentation/monitoring_reading_panel.dart:1`
- `mobile/lib/features/monitoring/presentation/monitoring_screen.dart:1`
- `mobile/lib/features/verification/presentation/verification_screen.dart:1`
- `mobile/lib/main.dart:1`
- `mobile/lib/shared/widgets/async_state_panel.dart:1`
- `mobile/test/widget_test.dart:1`

Flutter 3.50.1 marks `package:flutter/material.dart` deprecated and suggests `package:material_ui/material_ui.dart`. The `material_ui` dependency was not added; the existing project requirements identify it as invalid. These notices remain visible and unsuppressed.

**Role 2 — 3 style notices (`prefer_initializing_formals`):**

- `mobile/lib/core/location/location_reporter.dart:31` (`_service`)
- `mobile/lib/core/location/location_reporter.dart:32` (`_sender`)
- `mobile/lib/core/location/location_service.dart:29` (`_provider`)

These are in Vaishnavi-owned files and were not modified.

## 6. Ownership and Historical Findings

- No Role 1, Role 2 location, Role 3 backend, Role 2 dashboard, or Role 5 shared architecture files were modified.
- The existing `mobile/lib/core/location/` implementation is Role 2-owned and was preserved.
- **Historical, unverified Role 1 report:** an earlier handoff draft listed errors in `sim_scenario.dart`, `simulator_heart_rate_source.dart`, `anomaly_event.dart`, `last_moments_buffer.dart`, and a test package-name mismatch. The corresponding Role 1 implementation paths are absent from this checkout. Those reported errors could not be verified and must not be treated as current findings.
- Shared project architecture and API contracts remain subject to `PRD.md`, `SYSTEM_DESIGN.md`, `TEAM.md`, and `HANDOFF.md`.

## 7. Remaining Work and Dependencies

1. Integrate the Role 1 simulator and health-reading source into the mobile scenario flow. The three scenarios must use the same approved processing pipeline.
2. Integrate the approved backend reading and demo-run APIs; confirm request and response contracts with Role 3 before implementation.
3. Connect verification actions to the backend. The current “I'm okay” action is preview-only and does not send a response.
4. Display backend-authoritative incident, verification, resolution, and escalation state. The mobile app must not invent final incident outcomes.
5. Coordinate cross-component integration with Roles 1, 3, and 5, then rerun Flutter validation and Android checks.

The frontend remains a local preview until these interfaces are agreed and implemented. No real wearable, Bluetooth, or sensor integration is present.

## 8. Git and Handoff

- Aditya’s authorized write branch is `frontend` only. Do not switch branches or modify another developer’s branch.
- At the last validation, the branch was `frontend` at HEAD `c41c70f`. All changes were uncommitted and local.
- **No commit or push has been made.** No commit ID exists.
- The seven root-level deletions and the untracked `mobile/` project files are part of the existing local change set and must be preserved for human review.
- Generated Flutter/Gradle output, caches, `mobile/android/local.properties`, and the generated plugin registrant are retained locally but ignored by `mobile/.gitignore`.
- `mobile/pubspec.lock` is the application lockfile and should be included with the Flutter project when the changes are reviewed for commit.
- Next action: complete simulator and backend integration against the approved contracts, then have Utkarsh review cross-component integration before merging.
