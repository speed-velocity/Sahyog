# Backend test setup

## Pytest configuration

The repository-root `pytest.ini` sets `backend/tests` as the test path and
registers the `integration` marker. When running tests from the repository
root, pass `-c pytest.ini` so pytest uses this configuration explicitly.

## Unit and static tests

Unit and static tests do not need a PostgreSQL connection:

```powershell
uv run --project backend pytest -c pytest.ini -m "not integration"
```

These tests do not require a PostgreSQL connection. PostgreSQL integration
tests are marked `integration` and run separately.

## PostgreSQL integration-test connection

Database fixtures are opt-in: PostgreSQL is contacted only by a test that asks
for `test_database_engine`, `db_connection`, or `db_session`. Set
`SAHYOG_TEST_DATABASE_URL` in the local environment to a SQLAlchemy Psycopg 3
URL with username `sahyog_migrator` and database name exactly `sahyog_test`.
For example, after setting a local password, use:

```powershell
$env:SAHYOG_TEST_DATABASE_URL = "postgresql+psycopg://sahyog_migrator:<local-password>@localhost:5432/sahyog_test"
```

The test URL is separate from `SAHYOG_MIGRATION_DATABASE_URL`, which remains
dedicated to Alembic. The migration URL must also target `sahyog_test` when
preparing the test schema. The fixtures reject all other database names,
including `sahyog_dev`, and verify the connected database and role before
exposing a connection. This guard prevents an integration test from writing to
the development database by mistake.

The initial test connection uses `sahyog_migrator` because the current
`sahyog_app` role has no table DML grants. Keep the test URL local or in the CI
secret/environment configuration; never add a real URL or password to source
control.

## Prepare and run database tests

Start PostgreSQL without deleting its named volume, then apply migrations to
the test database with the dedicated migration URL:

```powershell
$env:SAHYOG_MIGRATION_DATABASE_URL = "<local sahyog_migrator URL targeting sahyog_test>"
uv run --locked --group migrations alembic upgrade head
```

The suite currently contains 27 PostgreSQL integration tests in
`test_postgresql_schema.py`. They cover revision/table presence, scenario and
generation checks, heart-rate validation, same-subject/run composite foreign
keys, incident trigger/evidence constraints, idempotency uniqueness, the
one-triggering-evidence partial unique index, and restrictive delete behavior.
They test database constraints, not application lifecycle or concurrent
reset/worker behavior.

Run these tests from the repository root with the root pytest configuration:

```powershell
uv run --project backend pytest -c pytest.ini -m integration -v
```

The fixture requires `SAHYOG_TEST_DATABASE_URL`, verifies
the connected user, database, Alembic revision, and application tables, and
rejects `sahyog_dev` and all other database names.

Database tests use a `NullPool` engine and a per-test connection transaction.
The session joins that transaction using a savepoint; teardown rolls back and
closes the session and connection. Expected constraint failures also roll
back the failed session transaction so it remains usable. Test connections
use a 10-second connection timeout, 5-second lock timeout, and 15-second
statement timeout. These settings affect only the test fixture, not application
or migration connections.

No fixture truncates tables, drops schemas, deletes data outside its
rollback-scoped transaction, or resets volumes. The 27 cases do not include
multi-connection concurrency tests; reset-versus-worker serialization and
concurrent idempotency remain future work. A previous run before the latest
timeout/transaction-test adjustments reported 19 cases passed and was
interrupted while waiting at verification idempotency. This is historical and
does not verify the current PostgreSQL suite.
