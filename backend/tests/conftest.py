"""Opt-in PostgreSQL test fixtures guarded to the isolated test database."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, Connection, Engine, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

TEST_DATABASE_NAME = "sahyog_test"
TEST_DATABASE_USER = "sahyog_migrator"
EXPECTED_REVISION = "25c1af2fe01c"
EXPECTED_TABLES = frozenset(
    {
        "users",
        "auth_identities",
        "caregiver_authorizations",
        "location_snapshots",
        "demo_runs",
        "health_readings",
        "anomaly_events",
        "incidents",
        "incident_anomaly_events",
        "verification_responses",
        "escalation_attempts",
        "incident_timeline_events",
    }
)


def validate_test_database_url(raw_url: str | None) -> URL:
    """Parse the test URL and reject anything outside the isolated DB contract."""
    if not raw_url:
        raise ValueError("SAHYOG_TEST_DATABASE_URL is required for database tests.")

    try:
        url = make_url(raw_url)
    except ArgumentError:
        raise ValueError(
            "SAHYOG_TEST_DATABASE_URL must be a valid SQLAlchemy URL."
        ) from None

    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if url.drivername != "postgresql+psycopg":
        raise ValueError("SAHYOG_TEST_DATABASE_URL must use PostgreSQL with Psycopg 3.")
    if url.username != TEST_DATABASE_USER:
        raise ValueError(
            "SAHYOG_TEST_DATABASE_URL must authenticate as sahyog_migrator."
        )
    if url.database != TEST_DATABASE_NAME:
        raise ValueError("SAHYOG_TEST_DATABASE_URL must target sahyog_test only.")

    return url


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Keep database-fixture tests out of the unit-only selection."""
    database_fixtures = {"test_database_engine", "db_connection", "db_session"}
    for item in items:
        if database_fixtures.intersection(item.fixturenames):
            item.add_marker(pytest.mark.integration)


def _connect_and_verify_database(engine: Engine) -> None:
    """Check target identity and the fully applied initial migration."""
    try:
        with engine.connect() as connection:
            database, current_user, session_user = connection.execute(
                text("SELECT current_database(), current_user, session_user")
            ).one()
            if database != TEST_DATABASE_NAME:
                pytest.fail("Test connection did not reach sahyog_test.", pytrace=False)
            if (current_user, session_user) != (TEST_DATABASE_USER, TEST_DATABASE_USER):
                pytest.fail(
                    "Test connection must use sahyog_migrator as current_user and session_user.",
                    pytrace=False,
                )

            inspector = inspect(connection)
            if not inspector.has_table("alembic_version", schema="public"):
                pytest.fail(
                    "sahyog_test is not migrated: public.alembic_version is missing.",
                    pytrace=False,
                )

            revisions = (
                connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                )
                .scalars()
                .all()
            )
            if revisions != [EXPECTED_REVISION]:
                pytest.fail(
                    f"sahyog_test must be at Alembic revision {EXPECTED_REVISION} before database tests.",
                    pytrace=False,
                )

            actual_tables = set(inspector.get_table_names(schema="public"))
            missing_tables = EXPECTED_TABLES - actual_tables
            if missing_tables:
                missing = ", ".join(sorted(missing_tables))
                pytest.fail(
                    f"sahyog_test is missing expected application tables: {missing}.",
                    pytrace=False,
                )
    except SQLAlchemyError:
        pytest.fail(
            "Could not verify PostgreSQL readiness for sahyog_test; check the test URL and migration state.",
            pytrace=False,
        )


@pytest.fixture(scope="session")
def test_database_engine() -> Iterator[Engine]:
    """Provide a verified, test-only engine when a database fixture is requested."""
    raw_url = os.environ.get("SAHYOG_TEST_DATABASE_URL")
    try:
        url = validate_test_database_url(raw_url)
    except ValueError as error:
        pytest.fail(str(error), pytrace=False)

    engine = create_engine(
        url,
        poolclass=NullPool,
        connect_args={
            "connect_timeout": 10,
            "options": "-c lock_timeout=5000 -c statement_timeout=15000",
        },
    )
    try:
        _connect_and_verify_database(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_connection(test_database_engine: Engine) -> Iterator[Connection]:
    """Provide a connection whose ordinary test writes are rolled back."""
    with test_database_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            if transaction.is_active:
                transaction.rollback()
            elif connection.in_transaction():
                connection.rollback()


@pytest.fixture
def db_session(db_connection: Connection) -> Iterator[Session]:
    """Bind a session to the rollback-scoped test connection."""
    with Session(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
    ) as session:
        yield session
