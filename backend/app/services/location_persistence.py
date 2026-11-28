"""PostgreSQL persistence repository for location snapshots."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.demo import DemoRun
from backend.app.models.incidents import Incident
from backend.app.models.location import LocationSnapshotRecord
from backend.app.services.location import (
    DEFAULT_STALE_AFTER_SECONDS,
    LocationSnapshot,
    LocationUpdateRequest,
)

__all__ = [
    "DemoRunNotFoundError",
    "IncidentNotFoundError",
    "LocationPersistenceError",
    "get_latest_location_record_for_incident",
    "get_latest_location_record_for_subject",
    "persist_location_snapshot",
    "snapshot_record_to_schema",
]


class LocationPersistenceError(ValueError):
    """Base error for location persistence rejections."""


class DemoRunNotFoundError(LocationPersistenceError):
    """Raised when the referenced demo run does not exist or does not match subject."""


class IncidentNotFoundError(LocationPersistenceError):
    """Raised when the referenced incident does not exist or does not match subject/run."""


def persist_location_snapshot(
    session: Session,
    *,
    update: LocationUpdateRequest,
    location_snapshot_id: UUID | None = None,
    received_at: datetime | None = None,
) -> LocationSnapshotRecord:
    """Persist an authorized location snapshot to PostgreSQL.

    Preserves the caller's snapshot ID and received_at timestamp if provided
    (such as from LocationService.record_location), or generates them if omitted.
    Resolves DemoRun.current_generation when demo_run_id is supplied to satisfy
    schema constraints. When incident_id is supplied and demo_run_id is omitted,
    derives the associated demo run and generation from the authoritative
    incident record. Does not commit or close the caller's session.
    """
    now = datetime.now(UTC)
    effective_snapshot_id = location_snapshot_id or uuid4()
    effective_received_at = received_at or now
    if effective_received_at.tzinfo is None:
        effective_received_at = effective_received_at.replace(tzinfo=UTC)
    else:
        effective_received_at = effective_received_at.astimezone(UTC)

    captured_at = update.captured_at
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=UTC)
    else:
        captured_at = captured_at.astimezone(UTC)

    effective_demo_run_id: UUID | None = update.demo_run_id
    run_generation: int | None = None
    if effective_demo_run_id is not None:
        demo_run = session.scalar(
            select(DemoRun).where(
                DemoRun.demo_run_id == effective_demo_run_id,
                DemoRun.subject_user_id == update.subject_user_id,
            )
        )
        if demo_run is None:
            raise DemoRunNotFoundError(
                f"Demo run {effective_demo_run_id} not found for subject {update.subject_user_id}"
            )
        run_generation = demo_run.current_generation

    if update.incident_id is not None:
        incident = session.scalar(
            select(Incident).where(
                Incident.incident_id == update.incident_id,
                Incident.subject_user_id == update.subject_user_id,
            )
        )
        if incident is None:
            raise IncidentNotFoundError(
                f"Incident {update.incident_id} not found for subject {update.subject_user_id}"
            )
        if effective_demo_run_id is not None:
            if (
                incident.demo_run_id is not None
                and incident.demo_run_id != effective_demo_run_id
            ):
                raise IncidentNotFoundError(
                    f"Incident {update.incident_id} belongs to demo run {incident.demo_run_id}, not {effective_demo_run_id}"
                )
        elif incident.demo_run_id is not None:
            effective_demo_run_id = incident.demo_run_id
            if incident.run_generation is not None:
                run_generation = incident.run_generation
            else:
                demo_run = session.scalar(
                    select(DemoRun).where(
                        DemoRun.demo_run_id == incident.demo_run_id,
                        DemoRun.subject_user_id == update.subject_user_id,
                    )
                )
                run_generation = demo_run.current_generation if demo_run else None

    record = LocationSnapshotRecord(
        location_id=effective_snapshot_id,
        subject_user_id=update.subject_user_id,
        incident_id=update.incident_id,
        demo_run_id=effective_demo_run_id,
        run_generation=run_generation,
        latitude=update.latitude,
        longitude=update.longitude,
        accuracy_meters=update.accuracy_meters,
        source_kind=update.source_kind,
        captured_at=captured_at,
        received_at=effective_received_at,
    )
    session.add(record)
    session.flush()
    return record


def get_latest_location_record_for_subject(
    session: Session,
    subject_user_id: UUID,
) -> LocationSnapshotRecord | None:
    """Fetch the latest location snapshot for a subject ordered by captured_at and received_at."""
    stmt = (
        select(LocationSnapshotRecord)
        .where(LocationSnapshotRecord.subject_user_id == subject_user_id)
        .order_by(
            LocationSnapshotRecord.captured_at.desc(),
            LocationSnapshotRecord.received_at.desc(),
        )
        .limit(1)
    )
    return session.scalar(stmt)


def get_latest_location_record_for_incident(
    session: Session,
    incident_id: UUID,
) -> LocationSnapshotRecord | None:
    """Fetch the latest location snapshot for an incident ordered by captured_at and received_at."""
    stmt = (
        select(LocationSnapshotRecord)
        .where(LocationSnapshotRecord.incident_id == incident_id)
        .order_by(
            LocationSnapshotRecord.captured_at.desc(),
            LocationSnapshotRecord.received_at.desc(),
        )
        .limit(1)
    )
    return session.scalar(stmt)


def snapshot_record_to_schema(
    record: LocationSnapshotRecord,
    *,
    now: datetime | None = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> LocationSnapshot:
    """Convert an ORM LocationSnapshotRecord into the Pydantic LocationSnapshot schema."""
    reference_now = now or datetime.now(UTC)
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=UTC)
    else:
        reference_now = reference_now.astimezone(UTC)

    captured_at = record.captured_at
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=UTC)
    else:
        captured_at = captured_at.astimezone(UTC)

    received_at = record.received_at
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=UTC)
    else:
        received_at = received_at.astimezone(UTC)

    age = reference_now - captured_at
    is_stale = age > timedelta(seconds=stale_after_seconds)

    return LocationSnapshot(
        location_snapshot_id=record.location_id,
        subject_user_id=record.subject_user_id,
        incident_id=record.incident_id,
        demo_run_id=record.demo_run_id,
        latitude=record.latitude,
        longitude=record.longitude,
        accuracy_meters=record.accuracy_meters,
        captured_at=captured_at,
        received_at=received_at,
        source_kind=record.source_kind,
        is_stale=is_stale,
        stale_after_seconds=stale_after_seconds,
    )
