from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from backend.app.services.location import (
    LocationService,
    LocationUpdateRejected,
    LocationUpdateRequest,
    SeededHospitalDirectory,
    haversine_distance_meters,
)
from pydantic import ValidationError


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


def make_update(
    *,
    captured_at: datetime,
    subject_user_id=None,
    incident_id=None,
    latitude: float = 18.5204,
    longitude: float = 73.8567,
    source_kind: str = "simulated",
) -> LocationUpdateRequest:
    return LocationUpdateRequest(
        subject_user_id=subject_user_id or uuid4(),
        incident_id=incident_id,
        latitude=latitude,
        longitude=longitude,
        accuracy_meters=12.5,
        captured_at=captured_at,
        source_kind=source_kind,
    )


def test_latest_location_is_available_by_subject_and_incident() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(now)
    service = LocationService(clock=clock)
    subject_user_id = uuid4()
    incident_id = uuid4()
    update = make_update(
        captured_at=now - timedelta(seconds=10),
        subject_user_id=subject_user_id,
        incident_id=incident_id,
    )

    created = service.record_location(update)

    assert created.subject_user_id == subject_user_id
    assert created.incident_id == incident_id
    assert created.source_kind == "SIMULATED"
    assert created.accuracy_meters == 12.5
    assert created.is_stale is False
    assert created.stale_after_seconds == 300

    by_subject = service.latest_for_subject(subject_user_id)
    by_incident = service.latest_for_incident(incident_id)

    assert by_subject is not None
    assert by_incident is not None
    assert by_subject.location_snapshot_id == created.location_snapshot_id
    assert by_incident.location_snapshot_id == created.location_snapshot_id


def test_location_becomes_stale_after_the_configured_window() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(now)
    service = LocationService(clock=clock, stale_after_seconds=300)
    subject_user_id = uuid4()
    service.record_location(
        make_update(captured_at=now, subject_user_id=subject_user_id)
    )

    clock.advance(301)
    snapshot = service.latest_for_subject(subject_user_id)

    assert snapshot is not None
    assert snapshot.is_stale is True


def test_non_credible_future_timestamp_is_rejected() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(now)
    service = LocationService(clock=clock)
    subject_user_id = uuid4()
    update = make_update(
        captured_at=now + timedelta(seconds=121),
        subject_user_id=subject_user_id,
    )

    with pytest.raises(LocationUpdateRejected):
        service.record_location(update)

    assert service.latest_for_subject(subject_user_id) is None


def test_naive_capture_time_is_rejected() -> None:
    with pytest.raises(ValidationError):
        LocationUpdateRequest(
            subject_user_id=uuid4(),
            latitude=18.5204,
            longitude=73.8567,
            captured_at=datetime(2026, 1, 1, 12, 0),
        )


def test_location_store_is_bounded() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(now)
    service = LocationService(clock=clock, max_location_entries=2)
    subjects = [uuid4() for _ in range(3)]

    for index, subject_user_id in enumerate(subjects):
        clock.value = now + timedelta(seconds=index)
        service.record_location(
            make_update(
                captured_at=clock.value,
                subject_user_id=subject_user_id,
            )
        )

    assert service.latest_for_subject(subjects[0]) is None
    assert service.latest_for_subject(subjects[1]) is not None
    assert service.latest_for_subject(subjects[2]) is not None


def test_seeded_hospitals_are_sorted_limited_and_labelled() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(now)
    service = LocationService(clock=clock)

    result = service.nearby_hospitals(18.5204, 73.8567, limit=2)

    assert len(result.hospitals) == 2
    assert result.provider == "SEEDED_DEMO_DIRECTORY"
    assert "No hospital has been contacted" in result.disclaimer
    assert result.hospitals[0].distance_meters <= result.hospitals[1].distance_meters
    assert all(hospital.source_kind == "SEEDED_DEMO" for hospital in result.hospitals)
    assert result.generated_at == now


def test_empty_hospital_directory_returns_no_results() -> None:
    class EmptyDirectory:
        provider_name = "EMPTY_DEMO_DIRECTORY"
        disclaimer = "No demonstration hospitals are configured."

        def list_hospitals(self):
            return ()

    service = LocationService(EmptyDirectory())

    result = service.nearby_hospitals(18.5204, 73.8567)

    assert result.hospitals == []
    assert result.provider == "EMPTY_DEMO_DIRECTORY"


def test_haversine_distance_is_zero_for_the_same_point() -> None:
    assert haversine_distance_meters(18.5204, 73.8567, 18.5204, 73.8567) == 0.0
    assert 0 < haversine_distance_meters(18.5204, 73.8567, 18.5679, 73.8730) < 10_000


def test_default_seeded_directory_is_fictional_demo_data() -> None:
    hospitals = SeededHospitalDirectory().list_hospitals()

    assert len(hospitals) >= 1
    assert all("Demo" in hospital.name for hospital in hospitals)
    assert all(hospital.source_kind == "SEEDED_DEMO" for hospital in hospitals)
