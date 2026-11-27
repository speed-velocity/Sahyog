"""Shared hospital lookup service and geographic distance calculations."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime

from backend.app.services.hospital.protocol import (
    DEFAULT_HOSPITAL_RESULT_LIMIT,
    MAX_HOSPITAL_RESULT_LIMIT,
    MIN_HOSPITAL_RESULT_LIMIT,
    HospitalDirectory,
    NearbyHospital,
    NearbyHospitalsResponse,
)
from backend.app.services.hospital.seeded import SeededHospitalDirectory

EARTH_RADIUS_METERS = 6_371_000.0


class HospitalService:
    """Bounded, provider-neutral hospital lookup service."""

    def __init__(
        self,
        directory: HospitalDirectory | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._directory = directory or SeededHospitalDirectory()
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def directory(self) -> HospitalDirectory:
        return self._directory

    @property
    def provider_name(self) -> str:
        return self._directory.provider_name

    @property
    def disclaimer(self) -> str:
        return self._directory.disclaimer

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
            for hospital in self._directory.list_hospitals()
        ]
        hospitals.sort(key=lambda hospital: (hospital.distance_meters, hospital.name))

        return NearbyHospitalsResponse(
            hospitals=hospitals[:safe_limit],
            provider=self._directory.provider_name,
            disclaimer=self._directory.disclaimer,
            generated_at=self._now(),
        )

    def _now(self) -> datetime:
        current = self._clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("hospital clock must return a timezone-aware datetime")
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
