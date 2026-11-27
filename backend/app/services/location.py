"""Bounded location snapshots and clearly labelled demo hospital lookup."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.services.hospital import (
    DEFAULT_HOSPITAL_RESULT_LIMIT,
    EARTH_RADIUS_METERS,
    MAX_HOSPITAL_RESULT_LIMIT,
    MIN_HOSPITAL_RESULT_LIMIT,
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

__all__ = [
    "DEFAULT_HOSPITAL_RESULT_LIMIT",
    "DEFAULT_MAX_LOCATION_ENTRIES",
    "DEFAULT_STALE_AFTER_SECONDS",
    "EARTH_RADIUS_METERS",
    "MAX_FUTURE_CAPTURE_SKEW_SECONDS",
    "MAX_HOSPITAL_RESULT_LIMIT",
    "MIN_HOSPITAL_RESULT_LIMIT",
    "SEEDED_HOSPITAL_DISCLAIMER",
    "SEEDED_HOSPITAL_PROVIDER",
    "HospitalDirectory",
    "HospitalSeed",
    "HospitalService",
    "HospitalServiceProtocol",
    "LocationService",
    "LocationSnapshot",
    "LocationUpdateRejected",
    "LocationUpdateRequest",
    "NearbyHospital",
    "NearbyHospitalsResponse",
    "SeededHospitalDirectory",
    "haversine_distance_meters",
]

DEFAULT_STALE_AFTER_SECONDS = 300
MAX_FUTURE_CAPTURE_SKEW_SECONDS = 120
DEFAULT_MAX_LOCATION_ENTRIES = 512


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
        hospital_service: HospitalServiceProtocol | None = None,
        stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
        max_location_entries: int = DEFAULT_MAX_LOCATION_ENTRIES,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if hospital_directory is not None and hospital_service is not None:
            raise ValueError(
                "Provide at most one of hospital_directory or hospital_service"
            )
        self._stale_after_seconds = max(1, int(stale_after_seconds))
        self._max_location_entries = max(1, int(max_location_entries))
        self._clock = clock or (lambda: datetime.now(UTC))
        self._hospital_service: HospitalServiceProtocol = (
            hospital_service or HospitalService(hospital_directory, clock=self._clock)
        )
        self._hospital_directory = (
            hospital_directory
            if hospital_directory is not None
            else getattr(self._hospital_service, "directory", None)
        )
        self._lock = threading.Lock()
        self._by_subject: dict[UUID, _StoredLocation] = {}
        self._by_incident: dict[UUID, _StoredLocation] = {}

    @property
    def stale_after_seconds(self) -> int:
        return self._stale_after_seconds

    @property
    def hospital_directory(self) -> HospitalDirectory | None:
        return self._hospital_directory

    @property
    def hospital_service(self) -> HospitalServiceProtocol:
        return self._hospital_service

    def current_time(self) -> datetime:
        """Return the current timezone-aware UTC datetime from the configured clock."""
        return self._now()

    def prepare_snapshot(self, update: LocationUpdateRequest) -> LocationSnapshot:
        """Validate timestamp skew and prepare a LocationSnapshot without modifying the cache."""
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
        return self._snapshot(stored, now)

    def publish_snapshot(
        self,
        snapshot: LocationSnapshot,
        update: LocationUpdateRequest | None = None,
    ) -> None:
        """Publish an established LocationSnapshot to the in-memory cache."""
        effective_update = update or LocationUpdateRequest(
            subject_user_id=snapshot.subject_user_id,
            incident_id=snapshot.incident_id,
            demo_run_id=snapshot.demo_run_id,
            latitude=snapshot.latitude,
            longitude=snapshot.longitude,
            accuracy_meters=snapshot.accuracy_meters,
            captured_at=snapshot.captured_at,
            source_kind=snapshot.source_kind,
        )
        stored = _StoredLocation(
            location_snapshot_id=snapshot.location_snapshot_id,
            update=effective_update,
            received_at=snapshot.received_at,
        )

        with self._lock:
            self._put_latest(self._by_subject, snapshot.subject_user_id, stored)
            if snapshot.incident_id is not None:
                self._put_latest(self._by_incident, snapshot.incident_id, stored)

    def record_location(self, update: LocationUpdateRequest) -> LocationSnapshot:
        snapshot = self.prepare_snapshot(update)
        self.publish_snapshot(snapshot, update=update)
        return snapshot

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
        return self._hospital_service.nearby_hospitals(latitude, longitude, limit)

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
