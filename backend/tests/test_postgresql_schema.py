from datetime import UTC, datetime
from uuid import uuid4

import pytest
from backend.app.models import (
    AnomalyEvent,
    DemoRun,
    EscalationAttempt,
    HealthReading,
    Incident,
    IncidentAnomalyEvent,
    IncidentTimelineEvent,
    User,
    VerificationResponse,
)
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

EXPECTED_REVISION = "99e748e414e3"
EXPECTED_TABLES = {
    "users",
    "demo_runs",
    "health_readings",
    "anomaly_events",
    "incidents",
    "incident_anomaly_events",
    "verification_responses",
    "escalation_attempts",
    "incident_timeline_events",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _user(session: Session) -> User:
    now = _now()
    user = User(user_id=uuid4(), created_at=now, updated_at=now)
    session.add(user)
    session.flush()
    return user


def _run(session: Session, subject_user_id, **overrides) -> DemoRun:
    values = {
        "demo_run_id": uuid4(),
        "subject_user_id": subject_user_id,
        "scenario": "NORMAL",
        "status": "TEST_STATUS",
        "outcome": None,
        "current_generation": 1,
        "start_idempotency_key": None,
        "started_at": _now(),
        "completed_at": None,
        "reset_at": None,
    }
    values.update(overrides)
    run = DemoRun(**values)
    session.add(run)
    session.flush()
    return run


def _reading(
    subject_user_id,
    *,
    demo_run_id=None,
    run_generation=None,
    ingestion_idempotency_key=None,
) -> HealthReading:
    now = _now()
    return HealthReading(
        reading_id=uuid4(),
        subject_user_id=subject_user_id,
        demo_run_id=demo_run_id,
        run_generation=run_generation,
        source_kind="SIMULATED",
        heart_rate_bpm=72,
        observed_at=now,
        received_at=now,
        activity_context=None,
        source_record_id=None,
        ingestion_idempotency_key=ingestion_idempotency_key,
    )


def _anomaly(
    subject_user_id,
    demo_run_id,
    *,
    generation=1,
    dedupe_key=None,
) -> AnomalyEvent:
    return AnomalyEvent(
        anomaly_event_id=uuid4(),
        subject_user_id=subject_user_id,
        demo_run_id=demo_run_id,
        run_generation=generation,
        detected_at=_now(),
        detector_result="TEST_RESULT",
        severity=None,
        explanation=None,
        detector_version=None,
        dedupe_key=dedupe_key or str(uuid4()),
    )


def _incident(
    subject_user_id,
    *,
    demo_run_id=None,
    run_generation=None,
    triggering_anomaly_event_id=None,
    creation_idempotency_key=None,
) -> Incident:
    now = _now()
    return Incident(
        incident_id=uuid4(),
        subject_user_id=subject_user_id,
        demo_run_id=demo_run_id,
        run_generation=run_generation,
        triggering_anomaly_event_id=triggering_anomaly_event_id,
        status="TEST_STATUS",
        creation_idempotency_key=creation_idempotency_key,
        created_at=now,
        updated_at=now,
        verification_deadline_at=None,
        resolved_at=None,
    )


def _expect_integrity_error(session: Session, row) -> None:
    session.add(row)
    try:
        with pytest.raises(IntegrityError):
            session.flush()
    finally:
        session.rollback()


def _expect_statement_integrity_error(
    session: Session,
    statement,
    parameters: dict,
) -> None:
    try:
        with pytest.raises(IntegrityError):
            session.execute(statement, parameters)
    finally:
        session.rollback()


def test_applied_revision_and_all_application_tables_exist(
    test_database_engine,
) -> None:
    with test_database_engine.connect() as connection:
        tables = set(inspect(connection).get_table_names(schema="public"))
        revision = (
            connection.execute(text("SELECT version_num FROM public.alembic_version"))
            .scalars()
            .all()
        )

    assert EXPECTED_TABLES <= tables
    assert revision == [EXPECTED_REVISION]


def test_demo_run_rejects_unsupported_scenario(db_session: Session) -> None:
    user = _user(db_session)
    _expect_integrity_error(
        db_session,
        DemoRun(
            demo_run_id=uuid4(),
            subject_user_id=user.user_id,
            scenario="UNSUPPORTED",
            status="TEST_STATUS",
            outcome=None,
            current_generation=1,
            start_idempotency_key=None,
            started_at=_now(),
            completed_at=None,
            reset_at=None,
        ),
    )


def test_demo_run_requires_positive_generation(db_session: Session) -> None:
    user = _user(db_session)
    _expect_integrity_error(
        db_session,
        DemoRun(
            demo_run_id=uuid4(),
            subject_user_id=user.user_id,
            scenario="NORMAL",
            status="TEST_STATUS",
            outcome=None,
            current_generation=0,
            start_idempotency_key=None,
            started_at=_now(),
            completed_at=None,
            reset_at=None,
        ),
    )


def test_demo_run_subject_must_reference_an_existing_user(db_session: Session) -> None:
    _expect_integrity_error(
        db_session,
        DemoRun(
            demo_run_id=uuid4(),
            subject_user_id=uuid4(),
            scenario="NORMAL",
            status="TEST_STATUS",
            outcome=None,
            current_generation=1,
            start_idempotency_key=None,
            started_at=_now(),
            completed_at=None,
            reset_at=None,
        ),
    )


def test_health_reading_requires_positive_bpm(db_session: Session) -> None:
    user = _user(db_session)
    reading = _reading(user.user_id)
    reading.heart_rate_bpm = 0
    _expect_integrity_error(db_session, reading)


def test_health_reading_requires_run_and_generation_together(
    db_session: Session,
) -> None:
    user = _user(db_session)
    _expect_integrity_error(
        db_session,
        _reading(user.user_id, run_generation=1),
    )


def test_health_reading_requires_positive_run_generation(db_session: Session) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    _expect_integrity_error(
        db_session,
        _reading(user.user_id, demo_run_id=run.demo_run_id, run_generation=0),
    )


def test_anomaly_event_requires_positive_generation(db_session: Session) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    _expect_integrity_error(
        db_session,
        _anomaly(user.user_id, run.demo_run_id, generation=0),
    )


def test_incident_requires_run_and_generation_together(db_session: Session) -> None:
    user = _user(db_session)
    _expect_integrity_error(
        db_session,
        _incident(user.user_id, run_generation=1),
    )


def test_incident_requires_positive_run_generation(db_session: Session) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    _expect_integrity_error(
        db_session,
        _incident(
            user.user_id,
            demo_run_id=run.demo_run_id,
            run_generation=0,
        ),
    )


def test_triggering_anomaly_requires_a_demo_run(db_session: Session) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    anomaly = _anomaly(user.user_id, run.demo_run_id)
    db_session.add(anomaly)
    db_session.flush()

    _expect_integrity_error(
        db_session,
        _incident(
            user.user_id,
            triggering_anomaly_event_id=anomaly.anomaly_event_id,
        ),
    )


def test_reading_composite_fk_requires_matching_run_subject(
    db_session: Session,
) -> None:
    run_owner = _user(db_session)
    different_subject = _user(db_session)
    run = _run(db_session, run_owner.user_id)

    _expect_integrity_error(
        db_session,
        _reading(
            different_subject.user_id,
            demo_run_id=run.demo_run_id,
            run_generation=run.current_generation,
        ),
    )


def test_incident_trigger_fk_requires_matching_subject_and_run(
    db_session: Session,
) -> None:
    anomaly_owner = _user(db_session)
    incident_owner = _user(db_session)
    anomaly_run = _run(db_session, anomaly_owner.user_id)
    incident_run = _run(db_session, incident_owner.user_id)
    anomaly = _anomaly(anomaly_owner.user_id, anomaly_run.demo_run_id)
    db_session.add(anomaly)
    db_session.flush()

    _expect_integrity_error(
        db_session,
        _incident(
            incident_owner.user_id,
            demo_run_id=incident_run.demo_run_id,
            run_generation=incident_run.current_generation,
            triggering_anomaly_event_id=anomaly.anomaly_event_id,
        ),
    )


def test_evidence_fk_requires_matching_incident_subject_and_run(
    db_session: Session,
) -> None:
    incident_owner = _user(db_session)
    evidence_owner = _user(db_session)
    incident_run = _run(db_session, incident_owner.user_id)
    evidence_run = _run(db_session, evidence_owner.user_id)
    incident = _incident(
        incident_owner.user_id,
        demo_run_id=incident_run.demo_run_id,
        run_generation=incident_run.current_generation,
    )
    anomaly = _anomaly(evidence_owner.user_id, evidence_run.demo_run_id)
    db_session.add_all([incident, anomaly])
    db_session.flush()

    _expect_integrity_error(
        db_session,
        IncidentAnomalyEvent(
            incident_id=incident.incident_id,
            anomaly_event_id=anomaly.anomaly_event_id,
            subject_user_id=evidence_owner.user_id,
            demo_run_id=evidence_run.demo_run_id,
            evidence_role="SUPPORTING",
            associated_at=_now(),
        ),
    )


def test_evidence_fk_requires_matching_anomaly_subject_and_run(
    db_session: Session,
) -> None:
    owner = _user(db_session)
    incident_run = _run(db_session, owner.user_id)
    other_run = _run(db_session, owner.user_id)
    incident = _incident(
        owner.user_id,
        demo_run_id=incident_run.demo_run_id,
        run_generation=incident_run.current_generation,
    )
    anomaly = _anomaly(owner.user_id, other_run.demo_run_id)
    db_session.add_all([incident, anomaly])
    db_session.flush()

    _expect_integrity_error(
        db_session,
        IncidentAnomalyEvent(
            incident_id=incident.incident_id,
            anomaly_event_id=anomaly.anomaly_event_id,
            subject_user_id=owner.user_id,
            demo_run_id=incident_run.demo_run_id,
            evidence_role="SUPPORTING",
            associated_at=_now(),
        ),
    )


def test_demo_run_start_idempotency_is_unique_per_subject(db_session: Session) -> None:
    user = _user(db_session)
    _run(db_session, user.user_id, start_idempotency_key="run-start-key")

    _expect_integrity_error(
        db_session,
        DemoRun(
            demo_run_id=uuid4(),
            subject_user_id=user.user_id,
            scenario="NORMAL",
            status="TEST_STATUS",
            outcome=None,
            current_generation=1,
            start_idempotency_key="run-start-key",
            started_at=_now(),
            completed_at=None,
            reset_at=None,
        ),
    )


def test_reading_ingestion_idempotency_is_unique_per_subject(
    db_session: Session,
) -> None:
    user = _user(db_session)
    key = "reading-ingestion-key"
    first = _reading(user.user_id, ingestion_idempotency_key=key)
    db_session.add(first)
    db_session.flush()

    _expect_integrity_error(
        db_session,
        _reading(user.user_id, ingestion_idempotency_key=key),
    )


def test_anomaly_dedupe_is_unique_per_run_generation(db_session: Session) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    key = "anomaly-dedupe-key"
    db_session.add(_anomaly(user.user_id, run.demo_run_id, dedupe_key=key))
    db_session.flush()

    _expect_integrity_error(
        db_session,
        _anomaly(user.user_id, run.demo_run_id, dedupe_key=key),
    )


def test_incident_creation_idempotency_is_unique_per_subject(
    db_session: Session,
) -> None:
    user = _user(db_session)
    db_session.add(_incident(user.user_id, creation_idempotency_key="incident-key"))
    db_session.flush()

    _expect_integrity_error(
        db_session,
        _incident(user.user_id, creation_idempotency_key="incident-key"),
    )


def test_verification_idempotency_is_unique_per_incident(db_session: Session) -> None:
    user = _user(db_session)
    incident = _incident(user.user_id)
    db_session.add(incident)
    db_session.flush()
    response_time = _now()

    def response() -> VerificationResponse:
        return VerificationResponse(
            verification_response_id=uuid4(),
            incident_id=incident.incident_id,
            responder_user_id=user.user_id,
            response_value="TEST_RESPONSE",
            idempotency_key="verification-key",
            responded_at=response_time,
            request_reference=None,
        )

    db_session.add(response())
    db_session.flush()
    _expect_integrity_error(db_session, response())
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1


def test_escalation_idempotency_is_unique_per_incident(db_session: Session) -> None:
    user = _user(db_session)
    incident = _incident(user.user_id)
    db_session.add(incident)
    db_session.flush()

    def attempt() -> EscalationAttempt:
        return EscalationAttempt(
            escalation_attempt_id=uuid4(),
            incident_id=incident.incident_id,
            trigger_reason="TEST_REASON",
            status="TEST_STATUS",
            started_at=_now(),
            completed_at=None,
            idempotency_key="escalation-key",
        )

    db_session.add(attempt())
    db_session.flush()
    _expect_integrity_error(db_session, attempt())


def test_timeline_event_idempotency_is_unique_per_incident(db_session: Session) -> None:
    user = _user(db_session)
    incident = _incident(user.user_id)
    db_session.add(incident)
    db_session.flush()

    def event() -> IncidentTimelineEvent:
        return IncidentTimelineEvent(
            timeline_event_id=uuid4(),
            incident_id=incident.incident_id,
            event_type="TEST_EVENT",
            occurred_at=_now(),
            actor_user_id=None,
            event_idempotency_key="timeline-key",
            details=None,
        )

    db_session.add(event())
    db_session.flush()
    _expect_integrity_error(db_session, event())


def test_only_one_triggering_evidence_row_is_allowed_per_incident(
    db_session: Session,
) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    first_anomaly = _anomaly(user.user_id, run.demo_run_id)
    second_anomaly = _anomaly(user.user_id, run.demo_run_id)
    db_session.add_all([first_anomaly, second_anomaly])
    db_session.flush()
    incident = _incident(
        user.user_id,
        demo_run_id=run.demo_run_id,
        run_generation=run.current_generation,
        triggering_anomaly_event_id=first_anomaly.anomaly_event_id,
    )
    db_session.add(incident)
    db_session.flush()

    db_session.add_all(
        [
            IncidentAnomalyEvent(
                incident_id=incident.incident_id,
                anomaly_event_id=first_anomaly.anomaly_event_id,
                subject_user_id=user.user_id,
                demo_run_id=run.demo_run_id,
                evidence_role="TRIGGERING",
                associated_at=_now(),
            ),
            IncidentAnomalyEvent(
                incident_id=incident.incident_id,
                anomaly_event_id=second_anomaly.anomaly_event_id,
                subject_user_id=user.user_id,
                demo_run_id=run.demo_run_id,
                evidence_role="SUPPORTING",
                associated_at=_now(),
            ),
        ]
    )
    db_session.flush()

    _expect_integrity_error(
        db_session,
        IncidentAnomalyEvent(
            incident_id=incident.incident_id,
            anomaly_event_id=second_anomaly.anomaly_event_id,
            subject_user_id=user.user_id,
            demo_run_id=run.demo_run_id,
            evidence_role="TRIGGERING",
            associated_at=_now(),
        ),
    )


def test_user_delete_is_restricted_when_demo_run_references_user(
    db_session: Session,
) -> None:
    user = _user(db_session)
    _run(db_session, user.user_id)

    _expect_statement_integrity_error(
        db_session,
        text("DELETE FROM users WHERE user_id = :user_id"),
        {"user_id": user.user_id},
    )


def test_demo_run_delete_is_restricted_when_reading_references_run(
    db_session: Session,
) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    db_session.add(
        _reading(
            user.user_id,
            demo_run_id=run.demo_run_id,
            run_generation=run.current_generation,
        )
    )
    db_session.flush()

    _expect_statement_integrity_error(
        db_session,
        text("DELETE FROM demo_runs WHERE demo_run_id = :demo_run_id"),
        {"demo_run_id": run.demo_run_id},
    )


def test_incident_delete_is_restricted_when_timeline_event_references_incident(
    db_session: Session,
) -> None:
    user = _user(db_session)
    incident = _incident(user.user_id)
    db_session.add(incident)
    db_session.flush()
    db_session.add(
        IncidentTimelineEvent(
            timeline_event_id=uuid4(),
            incident_id=incident.incident_id,
            event_type="TEST_EVENT",
            occurred_at=_now(),
            actor_user_id=None,
            event_idempotency_key=str(uuid4()),
            details=None,
        )
    )
    db_session.flush()

    _expect_statement_integrity_error(
        db_session,
        text("DELETE FROM incidents WHERE incident_id = :incident_id"),
        {"incident_id": incident.incident_id},
    )


def test_anomaly_delete_is_restricted_when_evidence_link_references_event(
    db_session: Session,
) -> None:
    user = _user(db_session)
    run = _run(db_session, user.user_id)
    anomaly = _anomaly(user.user_id, run.demo_run_id)
    incident = _incident(
        user.user_id,
        demo_run_id=run.demo_run_id,
        run_generation=run.current_generation,
    )
    db_session.add_all([anomaly, incident])
    db_session.flush()
    db_session.add(
        IncidentAnomalyEvent(
            incident_id=incident.incident_id,
            anomaly_event_id=anomaly.anomaly_event_id,
            subject_user_id=user.user_id,
            demo_run_id=run.demo_run_id,
            evidence_role="SUPPORTING",
            associated_at=_now(),
        )
    )
    db_session.flush()

    _expect_statement_integrity_error(
        db_session,
        text("DELETE FROM anomaly_events WHERE anomaly_event_id = :event_id"),
        {"event_id": anomaly.anomaly_event_id},
    )
