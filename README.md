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
