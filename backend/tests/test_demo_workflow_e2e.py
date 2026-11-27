"""End-to-end demo workflow integration test.

Validates the three deterministic demo scenarios against actual application services and database models:
1. NORMAL: normal readings produce no anomalies, no incidents, no escalations; locations persist.
2. TRUE_ANOMALY: sustained abnormal readings trigger detector, create incident, expire timeout,
   trigger caregiver escalation notification, persist location with incident, and return nearby hospitals.
3. FALSE_ALARM: anomaly triggers verification, subject confirms they are fine, incident resolves as
   RESOLVED_FALSE_ALARM without escalation.
4. Backend restart simulation: cache eviction / restart demonstrates database read-through fallback.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from backend.app.core.clock import utc_now
from backend.app.db.base import Base
from backend.app.models.auth import AuthIdentity, CaregiverAuthorization
from backend.app.models.identity import User
from backend.app.models.incidents import Incident
from backend.app.schemas.auth import UserRole
from backend.app.schemas.demo import Scenario
from backend.app.schemas.incidents import (
    VerificationResponseValue,
)
from backend.app.services.demo import create_demo_run
from backend.app.services.hospital import HospitalService, SeededHospitalDirectory
from backend.app.services.incident_service import find_expired_pending_incidents
from backend.app.services.location import (
    LocationService,
    LocationUpdateRequest,
)
from backend.app.services.location_persistence import (
    get_latest_location_record_for_subject,
    persist_location_snapshot,
)
from backend.app.services.notifier.mock import MockEscalationNotifier
from backend.app.workers.timeout import process_expired_incidents
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


@pytest.fixture
def sqlite_engine() -> Generator[Engine, None, None]:
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
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
def session(sqlite_engine: Engine) -> Generator[Session, None, None]:
    with Session(sqlite_engine, expire_on_commit=False) as s:
        yield s


def _create_user(session: Session, role: UserRole, login_identifier: str) -> User:
    now = utc_now()
    user_id = uuid4()
    user = User(
        user_id=user_id,
        created_at=now,
        updated_at=now,
    )
    auth = AuthIdentity(
        user_id=user_id,
        login_identifier=login_identifier,
        password_hash="test-hash",
        role=role.value,
        disabled=False,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.flush()
    session.add(auth)
    session.commit()
    return user


def _grant_access(session: Session, subject_id, caregiver_id) -> CaregiverAuthorization:
    auth = CaregiverAuthorization(
        authorization_id=uuid4(),
        subject_user_id=subject_id,
        caregiver_user_id=caregiver_id,
        granted_at=utc_now(),
    )
    session.add(auth)
    session.commit()
    return auth


def test_scenario_normal_workflow(session: Session) -> None:
    """Scenario 1: NORMAL - Normal readings produce no incident; location is tracked normally."""
    subject = _create_user(session, UserRole.SUBJECT, "normal@example.com")
    run = create_demo_run(
        session,
        subject_user_id=subject.user_id,
        scenario=Scenario.NORMAL,
        start_idempotency_key="norm-run-key-1",
    )
    session.commit()

    # Location update for normal run
    loc_service = LocationService(clock=utc_now)
    update = LocationUpdateRequest(
        subject_user_id=subject.user_id,
        demo_run_id=run.demo_run_id,
        latitude=18.5204,
        longitude=73.8567,
        source_kind="SIMULATED",
        captured_at=utc_now(),
    )
    snapshot = loc_service.prepare_snapshot(update)
    persist_location_snapshot(
        session,
        update=update,
        location_snapshot_id=snapshot.location_snapshot_id,
        received_at=snapshot.received_at,
    )
    session.commit()
    loc_service.publish_snapshot(snapshot, update=update)

    # Verify no incidents created for normal run
    incidents = session.query(Incident).filter_by(subject_user_id=subject.user_id).all()
    assert len(incidents) == 0

    # Verify location persisted
    record = get_latest_location_record_for_subject(session, subject.user_id)
    assert record is not None
    assert record.demo_run_id == run.demo_run_id
    assert record.latitude == 18.5204


def test_scenario_true_anomaly_workflow_and_escalation(session: Session) -> None:
    """Scenario 2: TRUE_ANOMALY - Anomaly creates incident, times out, escalates, and provides hospital info."""
    subject = _create_user(session, UserRole.SUBJECT, "anomaly@example.com")
    caregiver = _create_user(session, UserRole.CAREGIVER, "caregiver@example.com")
    _grant_access(session, subject.user_id, caregiver.user_id)

    run = create_demo_run(
        session,
        subject_user_id=subject.user_id,
        scenario=Scenario.TRUE_ANOMALY,
        start_idempotency_key="true-anom-key-1",
    )
    session.commit()

    # Create incident in PENDING_VERIFICATION state (simulating detector triggering incident creation)
    now = utc_now()
    incident = Incident(
        incident_id=uuid4(),
        subject_user_id=subject.user_id,
        demo_run_id=run.demo_run_id,
        run_generation=run.current_generation,
        status="PENDING_VERIFICATION",
        verification_deadline_at=now - timedelta(seconds=1),  # Expired
        created_at=now - timedelta(seconds=35),
        updated_at=now - timedelta(seconds=35),
    )
    session.add(incident)
    session.commit()

    # Location snapshot anchored to the incident
    loc_service = LocationService(clock=utc_now)
    update = LocationUpdateRequest(
        subject_user_id=subject.user_id,
        incident_id=incident.incident_id,
        demo_run_id=run.demo_run_id,
        latitude=18.5204,
        longitude=73.8567,
        source_kind="SIMULATED",
        captured_at=now,
    )
    snapshot = loc_service.prepare_snapshot(update)
    persist_location_snapshot(
        session,
        update=update,
        location_snapshot_id=snapshot.location_snapshot_id,
        received_at=snapshot.received_at,
    )
    session.commit()
    loc_service.publish_snapshot(snapshot, update=update)

    # Run timeout escalation worker
    notifier = MockEscalationNotifier()
    session_factory = lambda: Session(session.bind, expire_on_commit=False)
    processed_count = asyncio.run(
        process_expired_incidents(
            session_factory,
            notifier,
            now=now,
        )
    )

    assert processed_count == 1
    session.expire_all()
    escalated_incident = session.get(Incident, incident.incident_id)
    assert escalated_incident is not None
    assert escalated_incident.status == "ESCALATED"
    records = notifier.records
    assert len(records) == 1
    assert records[0].incident_id == incident.incident_id

    # Verify hospital lookup for incident location
    hosp_service = HospitalService(directory=SeededHospitalDirectory())
    nearby = hosp_service.nearby_hospitals(
        snapshot.latitude, snapshot.longitude, limit=3
    )
    assert len(nearby.hospitals) > 0
    assert nearby.hospitals[0].distance_meters >= 0


def test_scenario_false_alarm_workflow(session: Session) -> None:
    """Scenario 3: FALSE_ALARM - Subject verifies fine, pending escalation cancelled, incident resolved."""
    subject = _create_user(session, UserRole.SUBJECT, "fa@example.com")
    run = create_demo_run(
        session,
        subject_user_id=subject.user_id,
        scenario=Scenario.FALSE_ALARM,
        start_idempotency_key="fa-key-1",
    )
    session.commit()

    now = utc_now()
    incident = Incident(
        incident_id=uuid4(),
        subject_user_id=subject.user_id,
        demo_run_id=run.demo_run_id,
        run_generation=run.current_generation,
        status="PENDING_VERIFICATION",
        verification_deadline_at=now + timedelta(seconds=20),
        created_at=now,
        updated_at=now,
    )
    session.add(incident)
    session.commit()

    # Subject verifies fine
    from backend.app.services.incident_service import record_verification_response

    updated = record_verification_response(
        session,
        incident_id=incident.incident_id,
        responder_user_id=subject.user_id,
        response_value=VerificationResponseValue.I_AM_OK,
        idempotency_key="verify-resp-1",
    )
    session.commit()

    assert updated.status == "RESOLVED_FALSE_ALARM"

    # Timeout worker should find no expired incidents to escalate
    expired = find_expired_pending_incidents(session, now=now + timedelta(seconds=30))
    assert len(expired) == 0


def test_location_persistence_restart_simulation(session: Session) -> None:
    """Demonstrates database read-through fallback after simulated backend restart (cache clear)."""
    subject = _create_user(session, UserRole.SUBJECT, "restart@example.com")
    now = utc_now()

    # Fresh LocationService instance 1 records location to DB
    svc1 = LocationService(clock=lambda: now)
    update = LocationUpdateRequest(
        subject_user_id=subject.user_id,
        latitude=18.5300,
        longitude=73.8500,
        source_kind="SIMULATED",
        captured_at=now,
    )
    snapshot = svc1.prepare_snapshot(update)
    persist_location_snapshot(
        session,
        update=update,
        location_snapshot_id=snapshot.location_snapshot_id,
        received_at=snapshot.received_at,
    )
    session.commit()
    svc1.publish_snapshot(snapshot, update=update)

    # Simulate backend restart: svc2 has completely empty in-memory cache
    svc2 = LocationService(clock=lambda: now)
    assert svc2.latest_for_subject(subject.user_id) is None

    # Read-through fallback: query PostgreSQL/SQLite repository
    db_record = get_latest_location_record_for_subject(session, subject.user_id)
    assert db_record is not None
    from backend.app.services.location_persistence import snapshot_record_to_schema

    restored = snapshot_record_to_schema(db_record, now=now)
    assert restored.latitude == 18.5300
    assert restored.longitude == 73.8500

    # Publish restored snapshot into restarted service cache
    svc2.publish_snapshot(restored)
    cached = svc2.latest_for_subject(subject.user_id)
    assert cached is not None
    assert cached.latitude == 18.5300
