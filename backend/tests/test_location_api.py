from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from backend.app.api.location import get_location_service, router
from backend.app.core.auth import require_active_principal
from backend.app.db.session import get_db
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from backend.app.services.location import LocationService
from fastapi import FastAPI
from fastapi.testclient import TestClient

SUBJECT_USER_ID = uuid4()


class FakeLocationSession:
    def get(self, _model, _identifier):
        return type("OwnedRecord", (), {"subject_user_id": SUBJECT_USER_ID})()


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


class FailingHospitalDirectory:
    provider_name = "FAILING_DEMO_DIRECTORY"
    disclaimer = "Demo directory unavailable."

    def list_hospitals(self):
        raise RuntimeError("directory unavailable")


@pytest.fixture
def location_context():
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    service = LocationService(clock=clock)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_location_service] = lambda: service
    app.dependency_overrides[require_active_principal] = lambda: AuthenticatedPrincipal(
        user_id=SUBJECT_USER_ID, role=UserRole.SUBJECT
    )
    app.dependency_overrides[get_db] = FakeLocationSession
    with TestClient(app) as client:
        yield client, service, clock


def test_submit_and_retrieve_latest_location(location_context) -> None:
    client, _service, _clock = location_context
    subject_user_id = SUBJECT_USER_ID
    incident_id = uuid4()

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(subject_user_id),
            "incident_id": str(incident_id),
            "latitude": 18.5204,
            "longitude": 73.8567,
            "accuracy_meters": 9.5,
            "captured_at": "2026-01-01T11:59:30Z",
            "source_kind": "simulated",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["subject_user_id"] == str(subject_user_id)
    assert created["incident_id"] == str(incident_id)
    assert created["source_kind"] == "SIMULATED"
    assert created["is_stale"] is False
    assert created["stale_after_seconds"] == 300

    by_subject = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(subject_user_id)},
    )
    by_incident = client.get(
        "/api/v1/location/latest",
        params={"incident_id": str(incident_id)},
    )

    assert by_subject.status_code == 200
    assert by_incident.status_code == 200
    assert by_subject.json()["location_snapshot_id"] == created["location_snapshot_id"]
    assert by_incident.json()["location_snapshot_id"] == created["location_snapshot_id"]


def test_latest_location_missing_returns_error_envelope(location_context) -> None:
    client, _service, _clock = location_context

    response = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(SUBJECT_USER_ID)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "LOCATION_NOT_AVAILABLE"


def test_latest_location_requires_exactly_one_selector(location_context) -> None:
    client, _service, _clock = location_context
    subject_user_id = SUBJECT_USER_ID

    missing = client.get("/api/v1/location/latest")
    ambiguous = client.get(
        "/api/v1/location/latest",
        params={
            "subject_user_id": str(subject_user_id),
            "incident_id": str(uuid4()),
        },
    )

    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "LOCATION_QUERY_INVALID"
    assert ambiguous.status_code == 400
    assert ambiguous.json()["error"]["code"] == "LOCATION_QUERY_INVALID"


def test_future_capture_time_returns_custom_error(location_context) -> None:
    client, _service, clock = location_context
    captured_at = clock.value + timedelta(minutes=10)

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "latitude": 18.5204,
            "longitude": 73.8567,
            "captured_at": captured_at.isoformat(),
            "source_kind": "SIMULATED",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_LOCATION_TIMESTAMP"


def test_location_input_is_validated(location_context) -> None:
    client, _service, _clock = location_context

    invalid_coordinates = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "latitude": 91,
            "longitude": 73.8567,
            "captured_at": "2026-01-01T11:59:30Z",
        },
    )
    missing_timezone = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "latitude": 18.5204,
            "longitude": 73.8567,
            "captured_at": "2026-01-01T11:59:30",
        },
    )

    assert invalid_coordinates.status_code == 422
    assert missing_timezone.status_code == 422


def test_nearby_hospitals_are_bounded_and_labelled(location_context) -> None:
    client, _service, _clock = location_context

    response = client.get(
        "/api/v1/hospitals/nearby",
        params={"latitude": 18.5204, "longitude": 73.8567, "limit": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["hospitals"]) == 2
    assert body["provider"] == "SEEDED_DEMO_DIRECTORY"
    assert "No hospital has been contacted" in body["disclaimer"]
    assert (
        body["hospitals"][0]["distance_meters"]
        <= body["hospitals"][1]["distance_meters"]
    )
    assert all(
        hospital["source_kind"] == "SEEDED_DEMO" for hospital in body["hospitals"]
    )


def test_nearby_hospitals_reject_out_of_range_limit(location_context) -> None:
    client, _service, _clock = location_context

    response = client.get(
        "/api/v1/hospitals/nearby",
        params={"latitude": 18.5204, "longitude": 73.8567, "limit": 11},
    )

    assert response.status_code == 422


def test_hospital_directory_failure_returns_503() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    service = LocationService(FailingHospitalDirectory(), clock=clock)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_location_service] = lambda: service
    app.dependency_overrides[require_active_principal] = lambda: AuthenticatedPrincipal(
        user_id=SUBJECT_USER_ID, role=UserRole.SUBJECT
    )
    app.dependency_overrides[get_db] = FakeLocationSession

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/hospitals/nearby",
            params={"latitude": 18.5204, "longitude": 73.8567},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "HOSPITAL_DIRECTORY_UNAVAILABLE"
