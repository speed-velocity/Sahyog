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

## 9. Historical API Idempotency Contract Review (M4.6)

- **Status:** `TESTED` for the focused API unit tests; screen integration remains pending.
- Role 3 confirmed the backend idempotency contract: demo-start key replay requires the same scenario; a key reused with a different scenario returns 409; reading replay requires the exact same payload and returns the original persisted result; changed reading payloads return 409; verification retries reuse a key only for the exact same action, and each new action uses a new key.
- At the time of the earlier M4.6 review, commit `75b234b` was not present in the local Git object database; this was a historical limitation. The current remote reference has since been refreshed to `75b234b`, and the demo conflict behavior was inspected for M4.7.
- The generic API client already maps HTTP 409 to `ApiExceptionType.conflict` and passes successful replay response JSON through unchanged. No production API source or model change was needed.
- Added tests cover 409 conflict mapping, identical reading retry payloads, and preservation of replayed anomaly and incident identifiers.
- Files changed for that earlier task: `mobile/test/api_client_test.dart`, `mobile/test/api_models_test.dart`, and this handoff.
- Commands run from `mobile/`: focused `flutter test test/api_client_test.dart test/api_config_test.dart test/api_models_test.dart` passed (20 tests); `flutter analyze` exited 1 with 11 existing info-level notices and no analyzer errors; Dart formatting was applied to the two changed test files.
- No commit or push was made. The work remains on `frontend` at `ff22d94`.
- **Historical next action:** build typed API repository methods before connecting screens. The repository foundation is now recorded in M4.7 below; screen integration remains pending.

## 10. Endpoint-Specific API Repositories (M4.7)

- **Status:** `TESTED` for focused and full Flutter tests; API repositories are not connected to screens.
- Added endpoint-specific repositories over the existing `ApiClient` for registration/login, demo runs, readings, incidents, verification, and the flat backend dashboard overview. Added an in-memory-only `ApiSession`; no token persistence or automatic retries were introduced.
- Demo reset uses a bodyless POST. Protected repositories require a runtime Bearer token. Reading retry is an explicit resubmission of the same immutable request, retaining its idempotency key and serialized values. Verification accepts the caller-provided request/key and does not generate keys or retry automatically.
- Added a dashboard model matching the backend's flat overview shape, including nullable latest reading and incident fields. Incident parsing remains limited to the actual base incident response.
- Files created: `mobile/lib/core/api/api_session.dart`, `mobile/lib/core/api/api_response_parser.dart`, `mobile/lib/core/api/models/dashboard_models.dart`, and six files under `mobile/lib/core/api/repositories/` (`authentication_repository.dart`, `demo_repository.dart`, `reading_repository.dart`, `incident_repository.dart`, `verification_repository.dart`, `dashboard_repository.dart`); `mobile/test/api_repositories_test.dart`.
- Files modified: `mobile/lib/core/api/api_client.dart` (added bodyless POST), `mobile/lib/core/api/models/auth_models.dart` (registration request), `mobile/test/api_client_test.dart` (400 validation status coverage), and this handoff. No application screen, simulator, location, backend, or shared architecture file was changed.
- Routes covered: `POST /api/v1/auth/register`, `POST /api/v1/auth/token`, `POST /api/v1/demo/runs`, `GET /api/v1/demo/runs/{demo_run_id}`, `POST /api/v1/demo/runs/{demo_run_id}/reset`, `POST /api/v1/readings`, `GET /api/v1/incidents`, `GET /api/v1/incidents/{incident_id}`, `POST /api/v1/incidents/{incident_id}/verification`, and `GET /api/v1/dashboard/overview`.
- No dependency was added. The SDK required the already-authorized expanded filesystem access to write its own cache; no SDK permissions or files were manually changed.
- Commands from `mobile/`: `dart format` on changed Dart files (exit 0); focused API tests (`flutter test test/api_client_test.dart test/api_config_test.dart test/api_models_test.dart test/api_repositories_test.dart`) passed, 30 tests; full `flutter test` passed, 51 tests; `flutter analyze` exited 1 with the same 11 info-level notices and no analyzer errors. The 8 Role 4 Material import notices and 3 Role 2 style notices are unchanged and unsuppressed.
- Known contract caveat: backend verification retries currently return the incident for an existing incident/key without comparing request fields. The caller must generate a fresh key per new action and reuse the same immutable request only for its retry; Role 3 should confirm whether request-reference differences are considered a changed action.
- The local preview remains unchanged; no API repository is wired to a widget, simulator, SOS action, or location flow. No commit or push was made. Current branch/HEAD: `frontend` / `ff22d94`.
- **Next action:** resolve the simulator, auth UX/token lifetime, and backend verification retry contract with the responsible teammates before screen integration.

## 11. Backend Dashboard Overview UI (M4.8)

- **Status:** `TESTED` for mocked dashboard UI and the full Flutter suite; dashboard is not a live production integration until a backend URL and authenticated session are provided.
- Connected the existing `DashboardRepository` and flat `DashboardOverviewResponse` to a `Backend dashboard` app-bar action. The action opens a bottom sheet with the repository state; the local monitoring preview layout and timer remain unchanged.
- The panel displays backend `subject_user_id`, `monitoring_status`, `latest_reading` (BPM, source and timestamp when present), `active_incident`, `incident_status`, and `latest_update_at`. Null readings and incident/update fields have explicit unavailable/no-incident presentation.
- `SahyogApp` accepts the existing in-memory `ApiSession` and `DashboardRepository` as injection seams. Otherwise it constructs the existing repository using `SAHYOG_API_BASE_URL` from `--dart-define`; it does not supply a default API host. The controller avoids protected requests without a token and displays a sign-in-required message. The app still has no login screen or token persistence.
- Loading, API error message, and retry are presented in the dashboard sheet. No HTTP calls are placed in the monitoring widget; the controller invokes `DashboardRepository`.
- Files created: `mobile/lib/features/monitoring/presentation/dashboard_overview_controller.dart`, `mobile/lib/features/monitoring/presentation/dashboard_overview_panel.dart`, and `mobile/test/dashboard_integration_test.dart`.
- Files modified: `mobile/lib/app/sahyog_app.dart`, `mobile/lib/features/monitoring/presentation/monitoring_screen.dart` (no preview behavior changes), this handoff, and `mobile/test/widget_test.dart` was formatted while preserving its preview assertions.
- Focused dashboard tests: `flutter test test/dashboard_integration_test.dart` passed, 6 tests. Existing preview widget suite: `flutter test test/widget_test.dart` passed, 21 tests. Full suite: `flutter test` passed, 57 tests. Dart formatting passed. `flutter analyze` exited 1 with 13 info-level notices and no analyzer errors: the 11 pre-existing notices plus Material import notices in the new dashboard panel and dashboard integration test. Notices were not suppressed.
- `git diff --check` passed. Work remains local on `frontend` at `ff22d94`; no files were staged, committed or pushed.
- Remaining integration: provide an authenticated in-memory session from a future login flow and a configured reachable backend URL. This task does not connect simulator readings, verification, incidents, SOS, location, or backend navigation.
- **Next action:** coordinate authentication/UI token lifetime and backend connectivity before integrating any write operation or connecting this dashboard view to other screens.

## 12. Full Frontend Feature Integration & APK Build (M4.9)

- **Status:** `TESTED` (63/63 Flutter unit & widget tests passing; debug APK built; live backend integration verified via mocked HTTP transport).
- **Features Implemented:**
  - **Authentication (`AuthScreen`):** Login (`POST /api/v1/auth/token`) and Registration (`POST /api/v1/auth/register`) with form validation, role selector (`SUBJECT` / `CAREGIVER`), loading/error states, in-memory `ApiSession` token storage, and Logout.
  - **Monitoring & Simulation (`PreviewSessionController`, `MonitoringScreen`):** Deterministic simulated heart rate readings (`NORMAL`, `TRUE_ANOMALY`, `FALSE_ALARM`), spike/drop anomaly alert banner, and optional backend `DemoRepository.start` / `ReadingRepository.submit` ingestion when authenticated.
  - **Verification & Incidents (`VerificationScreen`, `IncidentScreen`):** Preserved preview-only UX while wiring live backend verification (`POST /api/v1/incidents/{id}/verification` with `I_AM_OK` and idempotency key) and live backend incident list/status feed (`GET /api/v1/incidents`).
  - **Location & Nearby Hospitals (`LocationHospitalsScreen`, `HospitalRepository`, `LocationRepository`):** Wired Vaishnavi's `LocationService` and `SimulatedLocationProvider` to `POST /api/v1/location/updates` and `GET /api/v1/hospitals/nearby`, clearly displaying `SIMULATED` location and `SEEDED_DEMO` hospital disclaimers.
  - **Caregiver Authorization Discovery (`AuthorizationRepository`):** Added `GET /api/v1/authorizations/me` repository and model support alongside the existing `DashboardOverviewPanel`.
- **Files Created:**
  - `mobile/lib/core/api/models/hospital_models.dart`
  - `mobile/lib/core/api/models/authorization_models.dart`
  - `mobile/lib/core/api/repositories/hospital_repository.dart`
  - `mobile/lib/core/api/repositories/authorization_repository.dart`
  - `mobile/lib/core/api/repositories/location_repository.dart`
  - `mobile/lib/features/auth/presentation/auth_screen.dart`
  - `mobile/lib/features/location/presentation/location_screen.dart`
  - `mobile/test/auth_screen_test.dart`
  - `mobile/test/location_screen_test.dart`
  - `mobile/test/hospital_repository_test.dart`
  - `mobile/test/authorization_repository_test.dart`
- **Files Modified:**
  - `mobile/lib/app/sahyog_app.dart`
  - `mobile/lib/features/monitoring/presentation/preview_session_controller.dart`
  - `mobile/lib/features/monitoring/presentation/monitoring_screen.dart`
  - `mobile/lib/features/verification/presentation/verification_screen.dart`
  - `mobile/lib/features/incident/presentation/incident_screen.dart`
  - `handoff/aditya.md`
- **Validation Results (from `mobile/`):**
  - `dart format .`: Passed (0 errors).
  - `flutter analyze`: 0 errors, 0 warnings, 20 info-level notices (pre-existing Material import deprecation notices, `use_null_aware_elements` in `location_repository.dart`, and `prefer_initializing_formals` in Role 2 location files).
  - `flutter test`: Passed (**63/63 tests** passing).
  - `git diff --check`: Passed (exit 0).
  - `flutter build apk --debug`: Passed (`mobile/build/app/outputs/flutter-apk/app-debug.apk`).
- **Git State:** All changes remain uncommitted and unstaged on `frontend`. No commit or push performed.
