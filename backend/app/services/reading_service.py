"""Transactional reading persistence and detector-event creation."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.demo import DemoRun
from backend.app.models.readings import AnomalyEvent, HealthReading
from backend.app.services.detector_adapter import (
    DetectorResult,
    canonical_dedupe_key,
    detector_result_value,
)


class DetectorUnavailable(RuntimeError):
    """No authoritative detector provider has been registered."""


class StaleReadingRun(RuntimeError):
    """The reading belongs to a reset or superseded generation."""


def persist_reading(
    session: Session,
    *,
    subject_user_id: UUID,
    demo_run_id: UUID,
    heart_rate_bpm: int,
    observed_at: datetime,
    source_kind: str,
    activity_context: str | None,
    source_record_id: str | None,
    ingestion_idempotency_key: str,
    detector_result: DetectorResult | None,
) -> tuple[HealthReading, AnomalyEvent | None]:
    run = session.scalar(
        select(DemoRun)
        .where(
            DemoRun.demo_run_id == demo_run_id,
            DemoRun.subject_user_id == subject_user_id,
        )
        .with_for_update()
    )
    if run is None:
        raise ValueError("demo run was not found")
    existing = session.scalar(
        select(HealthReading).where(
            HealthReading.subject_user_id == subject_user_id,
            HealthReading.ingestion_idempotency_key == ingestion_idempotency_key,
        )
    )
    if existing is not None:
        # Replay the original detector outcome for an idempotent retry. The
        # detector emits an event at the timestamp of the sample that
        # completed the anomaly episode, so this lookup recovers the same
        # event without feeding the duplicate sample into the stateful
        # detector again.
        existing_event = session.scalar(
            select(AnomalyEvent)
            .where(
                AnomalyEvent.subject_user_id == existing.subject_user_id,
                AnomalyEvent.demo_run_id == existing.demo_run_id,
                AnomalyEvent.run_generation == existing.run_generation,
                AnomalyEvent.detected_at == existing.observed_at,
            )
            .order_by(AnomalyEvent.detected_at.asc())
        )
        return existing, existing_event
    now = datetime.now(UTC)
    reading = HealthReading(
        reading_id=uuid4(),
        subject_user_id=subject_user_id,
        demo_run_id=demo_run_id,
        run_generation=run.current_generation,
        source_kind=source_kind,
        heart_rate_bpm=heart_rate_bpm,
        observed_at=observed_at.astimezone(UTC),
        received_at=now,
        activity_context=activity_context,
        source_record_id=source_record_id,
        ingestion_idempotency_key=ingestion_idempotency_key,
    )
    session.add(reading)
    if (
        detector_result is None
        or detector_result_value(detector_result.anomaly_kind) is None
    ):
        return reading, None
    event = AnomalyEvent(
        anomaly_event_id=uuid4(),
        subject_user_id=subject_user_id,
        demo_run_id=demo_run_id,
        run_generation=run.current_generation,
        detected_at=detector_result.detected_at.astimezone(UTC),
        detector_result=detector_result_value(detector_result.anomaly_kind),
        severity=detector_result.severity,
        explanation=detector_result.explanation,
        detector_version=detector_result.detector_version,
        dedupe_key=canonical_dedupe_key(
            subject_user_id=str(subject_user_id),
            demo_run_id=str(demo_run_id),
            run_generation=run.current_generation,
            result=detector_result,
        ),
    )
    session.add(event)
    return reading, event
