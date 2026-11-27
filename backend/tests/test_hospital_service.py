from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import pytest
from backend.app.api.location import get_location_service, router
from backend.app.core.auth import require_active_principal
from backend.app.db.session import get_db
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from backend.app.services import location as location_module
from backend.app.services.hospital import (
    SEEDED_HOSPITAL_DISCLAIMER,
    SEEDED_HOSPITAL_PROVIDER,
    HospitalDirectory,
    HospitalSeed,
    HospitalService,
    HospitalServiceProtocol,
    NearbyHospital,
    NearbyHospitalsResponse,
    SeededHospitalDirectory,
    haversine_distance_meters,
)
from backend.app.services.location import (
    LocationService,
    LocationUpdateRequest,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError


class _CustomDirectory:
    provider_name = "CUSTOM_TEST_DIRECTORY"
    disclaimer = "Custom test hospitals only."

    def __init__(self, entries: tuple[HospitalSeed, ...]) -> None:
        self._entries = entries

    def list_hospitals(self) -> tuple[HospitalSeed, ...]:
        return self._entries


def test_location_module_reexports_shared_hospital_contracts() -> None:
    assert location_module.HospitalDirectory is HospitalDirectory
    assert location_module.SeededHospitalDirectory is SeededHospitalDirectory
    assert location_module.HospitalSeed is HospitalSeed
    assert location_module.NearbyHospital is NearbyHospital
    assert location_module.NearbyHospitalsResponse is NearbyHospitalsResponse
    assert location_module.haversine_distance_meters is haversine_distance_meters


def test_seeded_hospital_directory_uses_fictional_pune_entries() -> None:
    directory: HospitalDirectory = SeededHospitalDirectory()
    entries = directory.list_hospitals()

    assert directory.provider_name == SEEDED_HOSPITAL_PROVIDER
    assert directory.disclaimer == SEEDED_HOSPITAL_DISCLAIMER
    assert len(entries) == 3
    assert all("Demo" in entry.name for entry in entries)
    assert all("Pune" in entry.address for entry in entries)
    assert all(entry.source_kind == "SEEDED_DEMO" for entry in entries)


def test_hospital_service_sorts_limits_and_labels_seeded_results() -> None:
    fixed_time = datetime(2026, 11, 26, 2, 15, tzinfo=UTC)
    service = HospitalService(clock=lambda: fixed_time)

    response = service.nearby_hospitals(18.5204, 73.8567, limit=2)

    assert response.provider == SEEDED_HOSPITAL_PROVIDER
    assert response.disclaimer == SEEDED_HOSPITAL_DISCLAIMER
    assert response.generated_at == fixed_time
    assert len(response.hospitals) == 2
    assert (
        response.hospitals[0].distance_meters <= response.hospitals[1].distance_meters
    )


def test_hospital_service_supports_injected_directory_and_clamps_limits() -> None:
    fixed_time = datetime(2026, 11, 26, 2, 15, tzinfo=UTC)
    entries = (
        HospitalSeed(
            hospital_id=uuid5(NAMESPACE_URL, "custom:beta"),
            name="Beta Demo Clinic",
            address="Beta street",
            latitude=18.5204,
            longitude=73.8567,
        ),
        HospitalSeed(
            hospital_id=uuid5(NAMESPACE_URL, "custom:alpha"),
            name="Alpha Demo Clinic",
            address="Alpha street",
            latitude=18.5204,
            longitude=73.8567,
        ),
    )
    service = HospitalService(_CustomDirectory(entries), clock=lambda: fixed_time)

    min_clamped = service.nearby_hospitals(18.5204, 73.8567, limit=0)
    assert len(min_clamped.hospitals) == 1
    # Equal distance ties break deterministically by hospital name.
    assert min_clamped.hospitals[0].name == "Alpha Demo Clinic"
    assert min_clamped.provider == "CUSTOM_TEST_DIRECTORY"

    max_clamped = service.nearby_hospitals(18.5204, 73.8567, limit=99)
    assert len(max_clamped.hospitals) == 2


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (-90.1, 73.8567),
        (90.1, 73.8567),
        (18.5204, -180.1),
        (18.5204, 180.1),
        (math.nan, 73.8567),
        (18.5204, math.nan),
    ],
)
def test_hospital_service_rejects_invalid_coordinates(
    latitude: float, longitude: float
) -> None:
    service = HospitalService()

    with pytest.raises(ValueError, match="between"):
        service.nearby_hospitals(latitude, longitude)


def test_hospital_service_requires_timezone_aware_clock() -> None:
    service = HospitalService(clock=lambda: datetime(2026, 11, 26, 2, 15))

    with pytest.raises(ValueError, match="timezone-aware"):
        service.nearby_hospitals(18.5204, 73.8567)


def test_location_service_accepts_injected_hospital_service() -> None:
    fixed_time = datetime(2026, 11, 26, 2, 15, tzinfo=UTC)
    expected = NearbyHospitalsResponse(
        hospitals=[],
        provider="INJECTED_HOSPITAL_SERVICE",
        disclaimer="Injected test disclaimer.",
        generated_at=fixed_time,
    )

    class _FakeHospitalService:
        def __init__(self) -> None:
            self.calls: list[tuple[float, float, int]] = []

        def nearby_hospitals(
            self,
            latitude: float,
            longitude: float,
            limit: int = 5,
        ) -> NearbyHospitalsResponse:
            self.calls.append((latitude, longitude, limit))
            return expected

    fake_service: HospitalServiceProtocol = _FakeHospitalService()
    location_service = LocationService(
        hospital_service=fake_service, clock=lambda: fixed_time
    )

    result = location_service.nearby_hospitals(18.5204, 73.8567, limit=3)

    assert result is expected
    assert fake_service.calls == [(18.5204, 73.8567, 3)]


def test_location_service_rejects_both_directory_and_service_injection() -> None:
    with pytest.raises(ValueError, match="at most one"):
        LocationService(
            SeededHospitalDirectory(),
            hospital_service=HospitalService(),
        )


def test_hospital_directory_protocol_runtime_checkable() -> None:
    assert isinstance(SeededHospitalDirectory(), HospitalDirectory)
    assert isinstance(_CustomDirectory(()), HospitalDirectory)

    class _IncompleteDirectory:
        provider_name = "INCOMPLETE"

    assert not isinstance(_IncompleteDirectory(), HospitalDirectory)


def test_hospital_service_protocol_runtime_checkable() -> None:
    assert isinstance(HospitalService(), HospitalServiceProtocol)

    class _NotAService:
        pass

    assert not isinstance(_NotAService(), HospitalServiceProtocol)


def test_hospital_service_exposes_directory_and_metadata_properties() -> None:
    custom_dir = _CustomDirectory(())
    service = HospitalService(custom_dir)

    assert service.directory is custom_dir
    assert service.provider_name == "CUSTOM_TEST_DIRECTORY"
    assert service.disclaimer == "Custom test hospitals only."


def test_location_service_exposes_directory_and_service_properties() -> None:
    # 1. Default seeded fallback
    default_ls = LocationService()
    assert default_ls.hospital_directory is not None
    assert default_ls._hospital_directory is not None
    assert default_ls.hospital_directory.provider_name == SEEDED_HOSPITAL_PROVIDER
    assert isinstance(default_ls.hospital_service, HospitalServiceProtocol)

    # 2. Legacy hospital_directory injection
    custom_dir = _CustomDirectory(())
    dir_ls = LocationService(custom_dir)
    assert dir_ls.hospital_directory is custom_dir
    assert dir_ls._hospital_directory is custom_dir

    # 3. New hospital_service injection
    custom_svc = HospitalService(custom_dir)
    svc_ls = LocationService(hospital_service=custom_svc)
    assert svc_ls.hospital_service is custom_svc
    assert svc_ls.hospital_directory is custom_dir


def test_location_service_legacy_hospital_directory_injection() -> None:
    fixed_time = datetime(2026, 11, 26, 2, 15, tzinfo=UTC)
    entries = (
        HospitalSeed(
            hospital_id=uuid5(NAMESPACE_URL, "custom:legacy"),
            name="Legacy Injected Clinic",
            address="Legacy street, Pune",
            latitude=18.5204,
            longitude=73.8567,
        ),
    )
    custom_dir = _CustomDirectory(entries)
    service = LocationService(hospital_directory=custom_dir, clock=lambda: fixed_time)

    response = service.nearby_hospitals(18.5204, 73.8567, limit=5)
    assert len(response.hospitals) == 1
    assert response.hospitals[0].name == "Legacy Injected Clinic"
    assert response.provider == "CUSTOM_TEST_DIRECTORY"
    assert response.disclaimer == "Custom test hospitals only."


def test_hospital_seed_frozen_and_validation() -> None:
    seed = HospitalSeed(
        hospital_id=uuid5(NAMESPACE_URL, "seed:test"),
        name="Test Clinic",
        address="Test Road",
        latitude=18.5,
        longitude=73.8,
    )
    with pytest.raises(ValidationError):
        seed.name = "Mutated"

    with pytest.raises(ValidationError):
        HospitalSeed(
            hospital_id=uuid5(NAMESPACE_URL, "seed:test2"),
            name="Test",
            address="Test",
            latitude=18.5,
            longitude=73.8,
            extra_field="unsupported",
        )


def test_location_service_preserves_location_operations_alongside_hospital_service() -> (
    None
):
    fixed_time = datetime(2026, 11, 26, 2, 15, tzinfo=UTC)
    subject_user_id = uuid5(NAMESPACE_URL, "user:subject-1")
    incident_id = uuid5(NAMESPACE_URL, "incident:1")

    service = LocationService(
        hospital_service=HospitalService(), clock=lambda: fixed_time
    )

    update = LocationUpdateRequest(
        subject_user_id=subject_user_id,
        incident_id=incident_id,
        latitude=18.5204,
        longitude=73.8567,
        accuracy_meters=10.0,
        captured_at=fixed_time,
        source_kind="SIMULATED",
    )
    snapshot = service.record_location(update)
    assert snapshot.subject_user_id == subject_user_id
    assert snapshot.latitude == 18.5204
    assert snapshot.is_stale is False

    retrieved = service.latest_for_subject(subject_user_id)
    assert retrieved is not None
    assert retrieved.location_snapshot_id == snapshot.location_snapshot_id

    # Verify hospital lookup works concurrently on the same service
    hospitals = service.nearby_hospitals(18.5204, 73.8567, limit=1)
    assert len(hospitals.hospitals) == 1
    assert hospitals.provider == SEEDED_HOSPITAL_PROVIDER


def test_nearby_hospital_endpoint_via_router_with_hospital_service() -> None:
    subject_id = uuid5(NAMESPACE_URL, "user:subject-api")
    fixed_time = datetime(2026, 11, 26, 2, 15, tzinfo=UTC)
    custom_dir = _CustomDirectory(
        (
            HospitalSeed(
                hospital_id=uuid5(NAMESPACE_URL, "api:h1"),
                name="Router Hospital One",
                address="Router Pune",
                latitude=18.5204,
                longitude=73.8567,
            ),
        )
    )
    service = LocationService(
        hospital_service=HospitalService(custom_dir, clock=lambda: fixed_time),
        clock=lambda: fixed_time,
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_location_service] = lambda: service
    app.dependency_overrides[require_active_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject_id, role=UserRole.SUBJECT
    )
    app.dependency_overrides[get_db] = lambda: type(
        "FakeSession", (), {"get": lambda _self, _m, _i: None}
    )()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/hospitals/nearby",
            params={"latitude": 18.5204, "longitude": 73.8567, "limit": 3},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "CUSTOM_TEST_DIRECTORY"
    assert body["disclaimer"] == "Custom test hospitals only."
    assert len(body["hospitals"]) == 1
    assert body["hospitals"][0]["name"] == "Router Hospital One"
    assert body["hospitals"][0]["distance_meters"] == 0.0
