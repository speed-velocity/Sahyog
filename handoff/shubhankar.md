# Individual Handoff

Owner: Shubhankar
Role: Backend
Last updated: 2026-11-27

## Completed
- Task IDs: B1.6 foundation slice started
- Summary: Added FastAPI application factory, environment-backed settings, bounded synchronous SQLAlchemy engine/session setup, `/health`, UTC clock, transaction helper, and versioned API router seam.

## In Progress
- Task IDs: B1.7, B1.10, I3.2, I3.4, I3.7, T0.4
- Current state: Added local JWT/Argon2 authentication, subject-controlled caregiver grant/revoke operations, immediate authorization checks, protected incident retrieval/verification routes, demo-run start/status/reset routes, reading ingestion/detector adapter seam, bounded incident lists, and dashboard overview. Incident, timeout, escalation, and PostgreSQL schema-test foundations remain integrated.

## Latest Backend Fixes
- Added `GET /api/v1/authorizations` for active authorization discovery. Caregivers receive their incoming subject grants; subjects receive grants they issued. The endpoint does not trust a caller-supplied subject ID and applies a bounded limit.
- Added `GET /api/v1/authorizations/me` for the caregiver dashboard. It derives the caregiver from the JWT and returns the `authorized_subjects` envelope with active subject grants only.
- Demo-start idempotency now rejects reuse of a key with a different scenario using `409`; exact same-scenario retries still replay the original run.
- Added dashboard development origins (`localhost:5173` and `127.0.0.1:5173`) to the default CORS configuration.
- Removed the committed password from the runtime database URL fallback. Deployments and local environments must provide `SAHYOG_DATABASE_URL` for their application connection.

## Files Changed
- `backend/app/main.py`: FastAPI application bootstrap.
- `backend/app/core/config.py`: validated runtime settings.
- `backend/app/db/session.py`: bounded synchronous SQLAlchemy engine/session dependency.
- `backend/app/api/health.py`: health endpoint.
- `backend/tests/test_health.py`: health endpoint test.
- `backend/app/core/clock.py`: shared timezone-aware UTC clock.
- `backend/app/db/transaction.py`: commit/rollback/close transaction boundary.
- `backend/app/api/v1.py`: `/api/v1` router seam.
- `backend/tests/test_infrastructure.py`: infrastructure tests.
- `backend/app/schemas/incidents.py`: confirmed initial status, transition, and `I_AM_OK` vocabulary.
- `backend/app/services/incident_lifecycle.py`: validated lifecycle state machine.
- `backend/app/services/notifier.py`: notifier protocol and structured result boundary.
- `backend/tests/test_incident_lifecycle.py`: lifecycle transition tests.
- `backend/alembic.ini`, `backend/migrations/`, `backend/tests/test_alembic_transaction_boundary.py`: integrated Utkarsh commit `800a806` migration infrastructure and test.
- `backend/app/services/incident_service.py`: generation-guarded incident creation, verification, and escalation-intent persistence.
- `backend/app/services/incident_service.py`: bounded expired-incident selection and notifier-result completion.
- `backend/app/schemas/incidents.py`, `backend/app/services/notifier.py`: explicit `ACCEPTED`, `DELIVERED`, `FAILED`, and `UNKNOWN` result vocabulary.
- `backend/tests/test_escalation_contract.py`: notifier-result contract test.
- `backend/app/workers/timeout.py`, `backend/tests/test_worker_contract.py`: bounded timeout batch worker and worker seam test.
- `backend/tests/integration/test_postgres_schema.py`: non-destructive schema/revision verification using `SAHYOG_TEST_DATABASE_URL`.
- `backend/app/core/auth.py`, `backend/app/api/auth.py`, `backend/app/schemas/auth.py`: local OAuth2 password/JWT authentication.
- `backend/app/models/auth.py`, `backend/migrations/versions/2f4d5b1a8c77_add_auth_identity_and_caregiver_authorization.py`: credential and caregiver authorization persistence.
- `backend/app/api/incidents.py`, `backend/app/schemas/api.py`: protected incident retrieval and subject verification routes.
- `backend/tests/test_auth.py`: password hashing and JWT claim tests.
- `backend/app/services/authorization.py`, `backend/app/api/authorizations.py`, `backend/app/schemas/authorization.py`: explicit subject approval and revocation routes.
- `backend/tests/test_authorization.py`: self-authorization and caregiver-role tests.
- `backend/app/api/demo.py`, `backend/app/schemas/demo.py`, `backend/app/services/demo.py`: demo-run lifecycle routes and generation reset.
- `backend/app/api/readings.py`, `backend/app/schemas/readings.py`, `backend/app/services/reading_service.py`, `backend/app/services/detector_adapter.py`: canonical reading ingestion and detector integration boundary.
- `backend/app/api/dashboard.py`, `backend/app/schemas/dashboard.py`: bounded backend-authoritative dashboard overview.
- `backend/.env.example`: safe placeholders for application, migration, test, auth, and demo-timeout configuration.
- `backend/app/models/`: imported Utkarsh's database foundation from commit `4df7d3b`.
- `backend/app/services/anomaly.py`, `backend/app/services/anomaly_integration.py`, `backend/app/services/detector_backend_contract.py`: integrated Prasiddh's published authoritative detector facade from `f496da0`.
- `backend/app/services/detector_provider.py`: bounded, locked detector-session cache keyed by subject/run/generation with configurable baseline.
- `backend/tests/test_detector_provider.py`: detector session isolation and anomaly-emission test.

## Interfaces
- Consumed: Utkarsh's SQLAlchemy models, Alembic migration infrastructure, migration role separation, and Python/uv dependency baseline.
- Exposed: `GET /health`; application settings and `get_db` dependency; incident lifecycle vocabulary and notifier protocol; detector-backed `POST /api/v1/readings`.
- Changed: Adopted Utkarsh's proposed initial incident statuses and `I_AM_OK` response for backend domain validation.

## Tests
- Command: `uv sync --locked --group dev; uv run --locked ruff check .; uv run --locked ruff format --check .; uv run --locked pytest`
- Result: Passed after installing Python 3.12 and uv; initial run was blocked until the toolchain was installed.
- Command: `py -m compileall -q backend`
- Result: Not run; Python launcher is unavailable in this environment.

- Command: `uv run --locked ruff check .`
- Result: Passed.
- Command: `uv run --locked ruff format --check .`
- Result: Passed.
- Command: `uv run --locked pytest`
- Result: Passed, 10 tests.
- Command: `uv run --locked --group migrations alembic -c alembic.ini upgrade head --sql`
- Result: Generated PostgreSQL DDL successfully; console truncation caused a broken-pipe traceback only because output was intentionally limited.
- Command: `uv run --locked pytest`
- Result: Passed, 10 tests; 1 PostgreSQL integration test skipped because `SAHYOG_TEST_DATABASE_URL` is not configured.
- Command: `uv run --locked pytest --ignore=tests/test_postgresql_schema.py --ignore=tests/integration/test_postgres_schema.py`
- Result: Passed, 25 tests.
- Command: FastAPI OpenAPI route registration check
- Result: Passed; 13 routes registered.
- Command: independent verification suite plus Alembic head check
- Result: Ruff passed, 25 tests passed, Alembic head `2f4d5b1a8c77`, and 13 routes registered.
- Command: `uv run --locked --group migrations alembic -c alembic.ini heads`
- Result: Passed; head is `2f4d5b1a8c77`.
- Command: disposable SQLite smoke test for incident creation and timeout intent
- Result: Passed; produced `ESCALATION_IN_PROGRESS` with one `PENDING` escalation attempt.
- Command: `uv run ruff check app tests; uv run ruff format --check app tests; uv run python -m compileall -q app`
- Result: Passed.
- Command: focused backend suite including auth, authorization, lifecycle, worker, health, infrastructure, escalation, metadata, and detector provider tests
- Result: Passed, 14 tests.
- Command: Prasiddh published detector integration and backend-contract tests
- Result: Passed, 34 tests and 4 subtests.
- Command: `uv run ruff check app tests; uv run ruff format --check app tests; uv run python -m compileall -q app`
- Result: Passed.
- Command: `uv run pytest -q --ignore=tests/test_postgresql_schema.py --ignore=tests/integration/test_postgres_schema.py`
- Result: Passed, 26 tests.
- Command: `uv run --group migrations alembic -c alembic.ini heads` and offline `upgrade head --sql`
- Result: Passed; Alembic head is `2f4d5b1a8c77` and both migrations generate PostgreSQL DDL.
- Command: full PostgreSQL suite with local isolated `sahyog_dev`/`sahyog_test` databases
- Result: Passed, 54 tests; SCRAM authentication restored after provisioning.
- Command: focused auth/authorization/health/infrastructure/metadata tests
- Result: Passed, 10 tests.
- Command: Ruff check and format check on backend app/tests
- Result: Passed.
- Command: OpenAPI route registration check
- Result: `/api/v1/authorizations`, `/api/v1/authorizations/me`, and `/api/v1/authorizations/{authorization_id}` registered.
- Command: focused demo/auth/authorization/health/infrastructure/metadata tests
- Result: Passed, 12 tests.

## Commits
- Commit ID: None; workspace is not currently a Git checkout.
- Summary: Changes are uncommitted in the shared workspace.

## Blockers
- Issue: Local database credentials are process-local and intentionally not committed.
- Required decision/owner: Each developer/CI environment must provide its own `SAHYOG_DATABASE_URL`, `SAHYOG_TEST_DATABASE_URL`, and `SAHYOG_MIGRATION_DATABASE_URL`.
- Issue: Local PostgreSQL credentials/service are not configured in this workspace.
- Required decision/owner: Provide isolated `sahyog_dev`/`sahyog_test` URLs when running database integration tests; never use migration credentials for FastAPI.
- Issue: The new auth migration must be applied to `sahyog_dev` and `sahyog_test` before live auth-route/database tests.
- Required decision/owner: Run the forward Alembic migration with `SAHYOG_MIGRATION_DATABASE_URL`; do not use application credentials for migration.
- Issue: The detector facade is integrated from the published source, but end-to-end API testing still depends on a live PostgreSQL database and authenticated demo user.
- Required decision/owner: Run the migration and API scenario tests in the shared integration environment.

## Next Steps
- Task: Push the integrated backend changes to the backend branch and run PostgreSQL scenario tests.
- Dependency: `SAHYOG_TEST_DATABASE_URL`, `SAHYOG_DATABASE_URL`, and migration application by Utkarsh.
