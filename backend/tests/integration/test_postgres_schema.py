import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

REQUIRED_REVISION = "25c1af2fe01c"
REQUIRED_TABLES = {
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


def _test_database_url() -> str:
    raw_url = os.environ.get("SAHYOG_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("SAHYOG_TEST_DATABASE_URL is not configured")
    url = make_url(raw_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if url.drivername != "postgresql+psycopg":
        pytest.fail("SAHYOG_TEST_DATABASE_URL must use PostgreSQL Psycopg")
    return url.render_as_string(hide_password=False)


def test_postgres_schema_is_migrated_and_complete() -> None:
    engine = create_engine(_test_database_url(), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            revision = connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            tables = set(inspect(connection).get_table_names())
    finally:
        engine.dispose()

    assert revision == REQUIRED_REVISION
    assert REQUIRED_TABLES.issubset(tables)
