"""Shared hospital abstraction and offline demo directory package."""

from backend.app.services.hospital.protocol import (
    DEFAULT_HOSPITAL_RESULT_LIMIT,
    MAX_HOSPITAL_RESULT_LIMIT,
    MIN_HOSPITAL_RESULT_LIMIT,
    HospitalDirectory,
    HospitalSeed,
    HospitalServiceProtocol,
    NearbyHospital,
    NearbyHospitalsResponse,
)
from backend.app.services.hospital.seeded import (
    SEEDED_HOSPITAL_DISCLAIMER,
    SEEDED_HOSPITAL_PROVIDER,
    SeededHospitalDirectory,
)
from backend.app.services.hospital.service import (
    EARTH_RADIUS_METERS,
    HospitalService,
    haversine_distance_meters,
)

__all__ = [
    "DEFAULT_HOSPITAL_RESULT_LIMIT",
    "EARTH_RADIUS_METERS",
    "MAX_HOSPITAL_RESULT_LIMIT",
    "MIN_HOSPITAL_RESULT_LIMIT",
    "SEEDED_HOSPITAL_DISCLAIMER",
    "SEEDED_HOSPITAL_PROVIDER",
    "HospitalDirectory",
    "HospitalSeed",
    "HospitalService",
    "HospitalServiceProtocol",
    "NearbyHospital",
    "NearbyHospitalsResponse",
    "SeededHospitalDirectory",
    "haversine_distance_meters",
]
