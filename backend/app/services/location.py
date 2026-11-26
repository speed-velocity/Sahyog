"""Bounded location snapshots and clearly labelled demo hospital lookup."""

from __future__ import annotations

import math
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_STALE_AFTER_SECONDS = 300
MAX_FUTURE_CAPTURE_SKEW_SECONDS = 120
DEFAULT_MAX_LOCATION_ENTRIES = 512
DEFAULT_HOSPITAL_RESULT_LIMIT = 5
MIN_HOSPITAL_RESULT_LIMIT = 1
MAX_HOSPITAL_RESULT_LIMIT = 10
EARTH_RADIUS_METERS = 6_371_000.0
SEEDED_HOSPITAL_PROVIDER = "SEEDED_DEMO_DIRECTORY"
SEEDED_HOSPITAL_DISCLAIMER = (
    "Seeded demonstration hospital data only. No hospital has been contacted, "
    "is confirmed available, or has accepted an incident."
)


class LocationUpdateRequest(BaseModel):
    """Authorised location snapshot supplied by the mobile client."""

    model_config = ConfigDict(extra="forbid")

    subject_user_id: UUID
    incident_id: UUID | None = None
    demo_run_id: UUID | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, gt=0, le=100_000)
    captured_at: datetime
    source_kind: str = Field(default="UNKNOWN", min_length=1, max_length=40)

    @field_validator("captured_at")
    @classmethod
    def captured_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")
        return value.astimezone(UTC)

    @field_validator("source_kind")
    @classmethod
    def normalize_source_kind(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("source_kind must not be blank")
        return normalized


class LocationSnapshot(BaseModel):
    """Latest authorised location returned to the dashboard or mobile client."""

    model_config = ConfigDict(extra="forbid")

    location_snapshot_id: UUID
    subject_user_id: UUID
    incident_id: UUID | None = None
    demo_run_id: UUID | None = None
    latitude: float
    longitude: float
    accuracy_meters: float | None = None
    captured_at: datetime
    received_at: datetime
    source_kind: str
    is_stale: bool
    stale_after_seconds: int


class HospitalSeed(BaseModel):
    """A clearly labelled hospital directory entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hospital_id: UUID
    name: str
    address: str
    latitude: float
    longitude: float
    source_kind: str = "SEEDED_DEMO"


class NearbyHospital(BaseModel):
    """Hospital directory entry enriched with distance from the query point."""

    model_config = ConfigDict(extra="forbid")

    hospital_id: UUID
    name: str
    address: str
    latitude: float
    longitude: float
    distance_meters: float
    source_kind: str


class NearbyHospitalsResponse(BaseModel):
    """Bounded hospital list with explicit provenance and disclaimer."""

    model_config = ConfigDict(extra="forbid")

    hospitals: list[NearbyHospital]
    provider: str | None = None
    disclaimer: str
    generated_at: datetime


class HospitalDirectory(Protocol):
    """Narrow boundary for replacing seeded data with the shared provider."""

    @property
    def provider_name(self) -> str: ...

    @property
    def disclaimer(self) -> str: ...

    def list_hospitals(self) -> Sequence[HospitalSeed]: ...


class SeededHospitalDirectory:
    """Offline fallback with fictional demonstration hospitals only."""

    provider_name = SEEDED_HOSPITAL_PROVIDER
    disclaimer = SEEDED_HOSPITAL_DISCLAIMER

    def __init__(self) -> None:
        self._hospitals = (
            HospitalSeed(
                hospital_id=uuid5(NAMESPACE_URL, "sahyog-demo-hospital:central"),
                name="Sahyog Demo Central Hospital",
                address="Demo directory entry, central Pune",
                latitude=18.5167,
                longitude=73.8740,
            ),
            HospitalSeed(
                hospital_id=uuid5(NAMESPACE_URL, "sahyog-demo-hospital:north"),
                name="Sahyog Demo North Emergency Centre",
                address="Demo directory entry, north Pune",
                latitude=18.5679,
                longitude=73.8730,
            ),
            HospitalSeed(
                hospital_id=uuid5(NAMESPACE_URL, "sahyog-demo-hospital:west"),
                name="Sahyog Demo Community Care",
                address="Demo directory entry, west Pune",
                latitude=18.5089,
                longitude=73.8077,
            ),
        )

    def list_hospitals(self) -> Sequence[HospitalSeed]:
        return self._hospitals


class LocationUpdateRejected(ValueError):
    """Raised when a location timestamp is not credible for the current clock."""


@dataclass(frozen=True)
class _StoredLocation:
    location_snapshot_id: UUID
    update: LocationUpdateRequest
    received_at: datetime


class LocationService:
    """Thread-safe, bounded in-memory store for demonstration location data."""

    def __init__(
        self,
        hospital_directory: HospitalDirectory | None = None,
        *,
        stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
        max_location_entries: int = DEFAULT_MAX_LOCATION_ENTRIES,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._hospital_directory = hospital_directory or SeededHospitalDirectory()
        self._stale_after_seconds = max(1, int(stale_after_seconds))
        self._max_location_entries = max(1, int(max_location_entries))
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()
        self._by_subject: dict[UUID, _StoredLocation] = {}
        self._by_incident: dict[UUID, _StoredLocation] = {}

    @property
    def stale_after_seconds(self) -> int:
        return self._stale_after_seconds

    def record_location(self, update: LocationUpdateRequest) -> LocationSnapshot:
        now = self._now()
        if update.captured_at > now + timedelta(
            seconds=MAX_FUTURE_CAPTURE_SKEW_SECONDS
        ):
            raise LocationUpdateRejected(
                "captured_at must not be more than two minutes in the future"
            )

        stored = _StoredLocation(
            location_snapshot_id=uuid4(),
            update=update,
            received_at=now,
        )

        with self._lock:
            self._put_latest(self._by_subject, update.subject_user_id, stored)
            if update.incident_id is not None:
                self._put_latest(self._by_incident, update.incident_id, stored)

        return self._snapshot(stored, now)

    def latest_for_subject(self, subject_user_id: UUID) -> LocationSnapshot | None:
        now = self._now()
        with self._lock:
            stored = self._by_subject.get(subject_user_id)
        return None if stored is None else self._snapshot(stored, now)

    def latest_for_incident(self, incident_id: UUID) -> LocationSnapshot | None:
        now = self._now()
        with self._lock:
            stored = self._by_incident.get(incident_id)
        return None if stored is None else self._snapshot(stored, now)

    def nearby_hospitals(
        self,
        latitude: float,
        longitude: float,
        limit: int = DEFAULT_HOSPITAL_RESULT_LIMIT,
    ) -> NearbyHospitalsResponse:
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

        safe_limit = max(
            MIN_HOSPITAL_RESULT_LIMIT,
            min(int(limit), MAX_HOSPITAL_RESULT_LIMIT),
        )
        hospitals = [
            NearbyHospital(
                hospital_id=hospital.hospital_id,
                name=hospital.name,
                address=hospital.address,
                latitude=hospital.latitude,
                longitude=hospital.longitude,
                source_kind=hospital.source_kind,
                distance_meters=haversine_distance_meters(
                    latitude,
                    longitude,
                    hospital.latitude,
                    hospital.longitude,
                ),
            )
            for hospital in self._hospital_directory.list_hospitals()
        ]
        hospitals.sort(key=lambda hospital: (hospital.distance_meters, hospital.name))

        return NearbyHospitalsResponse(
            hospitals=hospitals[:safe_limit],
            provider=self._hospital_directory.provider_name,
            disclaimer=self._hospital_directory.disclaimer,
            generated_at=self._now(),
        )

    def _put_latest(
        self,
        mapping: dict[UUID, _StoredLocation],
        key: UUID,
        stored: _StoredLocation,
    ) -> None:
        mapping[key] = stored
        while len(mapping) > self._max_location_entries:
            oldest_key = min(
                mapping,
                key=lambda candidate: mapping[candidate].received_at,
            )
            del mapping[oldest_key]

    def _snapshot(self, stored: _StoredLocation, now: datetime) -> LocationSnapshot:
        update = stored.update
        age = now - update.captured_at
        return LocationSnapshot(
            location_snapshot_id=stored.location_snapshot_id,
            subject_user_id=update.subject_user_id,
            incident_id=update.incident_id,
            demo_run_id=update.demo_run_id,
            latitude=update.latitude,
            longitude=update.longitude,
            accuracy_meters=update.accuracy_meters,
            captured_at=update.captured_at,
            received_at=stored.received_at,
            source_kind=update.source_kind,
            is_stale=age > timedelta(seconds=self._stale_after_seconds),
            stale_after_seconds=self._stale_after_seconds,
        )

    def _now(self) -> datetime:
        current = self._clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("location clock must return a timezone-aware datetime")
        return current.astimezone(UTC)


def haversine_distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    latitude_a_radians = math.radians(latitude_a)
    latitude_b_radians = math.radians(latitude_b)
    latitude_delta = math.radians(latitude_b - latitude_a)
    longitude_delta = math.radians(longitude_b - longitude_a)

    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a_radians)
        * math.cos(latitude_b_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(haversine)))
