from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from backend.app.api.location import get_location_service, router
from backend.app.core.auth import require_active_principal
from backend.app.db.session import get_db
from backend.app.models.auth import CaregiverAuthorization
from backend.app.models.location import LocationSnapshotRecord
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from backend.app.services.location import (
    LocationService,
    LocationUpdateRequest,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

SUBJECT_USER_ID = uuid4()


class FakeLocationSession:
    def __init__(
        self,
        *,
        fail_on_flush: bool = False,
        fail_on_commit: bool = False,
        missing_demo_run: bool = False,
        missing_incident: bool = False,
        incident_demo_run_id: UUID | None = None,
        incident_run_generation: int | None = None,
    ) -> None:
        self.committed = False
        self.rolled_back = False
        self.added: list[object] = []
        self.location_records: list[LocationSnapshotRecord] = []
        self.fail_on_flush = fail_on_flush
        self.fail_on_commit = fail_on_commit
        self.missing_demo_run = missing_demo_run
        self.missing_incident = missing_incident
        self.incident_demo_run_id = incident_demo_run_id
        self.incident_run_generation = incident_run_generation
        self.scalar_query_count = 0

    def get(self, _model, _identifier):
        return type(
            "OwnedRecord",
            (),
            {
                "subject_user_id": SUBJECT_USER_ID,
                "demo_run_id": self.incident_demo_run_id,
                "run_generation": self.incident_run_generation,
            },
        )()

    def scalar(self, stmt):
        self.scalar_query_count += 1
        for desc in getattr(stmt, "column_descriptions", []):
            entity = desc.get("entity") or desc.get("type")
            if entity is LocationSnapshotRecord:
                return self.location_records[-1] if self.location_records else None
            if entity is CaregiverAuthorization:
                return None
            type_name = str(entity)
            if (
                "demo_runs" in type_name or "DemoRun" in type_name
            ) and self.missing_demo_run:
                return None
            if (
                "incidents" in type_name or "Incident" in type_name
            ) and self.missing_incident:
                return None
        return type(
            "OwnedRecord",
            (),
            {
                "subject_user_id": SUBJECT_USER_ID,
                "current_generation": 1,
                "demo_run_id": self.incident_demo_run_id,
                "run_generation": self.incident_run_generation,
                "incident_id": uuid4(),
            },
        )()

    def add(self, obj: object) -> None:
        self.added.append(obj)
        if isinstance(obj, LocationSnapshotRecord):
            self.location_records.append(obj)

    def flush(self) -> None:
        if self.fail_on_flush:
            raise RuntimeError("Simulated DB flush error")

    def commit(self) -> None:
        if self.fail_on_commit:
            raise RuntimeError("Simulated DB commit error")
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


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


# ---------------------------------------------------------------------------
# Focused PostgreSQL Location Persistence & Read-Through Tests
# ---------------------------------------------------------------------------


def _build_test_client(
    service: LocationService | None = None,
    session: FakeLocationSession | None = None,
    principal: AuthenticatedPrincipal | None = None,
) -> tuple[TestClient, LocationService, FakeLocationSession]:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    svc = service or LocationService(clock=clock)
    sess = session or FakeLocationSession()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_location_service] = lambda: svc
    app.dependency_overrides[require_active_principal] = lambda: (
        principal
        or AuthenticatedPrincipal(user_id=SUBJECT_USER_ID, role=UserRole.SUBJECT)
    )
    app.dependency_overrides[get_db] = lambda: sess
    return TestClient(app), svc, sess


def test_successful_update_shares_uuid_and_timestamp_and_commits() -> None:
    client, service, session = _build_test_client()
    incident_id = uuid4()

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "incident_id": str(incident_id),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accuracy_meters": 10.0,
            "captured_at": "2026-01-01T11:59:00Z",
            "source_kind": "GPS",
        },
    )

    assert response.status_code == 201
    body = response.json()

    # 1. Assert DB transaction was committed and record added
    assert session.committed is True
    assert session.rolled_back is False
    assert len(session.location_records) == 1
    db_record = session.location_records[0]

    # 2. Assert exact snapshot UUID and received_at are shared
    assert body["location_snapshot_id"] == str(db_record.location_id)
    assert datetime.fromisoformat(body["received_at"]) == db_record.received_at

    # 3. Assert in-memory cache was published with the exact same snapshot
    cached = service.latest_for_subject(SUBJECT_USER_ID)
    assert cached is not None
    assert str(cached.location_snapshot_id) == body["location_snapshot_id"]
    assert cached.received_at == db_record.received_at


def test_location_update_with_incident_derives_demo_run_id_in_response_and_cache() -> (
    None
):
    expected_run_id = uuid4()
    incident_id = uuid4()
    session = FakeLocationSession(
        incident_demo_run_id=expected_run_id,
        incident_run_generation=3,
    )
    client, service, _ = _build_test_client(session=session)

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "incident_id": str(incident_id),
            "latitude": 18.5204,
            "longitude": 73.8567,
            "captured_at": "2026-01-01T11:59:00Z",
            "source_kind": "INCIDENT_UPDATE",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["demo_run_id"] == str(expected_run_id)
    assert body["incident_id"] == str(incident_id)

    # Assert cache contains the derived demo_run_id
    cached_subj = service.latest_for_subject(SUBJECT_USER_ID)
    assert cached_subj is not None
    assert cached_subj.demo_run_id == expected_run_id

    cached_inc = service.latest_for_incident(incident_id)
    assert cached_inc is not None
    assert cached_inc.demo_run_id == expected_run_id

    # Assert database record contains the derived demo_run_id and run_generation
    assert len(session.location_records) == 1
    db_rec = session.location_records[0]
    assert db_rec.demo_run_id == expected_run_id
    assert db_rec.run_generation == 3


def test_persistence_failure_on_flush_rolls_back_and_leaves_cache_unmodified() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    service = LocationService(clock=clock)

    # Pre-populate cache with an initial snapshot
    initial_update = LocationUpdateRequest(
        subject_user_id=SUBJECT_USER_ID,
        latitude=10.0,
        longitude=10.0,
        captured_at=datetime(2026, 1, 1, 11, 50, tzinfo=UTC),
        source_kind="INITIAL",
    )
    initial_snap = service.record_location(initial_update)

    session = FakeLocationSession(fail_on_flush=True)
    client, _, _ = _build_test_client(service=service, session=session)

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "latitude": 20.0,
            "longitude": 20.0,
            "captured_at": "2026-01-01T11:59:00Z",
            "source_kind": "NEW_FAILED",
        },
    )

    # Assert HTTP 500 with generic error envelope (no internal exception leakage)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "LOCATION_PERSISTENCE_FAILED"
    assert "Simulated DB flush error" not in response.text

    # Assert rollback occurred
    assert session.rolled_back is True
    assert session.committed is False

    # Assert cache was NOT updated; initial snapshot remains intact
    cached = service.latest_for_subject(SUBJECT_USER_ID)
    assert cached is not None
    assert cached.location_snapshot_id == initial_snap.location_snapshot_id
    assert cached.source_kind == "INITIAL"


def test_persistence_failure_on_commit_rolls_back_and_leaves_cache_unmodified() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    service = LocationService(clock=clock)

    session = FakeLocationSession(fail_on_commit=True)
    client, _, _ = _build_test_client(service=service, session=session)

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "latitude": 25.0,
            "longitude": 25.0,
            "captured_at": "2026-01-01T11:59:00Z",
            "source_kind": "COMMIT_FAIL",
        },
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "LOCATION_PERSISTENCE_FAILED"
    assert session.rolled_back is True

    # Cache must be completely empty since no commit succeeded
    assert service.latest_for_subject(SUBJECT_USER_ID) is None


def test_scope_error_missing_demo_run_returns_400_and_rolls_back() -> None:
    session = FakeLocationSession(missing_demo_run=True)
    client, service, _ = _build_test_client(session=session)

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "demo_run_id": str(uuid4()),
            "latitude": 15.0,
            "longitude": 15.0,
            "captured_at": "2026-01-01T11:59:00Z",
            "source_kind": "TEST",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "LOCATION_SCOPE_INVALID"
    assert session.rolled_back is True
    assert service.latest_for_subject(SUBJECT_USER_ID) is None


def test_scope_error_missing_incident_returns_400_and_rolls_back() -> None:
    session = FakeLocationSession(missing_incident=True)
    client, service, _ = _build_test_client(session=session)

    response = client.post(
        "/api/v1/location/updates",
        json={
            "subject_user_id": str(SUBJECT_USER_ID),
            "incident_id": str(uuid4()),
            "latitude": 15.0,
            "longitude": 15.0,
            "captured_at": "2026-01-01T11:59:00Z",
            "source_kind": "TEST",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "LOCATION_SCOPE_INVALID"
    assert session.rolled_back is True
    assert service.latest_for_subject(SUBJECT_USER_ID) is None


def test_read_through_cache_hit_does_not_query_database() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    service = LocationService(clock=clock)
    service.record_location(
        LocationUpdateRequest(
            subject_user_id=SUBJECT_USER_ID,
            latitude=11.1,
            longitude=22.2,
            captured_at=datetime(2026, 1, 1, 11, 58, tzinfo=UTC),
            source_kind="CACHE_HIT",
        )
    )

    session = FakeLocationSession()
    client, _, _ = _build_test_client(service=service, session=session)

    response = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(SUBJECT_USER_ID)},
    )

    assert response.status_code == 200
    assert response.json()["source_kind"] == "CACHE_HIT"
    # Scalar query count should be 0 because cache hit resolved the request
    assert session.scalar_query_count == 0


def test_read_through_subject_cache_miss_queries_db_and_repopulates_cache() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    service = LocationService(clock=clock)
    session = FakeLocationSession()

    db_rec = LocationSnapshotRecord(
        location_id=uuid4(),
        subject_user_id=SUBJECT_USER_ID,
        latitude=19.0760,
        longitude=72.8777,
        accuracy_meters=8.0,
        source_kind="DB_SEEDED",
        captured_at=datetime(2026, 1, 1, 11, 58, tzinfo=UTC),
        received_at=datetime(2026, 1, 1, 11, 58, 5, tzinfo=UTC),
    )
    session.location_records.append(db_rec)

    client, _, _ = _build_test_client(service=service, session=session)

    # Cache is empty initially
    assert service.latest_for_subject(SUBJECT_USER_ID) is None

    response = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(SUBJECT_USER_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["location_snapshot_id"] == str(db_rec.location_id)
    assert body["source_kind"] == "DB_SEEDED"

    # Cache was repopulated by read-through
    cached = service.latest_for_subject(SUBJECT_USER_ID)
    assert cached is not None
    assert cached.location_snapshot_id == db_rec.location_id

    # Subsequent request uses cache; scalar_query_count does not increase
    count_before = session.scalar_query_count
    cached_resp = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(SUBJECT_USER_ID)},
    )
    assert cached_resp.status_code == 200
    assert session.scalar_query_count == count_before


def test_read_through_incident_cache_miss_queries_db_and_repopulates_cache() -> None:
    clock = FixedClock(datetime(2026, 1, 1, 12, 0, tzinfo=UTC))
    service = LocationService(clock=clock)
    session = FakeLocationSession()
    incident_id = uuid4()

    db_rec = LocationSnapshotRecord(
        location_id=uuid4(),
        subject_user_id=SUBJECT_USER_ID,
        incident_id=incident_id,
        latitude=28.7041,
        longitude=77.1025,
        accuracy_meters=5.0,
        source_kind="INCIDENT_DB",
        captured_at=datetime(2026, 1, 1, 11, 58, tzinfo=UTC),
        received_at=datetime(2026, 1, 1, 11, 58, 2, tzinfo=UTC),
    )
    session.location_records.append(db_rec)

    client, _, _ = _build_test_client(service=service, session=session)

    assert service.latest_for_incident(incident_id) is None

    response = client.get(
        "/api/v1/location/latest",
        params={"incident_id": str(incident_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["location_snapshot_id"] == str(db_rec.location_id)
    assert body["incident_id"] == str(incident_id)

    # In-memory cache now repopulated for this incident
    cached = service.latest_for_incident(incident_id)
    assert cached is not None
    assert cached.location_snapshot_id == db_rec.location_id


def test_read_through_unauthorized_caregiver_cannot_access_db_record() -> None:
    other_subject = uuid4()
    caregiver = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.CAREGIVER)

    session = FakeLocationSession()
    # Seed a record for other_subject in DB
    db_rec = LocationSnapshotRecord(
        location_id=uuid4(),
        subject_user_id=other_subject,
        latitude=10.0,
        longitude=10.0,
        source_kind="SECRET",
        captured_at=datetime(2026, 1, 1, 11, 58, tzinfo=UTC),
        received_at=datetime(2026, 1, 1, 11, 58, 2, tzinfo=UTC),
    )
    session.location_records.append(db_rec)

    # can_access_subject will return False for unauthorized caregiver
    client, _, _ = _build_test_client(session=session, principal=caregiver)

    response = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(other_subject)},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "LOCATION_ACCESS_DENIED"


def test_read_through_preserves_staleness_computation() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    clock = FixedClock(now)
    service = LocationService(clock=clock, stale_after_seconds=300)
    session = FakeLocationSession()

    # Captured 400 seconds ago (> 300s window)
    db_rec = LocationSnapshotRecord(
        location_id=uuid4(),
        subject_user_id=SUBJECT_USER_ID,
        latitude=10.0,
        longitude=10.0,
        source_kind="OLD_DB",
        captured_at=now - timedelta(seconds=400),
        received_at=now - timedelta(seconds=395),
    )
    session.location_records.append(db_rec)

    client, _, _ = _build_test_client(service=service, session=session)

    response = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(SUBJECT_USER_ID)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_stale"] is True


def test_read_through_empty_cache_and_empty_db_returns_404() -> None:
    session = FakeLocationSession()
    client, _, _ = _build_test_client(session=session)

    response = client.get(
        "/api/v1/location/latest",
        params={"subject_user_id": str(SUBJECT_USER_ID)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "LOCATION_NOT_AVAILABLE"
