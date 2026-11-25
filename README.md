# Sahyog Android frontend

Flutter Android presentation app for the Sahyog hackathon project. The current
build is a local UI preview: simulator, backend, location, speech recognition,
and incident services are not connected.

## Technologies

- Flutter and Dart
- Material-style Flutter UI using the `material_ui` package
- Android runner project using Kotlin and Gradle
- Flutter widget tests

Use a Flutter SDK whose bundled Dart version satisfies the constraint in
`pubspec.yaml`.

## Run the app

From this directory:

```sh
flutter pub get
flutter run
```

The Android application ID is currently `com.sahyog.sahyog_mobile`. Confirm the
final application ID and release signing configuration with the integration
lead before preparing a release build.

## Frontend screens

- **Monitoring:** Shows connection and reading states, scenario controls, and a
  scenario progress preview.
- **Verification:** Shows that verification status is unavailable in this
  preview and provides a local-only acknowledgement interaction.
- **Incident:** Shows that incident status is unavailable and explains which
  future status information will come from the backend.

The illustrative **72 bpm** value is labeled “NOT LIVE DATA” and is not from a
sensor or simulator.

## Local scenario previews

The Monitoring screen provides `NORMAL`, `TRUE_ANOMALY`, and `FALSE_ALARM`.
Each button starts the same local 60-second presentation timer. A preview can
be reset or replayed, and a running preview prevents another scenario from
starting. These previews generate no readings and make no detection, incident,
verification, resolution, or escalation decisions.

The Verification screen’s “I’m okay” action only displays local preview
feedback. No reply is sent and no incident status is changed.

## Run tests and checks

From this directory:

```sh
dart format lib test
flutter analyze
flutter test
```

## Current limitations

- Heart-rate readings, simulator scenarios, and anomaly detection are not
  integrated. The preview timer is not a monitoring timer.
- Backend authentication, APIs, authoritative incident state, verification
  responses, and escalation are not integrated.
- Location services and location permissions are not integrated.
- Speech recognition, reply classification, and wearable connectivity are not
  implemented.
- Android release signing is not configured; the generated release build
  configuration currently uses debug signing.

## Pending integration dependencies

- **Prasiddh:** Publish the agreed simulator, heart-rate reading, and monitoring
  interfaces before connecting monitoring UI.
- **Shubhankar:** Confirm API routes, request/response schemas, authentication,
  incident lifecycle, verification behavior, and error contracts.
- **Vaishnavi:** Confirm the approved location interface and permission behavior
  before adding mobile location integration.
- **Utkarsh:** Confirm shared dependencies, Android SDK/build settings, final
  application ID, and release configuration.

No pending integration is represented as completed in this preview.
