"""Transactional incident, verification, and escalation orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.clock import utc_now
from backend.app.models.demo import DemoRun
from backend.app.models.incidents import (
    EscalationAttempt,
    Incident,
    IncidentAnomalyEvent,
    IncidentTimelineEvent,
    VerificationResponse,
)
from backend.app.models.readings import AnomalyEvent
from backend.app.schemas.incidents import (
    IncidentStatus,
    IncidentTransition,
    NotificationResultStatus,
    VerificationResponseValue,
)
from backend.app.services.incident_lifecycle import (
    transition_incident,
)


class IncidentServiceError(RuntimeError):
    """Base error for rejected incident operations."""


class StaleDemoGeneration(IncidentServiceError):
    """The request belongs to a reset or superseded demo generation."""


class VerificationExpired(IncidentServiceError):
    """The response arrived at or after the persisted deadline."""


class IncidentNotAwaitingVerification(IncidentServiceError):
    """The incident cannot accept a verification response."""


def _as_utc(value: datetime) -> datetime:
    """Normalize aware values and treat legacy naive DB values as UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _lock_run(session: Session, demo_run_id: UUID, subject_user_id: UUID) -> DemoRun:
    run = session.scalar(
        select(DemoRun)
        .where(
            DemoRun.demo_run_id == demo_run_id,
            DemoRun.subject_user_id == subject_user_id,
        )
        .with_for_update()
    )
    if run is None:
        raise IncidentServiceError("demo run was not found")
    return run


def _assert_fresh_run(run: DemoRun, generation: int) -> None:
    if run.reset_at is not None or run.current_generation != generation:
        raise StaleDemoGeneration("demo work belongs to a stale generation")


def _timeline(
    session: Session,
    *,
    incident_id: UUID,
    event_type: str,
    occurred_at: datetime,
    event_idempotency_key: str,
    actor_user_id: UUID | None = None,
) -> None:
    session.add(
        IncidentTimelineEvent(
            timeline_event_id=uuid4(),
            incident_id=incident_id,
            event_type=event_type,
            occurred_at=occurred_at,
            actor_user_id=actor_user_id,
            event_idempotency_key=event_idempotency_key,
        )
    )


def create_incident_for_anomaly(
    session: Session,
    *,
    anomaly_event_id: UUID,
    verification_deadline_at: datetime,
    creation_idempotency_key: str,
    now: datetime | None = None,
) -> Incident:
    """Create one pending incident for an anomaly in one caller transaction.

    The caller owns commit/rollback. The demo-run row is locked before any
    run-scoped child write, preventing reset/worker races.
    """

    current_time = _as_utc(now or utc_now())
    verification_deadline_at = _as_utc(verification_deadline_at)
    anomaly = session.get(AnomalyEvent, anomaly_event_id, with_for_update=True)
    if anomaly is None:
        raise IncidentServiceError("anomaly event was not found")
    run = _lock_run(session, anomaly.demo_run_id, anomaly.subject_user_id)
    _assert_fresh_run(run, anomaly.run_generation)

    existing = session.scalar(
        select(Incident).where(
            Incident.subject_user_id == anomaly.subject_user_id,
            Incident.creation_idempotency_key == creation_idempotency_key,
        )
    )
    if existing is not None:
        return existing

    existing_trigger = session.scalar(
        select(Incident).where(
            Incident.subject_user_id == anomaly.subject_user_id,
            Incident.demo_run_id == anomaly.demo_run_id,
            Incident.triggering_anomaly_event_id == anomaly.anomaly_event_id,
        )
    )
    if existing_trigger is not None:
        return existing_trigger

    incident = Incident(
        incident_id=uuid4(),
        subject_user_id=anomaly.subject_user_id,
        demo_run_id=anomaly.demo_run_id,
        run_generation=anomaly.run_generation,
        triggering_anomaly_event_id=anomaly.anomaly_event_id,
        status=IncidentStatus.PENDING_VERIFICATION.value,
        creation_idempotency_key=creation_idempotency_key,
        created_at=current_time,
        updated_at=current_time,
        verification_deadline_at=verification_deadline_at,
    )
    session.add(incident)
    session.add(
        IncidentAnomalyEvent(
            incident_id=incident.incident_id,
            anomaly_event_id=anomaly.anomaly_event_id,
            subject_user_id=anomaly.subject_user_id,
            demo_run_id=anomaly.demo_run_id,
            evidence_role="TRIGGERING",
            associated_at=current_time,
        )
    )
    _timeline(
        session,
        incident_id=incident.incident_id,
        event_type="INCIDENT_CREATED",
        occurred_at=current_time,
        event_idempotency_key=f"incident-created:{creation_idempotency_key}",
    )
    return incident


def record_verification_response(
    session: Session,
    *,
    incident_id: UUID,
    responder_user_id: UUID,
    response_value: VerificationResponseValue,
    idempotency_key: str,
    request_reference: str | None = None,
    now: datetime | None = None,
) -> Incident:
    """Record `I_AM_OK` and resolve a pending incident atomically."""

    current_time = _as_utc(now or utc_now())
    incident = session.scalar(
        select(Incident).where(Incident.incident_id == incident_id).with_for_update()
    )
    if incident is None:
        raise IncidentServiceError("incident was not found")

    duplicate = session.scalar(
        select(VerificationResponse).where(
            VerificationResponse.incident_id == incident_id,
            VerificationResponse.idempotency_key == idempotency_key,
        )
    )
    if duplicate is not None:
        return incident

    if incident.status != IncidentStatus.PENDING_VERIFICATION.value:
        raise IncidentNotAwaitingVerification("incident is not awaiting verification")
    if incident.verification_deadline_at is not None and current_time >= _as_utc(
        incident.verification_deadline_at
    ):
        raise VerificationExpired("verification deadline has elapsed")

    transition_incident(
        IncidentStatus(incident.status),
        IncidentTransition.I_AM_OK,
    )
    session.add(
        VerificationResponse(
            verification_response_id=uuid4(),
            incident_id=incident_id,
            responder_user_id=responder_user_id,
            response_value=response_value.value,
            idempotency_key=idempotency_key,
            responded_at=current_time,
            request_reference=request_reference,
        )
    )
    incident.status = IncidentStatus.RESOLVED_FALSE_ALARM.value
    incident.updated_at = current_time
    incident.resolved_at = current_time
    _timeline(
        session,
        incident_id=incident_id,
        event_type="VERIFICATION_ACCEPTED",
        occurred_at=current_time,
        event_idempotency_key=f"verification:{idempotency_key}",
        actor_user_id=responder_user_id,
    )
    return incident


def begin_timeout_escalation(
    session: Session,
    *,
    incident_id: UUID,
    idempotency_key: str,
    now: datetime | None = None,
) -> EscalationAttempt:
    """Persist escalation intent after a confirmed verification timeout."""

    current_time = _as_utc(now or utc_now())
    incident = session.scalar(
        select(Incident).where(Incident.incident_id == incident_id).with_for_update()
    )
    if incident is None:
        raise IncidentServiceError("incident was not found")

    existing = session.scalar(
        select(EscalationAttempt).where(
            EscalationAttempt.incident_id == incident_id,
            EscalationAttempt.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing

    if incident.status != IncidentStatus.PENDING_VERIFICATION.value:
        raise IncidentServiceError("incident is not pending verification")
    if incident.verification_deadline_at is None or current_time < _as_utc(
        incident.verification_deadline_at
    ):
        raise IncidentServiceError("verification deadline has not elapsed")

    transition_incident(
        IncidentStatus(incident.status),
        IncidentTransition.VERIFICATION_TIMEOUT,
    )
    attempt = EscalationAttempt(
        escalation_attempt_id=uuid4(),
        incident_id=incident_id,
        trigger_reason="VERIFICATION_TIMEOUT",
        status="PENDING",
        started_at=current_time,
        idempotency_key=idempotency_key,
    )
    session.add(attempt)
    incident.status = IncidentStatus.ESCALATION_IN_PROGRESS.value
    incident.updated_at = current_time
    _timeline(
        session,
        incident_id=incident_id,
        event_type="ESCALATION_STARTED",
        occurred_at=current_time,
        event_idempotency_key=f"escalation-started:{idempotency_key}",
    )
    return attempt


def complete_escalation(
    session: Session,
    *,
    incident_id: UUID,
    escalation_attempt_id: UUID,
    result: NotificationResultStatus,
    completed_at: datetime | None = None,
) -> Incident:
    """Apply a notifier result after the external call has completed."""

    current_time = _as_utc(completed_at or utc_now())
    incident = session.scalar(
        select(Incident).where(Incident.incident_id == incident_id).with_for_update()
    )
    if incident is None:
        raise IncidentServiceError("incident was not found")
    attempt = session.scalar(
        select(EscalationAttempt)
        .where(
            EscalationAttempt.escalation_attempt_id == escalation_attempt_id,
            EscalationAttempt.incident_id == incident_id,
        )
        .with_for_update()
    )
    if attempt is None:
        raise IncidentServiceError("escalation attempt was not found")

    if attempt.completed_at is not None:
        return incident
    if incident.status != IncidentStatus.ESCALATION_IN_PROGRESS.value:
        raise IncidentServiceError("incident is not being escalated")

    attempt.status = result.value
    attempt.completed_at = current_time
    incident.updated_at = current_time
    if result in {
        NotificationResultStatus.ACCEPTED,
        NotificationResultStatus.DELIVERED,
    }:
        transition_incident(
            IncidentStatus(incident.status),
            IncidentTransition.ESCALATION_SUCCEEDED,
        )
        incident.status = IncidentStatus.ESCALATED.value
        _timeline(
            session,
            incident_id=incident_id,
            event_type="ESCALATION_COMPLETED",
            occurred_at=current_time,
            event_idempotency_key=f"escalation-completed:{escalation_attempt_id}",
        )
    else:
        _timeline(
            session,
            incident_id=incident_id,
            event_type="ESCALATION_FAILED",
            occurred_at=current_time,
            event_idempotency_key=f"escalation-result:{escalation_attempt_id}",
        )
    return incident


def find_expired_pending_incidents(
    session: Session,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> list[UUID]:
    """Return a bounded batch of incident IDs eligible for timeout handling."""

    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    current_time = _as_utc(now or utc_now())
    rows = session.scalars(
        select(Incident.incident_id)
        .where(
            Incident.status == IncidentStatus.PENDING_VERIFICATION.value,
            Incident.verification_deadline_at.is_not(None),
            Incident.verification_deadline_at <= current_time,
        )
        .order_by(Incident.verification_deadline_at, Incident.incident_id)
        .limit(limit)
    )
    return list(rows)
