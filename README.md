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
# SAHYOG — Detect. Verify. Respond.

SAHYOG is a simulated health-monitoring and emergency-response prototype. It demonstrates one shared pipeline for detecting unusual health patterns, verifying the person’s condition, and escalating when there is no response.

The prototype is designed for local demonstrations and is not a clinical medical device or a guaranteed emergency-dispatch service.

## Demo scenarios

The same application pipeline supports three deterministic scenarios:

- `NORMAL` — simulated normal readings, no incident, no escalation.
- `TRUE_ANOMALY` — sustained abnormal readings, verification timeout, and escalation.
- `FALSE_ALARM` — abnormal readings, `I_AM_OK` confirmation, and false-alarm resolution.

Simulated readings and mock notifications must always be labelled as simulated.

## Architecture

- Flutter Android application for monitoring and scenario control.
- FastAPI backend for authentication, readings, anomaly integration, incidents, verification, escalation, and dashboard APIs.
- PostgreSQL with SQLAlchemy and Alembic for durable persistence.
- React caregiver dashboard for backend-authoritative status and incident visibility.
- Pluggable anomaly detector and notifier boundaries for future integrations.

The backend owns incident state. The detector supplies anomaly results; it does not create incidents directly. The dashboard consumes backend responses rather than detector payloads.

## Backend API highlights

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/token`
- `POST /api/v1/authorizations`
- `DELETE /api/v1/authorizations/{authorization_id}`
- `POST /api/v1/demo/runs`
- `GET /api/v1/demo/runs/{demo_run_id}`
- `POST /api/v1/demo/runs/{demo_run_id}/reset`
- `POST /api/v1/readings`
- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{incident_id}`
- `POST /api/v1/incidents/{incident_id}/verification`
- `GET /api/v1/dashboard/overview`
- `GET /health`

## Local backend setup

Requirements:

- Python 3.12
- `uv`
- PostgreSQL 16 for database-backed execution

From `backend/`:

```powershell
uv sync --locked --group migrations --group dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Copy `backend/.env.example` to a local `.env` and replace its placeholders. Never commit real passwords, signing keys, or database URLs.

Use separate credentials for:

- `SAHYOG_DATABASE_URL` — FastAPI runtime.
- `SAHYOG_MIGRATION_DATABASE_URL` — Alembic migrations.
- `SAHYOG_TEST_DATABASE_URL` — isolated PostgreSQL tests.

Apply schema changes only through Alembic migrations:

```powershell
uv run --locked --group migrations alembic -c alembic.ini upgrade head
```

## Security and data handling

- Passwords are stored as Argon2 hashes, never plaintext.
- Access tokens are signed JWTs with an environment-provided secret.
- Caregiver access requires explicit subject approval.
- Revocation immediately blocks future protected requests while preserving history.
- Migration and application database credentials are separate.
- Health data and location data should be minimized and must not be unnecessarily logged.

## Credits

SAHYOG was developed collaboratively by:

- **Prasiddh — AI/ML and health monitoring:** simulated reading analysis, anomaly detection, detector contracts, deterministic test vectors, and anomaly evidence design.
- **Vaishnavi — dashboard and location:** caregiver dashboard, location handling, hospital-data integration, and dashboard-facing state requirements.
- **Shubhankar — backend engineering:** FastAPI application, authentication, authorization, API schemas, incident lifecycle, verification, escalation orchestration, detector integration boundary, and backend tests.
- **Aditya — Flutter Android application:** mobile monitoring experience, demo scenario controls, verification UI, simulated reading presentation, and backend integration.
- **Utkarsh — software integration and database engineering:** PostgreSQL foundation, SQLAlchemy models, Alembic migrations, database roles, CI infrastructure, integration tests, notifier/hospital integration coordination, and cross-component integration.

## Project documents

- [PRD.md](PRD.md) — product requirements and scope.
- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) — architecture and contracts.
- [TEAM.md](TEAM.md) — ownership and responsibilities.
- [Agents.md](Agents.md) — coding-agent instructions.
- [HandOff.md](HandOff.md) — shared integration tracker.
