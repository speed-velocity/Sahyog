"""Tests for PostgreSQL location persistence repository using isolated in-memory SQLite."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from backend.app.db.base import Base
from backend.app.models.demo import DemoRun
from backend.app.models.identity import User
from backend.app.models.incidents import Incident
from backend.app.models.location import LocationSnapshotRecord
from backend.app.services.location import (
    DEFAULT_STALE_AFTER_SECONDS,
    LocationUpdateRequest,
)
from backend.app.services.location_persistence import (
    DemoRunNotFoundError,
    IncidentNotFoundError,
    get_latest_location_record_for_incident,
    get_latest_location_record_for_subject,
    persist_location_snapshot,
    snapshot_record_to_schema,
)
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.fixture
def sqlite_engine() -> Generator[Engine, None, None]:
    """Isolated SQLite in-memory database with foreign keys and btrim function."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        # Register btrim for ck_location_snapshots_source_kind_nonempty compatibility
        dbapi_connection.create_function(
            "btrim", 1, lambda s: s.strip() if s is not None else ""
        )

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def sqlite_session(sqlite_engine: Engine) -> Generator[Session, None, None]:
    """Session fixture specifically named to avoid collision with live DB fixtures."""
    with Session(sqlite_engine, expire_on_commit=False) as session:
        yield session


def _create_user(session: Session) -> User:
    user = User(
        user_id=uuid4(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(user)
    session.flush()
    return user


def _create_demo_run(session: Session, user: User, generation: int = 1) -> DemoRun:
    demo_run = DemoRun(
        demo_run_id=uuid4(),
        subject_user_id=user.user_id,
        scenario="NORMAL",
        status="RUNNING",
        current_generation=generation,
        started_at=datetime.now(UTC),
    )
    session.add(demo_run)
    session.flush()
    return demo_run


def _create_incident(
    session: Session, user: User, demo_run: DemoRun | None = None
) -> Incident:
    incident = Incident(
        incident_id=uuid4(),
        subject_user_id=user.user_id,
        demo_run_id=demo_run.demo_run_id if demo_run else None,
        run_generation=demo_run.current_generation if demo_run else None,
        status="PENDING_VERIFICATION",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(incident)
    session.flush()
    return incident


def test_persist_standalone_location_snapshot(sqlite_session: Session) -> None:
    user = _create_user(sqlite_session)
    now = datetime.now(UTC)
    snapshot_id = uuid4()
    received_at = now - timedelta(seconds=2)
    captured_at = now - timedelta(seconds=5)

    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        latitude=12.9716,
        longitude=77.5946,
        accuracy_meters=15.0,
        captured_at=captured_at,
        source_kind="GPS",
    )

    record = persist_location_snapshot(
        sqlite_session,
        update=update,
        location_snapshot_id=snapshot_id,
        received_at=received_at,
    )

    assert record.location_id == snapshot_id
    assert record.subject_user_id == user.user_id
    assert record.demo_run_id is None
    assert record.run_generation is None
    assert record.incident_id is None
    assert record.latitude == 12.9716
    assert record.longitude == 77.5946
    assert record.accuracy_meters == 15.0
    assert record.source_kind == "GPS"
    assert record.captured_at == captured_at
    assert record.received_at == received_at

    # Verify session is still active and not committed or closed
    assert sqlite_session.is_active
    assert record in sqlite_session


def test_persist_snapshot_resolves_demo_run_generation(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    demo_run = _create_demo_run(sqlite_session, user, generation=42)
    now = datetime.now(UTC)

    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        demo_run_id=demo_run.demo_run_id,
        latitude=28.6139,
        longitude=77.2090,
        accuracy_meters=10.0,
        captured_at=now,
        source_kind="NETWORK",
    )

    record = persist_location_snapshot(sqlite_session, update=update)

    assert record.location_id is not None
    assert record.subject_user_id == user.user_id
    assert record.demo_run_id == demo_run.demo_run_id
    assert record.run_generation == 42
    assert record.source_kind == "NETWORK"
    assert record.received_at is not None


def test_persist_snapshot_anchored_to_incident_and_demo_run(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    demo_run = _create_demo_run(sqlite_session, user, generation=5)
    incident = _create_incident(sqlite_session, user, demo_run)
    now = datetime.now(UTC)

    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        incident_id=incident.incident_id,
        demo_run_id=demo_run.demo_run_id,
        latitude=19.0760,
        longitude=72.8777,
        accuracy_meters=5.0,
        captured_at=now,
        source_kind="FUSED",
    )

    record = persist_location_snapshot(sqlite_session, update=update)

    assert record.subject_user_id == user.user_id
    assert record.incident_id == incident.incident_id
    assert record.demo_run_id == demo_run.demo_run_id
    assert record.run_generation == 5


def test_persist_snapshot_derives_demo_run_and_generation_from_incident(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    demo_run = _create_demo_run(sqlite_session, user, generation=7)
    incident = _create_incident(sqlite_session, user, demo_run)
    now = datetime.now(UTC)

    # Note: demo_run_id is omitted by caller
    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        incident_id=incident.incident_id,
        latitude=19.0760,
        longitude=72.8777,
        accuracy_meters=5.0,
        captured_at=now,
        source_kind="INCIDENT_RESOLVED",
    )

    record = persist_location_snapshot(sqlite_session, update=update)

    assert record.subject_user_id == user.user_id
    assert record.incident_id == incident.incident_id
    # Confirms demo_run_id and run_generation are derived from incident
    assert record.demo_run_id == demo_run.demo_run_id
    assert record.run_generation == 7


def test_persist_snapshot_with_standalone_incident_without_demo_run(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    incident = _create_incident(sqlite_session, user, demo_run=None)
    now = datetime.now(UTC)

    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        incident_id=incident.incident_id,
        latitude=19.0760,
        longitude=72.8777,
        accuracy_meters=5.0,
        captured_at=now,
        source_kind="STANDALONE_INCIDENT",
    )

    record = persist_location_snapshot(sqlite_session, update=update)

    assert record.subject_user_id == user.user_id
    assert record.incident_id == incident.incident_id
    assert record.demo_run_id is None
    assert record.run_generation is None


def test_persist_snapshot_rejects_missing_demo_run(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    now = datetime.now(UTC)

    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        demo_run_id=uuid4(),
        latitude=13.0827,
        longitude=80.2707,
        captured_at=now,
    )

    with pytest.raises(DemoRunNotFoundError, match="Demo run .* not found"):
        persist_location_snapshot(sqlite_session, update=update)


def test_persist_snapshot_rejects_cross_user_demo_run(
    sqlite_session: Session,
) -> None:
    user_a = _create_user(sqlite_session)
    user_b = _create_user(sqlite_session)
    demo_run_b = _create_demo_run(sqlite_session, user_b, generation=1)
    now = datetime.now(UTC)

    update = LocationUpdateRequest(
        subject_user_id=user_a.user_id,
        demo_run_id=demo_run_b.demo_run_id,
        latitude=13.0827,
        longitude=80.2707,
        captured_at=now,
    )

    with pytest.raises(DemoRunNotFoundError, match="Demo run .* not found"):
        persist_location_snapshot(sqlite_session, update=update)


def test_persist_snapshot_rejects_missing_incident(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    now = datetime.now(UTC)

    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        incident_id=uuid4(),
        latitude=13.0827,
        longitude=80.2707,
        captured_at=now,
    )

    with pytest.raises(IncidentNotFoundError, match="Incident .* not found"):
        persist_location_snapshot(sqlite_session, update=update)


def test_persist_snapshot_rejects_cross_user_incident(
    sqlite_session: Session,
) -> None:
    user_a = _create_user(sqlite_session)
    user_b = _create_user(sqlite_session)
    incident_b = _create_incident(sqlite_session, user_b)
    now = datetime.now(UTC)

    update = LocationUpdateRequest(
        subject_user_id=user_a.user_id,
        incident_id=incident_b.incident_id,
        latitude=13.0827,
        longitude=80.2707,
        captured_at=now,
    )

    with pytest.raises(IncidentNotFoundError, match="Incident .* not found"):
        persist_location_snapshot(sqlite_session, update=update)


def test_get_latest_location_record_for_subject_ordering(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    now = datetime.now(UTC)

    t0 = now - timedelta(seconds=30)
    t1 = now - timedelta(seconds=20)
    t2 = now - timedelta(seconds=10)

    u0 = LocationUpdateRequest(
        subject_user_id=user.user_id,
        latitude=10.0,
        longitude=10.0,
        captured_at=t0,
    )
    u1 = LocationUpdateRequest(
        subject_user_id=user.user_id,
        latitude=20.0,
        longitude=20.0,
        captured_at=t1,
    )
    u2 = LocationUpdateRequest(
        subject_user_id=user.user_id,
        latitude=30.0,
        longitude=30.0,
        captured_at=t2,
    )

    persist_location_snapshot(sqlite_session, update=u0, received_at=t0)
    persist_location_snapshot(sqlite_session, update=u1, received_at=t1)
    rec2 = persist_location_snapshot(sqlite_session, update=u2, received_at=t2)

    latest = get_latest_location_record_for_subject(sqlite_session, user.user_id)
    assert latest is not None
    assert latest.location_id == rec2.location_id
    assert latest.latitude == 30.0
    assert latest.longitude == 30.0


def test_get_latest_location_record_for_incident_ordering(
    sqlite_session: Session,
) -> None:
    user = _create_user(sqlite_session)
    demo_run = _create_demo_run(sqlite_session, user)
    incident_1 = _create_incident(sqlite_session, user, demo_run)
    incident_2 = _create_incident(sqlite_session, user, demo_run)
    now = datetime.now(UTC)

    t0 = now - timedelta(seconds=20)
    t1 = now - timedelta(seconds=10)
    t2 = now

    u0 = LocationUpdateRequest(
        subject_user_id=user.user_id,
        incident_id=incident_1.incident_id,
        demo_run_id=demo_run.demo_run_id,
        latitude=11.0,
        longitude=11.0,
        captured_at=t0,
    )
    u1 = LocationUpdateRequest(
        subject_user_id=user.user_id,
        incident_id=incident_1.incident_id,
        demo_run_id=demo_run.demo_run_id,
        latitude=12.0,
        longitude=12.0,
        captured_at=t1,
    )
    u2 = LocationUpdateRequest(
        subject_user_id=user.user_id,
        incident_id=incident_2.incident_id,
        demo_run_id=demo_run.demo_run_id,
        latitude=45.0,
        longitude=45.0,
        captured_at=t2,
    )

    persist_location_snapshot(sqlite_session, update=u0, received_at=t0)
    rec1 = persist_location_snapshot(sqlite_session, update=u1, received_at=t1)
    persist_location_snapshot(sqlite_session, update=u2, received_at=t2)

    latest_inc1 = get_latest_location_record_for_incident(
        sqlite_session, incident_1.incident_id
    )
    assert latest_inc1 is not None
    assert latest_inc1.location_id == rec1.location_id
    assert latest_inc1.latitude == 12.0


def test_get_latest_returns_none_when_empty(sqlite_session: Session) -> None:
    assert get_latest_location_record_for_subject(sqlite_session, uuid4()) is None
    assert get_latest_location_record_for_incident(sqlite_session, uuid4()) is None


def test_snapshot_record_to_schema_conversion(sqlite_session: Session) -> None:
    user = _create_user(sqlite_session)
    now = datetime.now(UTC)
    captured_at = now - timedelta(seconds=60)
    received_at = now - timedelta(seconds=55)

    update = LocationUpdateRequest(
        subject_user_id=user.user_id,
        latitude=15.5,
        longitude=75.5,
        accuracy_meters=8.0,
        captured_at=captured_at,
        source_kind="CELL",
    )
    record = persist_location_snapshot(
        sqlite_session,
        update=update,
        received_at=received_at,
    )

    # Fresh snapshot (age 60s < default 300s) -> is_stale False
    schema = snapshot_record_to_schema(record, now=now)
    assert schema.location_snapshot_id == record.location_id
    assert schema.subject_user_id == user.user_id
    assert schema.latitude == 15.5
    assert schema.longitude == 75.5
    assert schema.accuracy_meters == 8.0
    assert schema.source_kind == "CELL"
    assert schema.captured_at == captured_at
    assert schema.received_at == received_at
    assert schema.is_stale is False
    assert schema.stale_after_seconds == DEFAULT_STALE_AFTER_SECONDS

    # Older snapshot (age 400s > default 300s) -> is_stale True
    future_now = captured_at + timedelta(seconds=400)
    stale_schema = snapshot_record_to_schema(record, now=future_now)
    assert stale_schema.is_stale is True


def test_database_check_constraints_enforced(sqlite_session: Session) -> None:
    user = _create_user(sqlite_session)
    now = datetime.now(UTC)

    # Violate latitude range (> 90) directly on model
    invalid_record = LocationSnapshotRecord(
        location_id=uuid4(),
        subject_user_id=user.user_id,
        latitude=95.0,
        longitude=50.0,
        source_kind="TEST",
        captured_at=now,
        received_at=now,
    )
    sqlite_session.add(invalid_record)
    with pytest.raises(IntegrityError):
        sqlite_session.flush()
    sqlite_session.rollback()

    # Violate run_generation pair (demo_run_id without run_generation)
    invalid_run_pair = LocationSnapshotRecord(
        location_id=uuid4(),
        subject_user_id=user.user_id,
        demo_run_id=uuid4(),
        run_generation=None,
        latitude=10.0,
        longitude=10.0,
        source_kind="TEST",
        captured_at=now,
        received_at=now,
    )
    sqlite_session.add(invalid_run_pair)
    with pytest.raises(IntegrityError):
        sqlite_session.flush()
    sqlite_session.rollback()
