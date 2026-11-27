"""Shared hospital directory protocol and canonical response schemas."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DEFAULT_HOSPITAL_RESULT_LIMIT = 5
MIN_HOSPITAL_RESULT_LIMIT = 1
MAX_HOSPITAL_RESULT_LIMIT = 10


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


@runtime_checkable
class HospitalDirectory(Protocol):
    """Narrow boundary for replacing seeded data with the shared provider."""

    @property
    def provider_name(self) -> str: ...

    @property
    def disclaimer(self) -> str: ...

    def list_hospitals(self) -> Sequence[HospitalSeed]: ...


@runtime_checkable
class HospitalServiceProtocol(Protocol):
    """Injectable hospital-lookup service boundary for backend consumers."""

    def nearby_hospitals(
        self,
        latitude: float,
        longitude: float,
        limit: int = DEFAULT_HOSPITAL_RESULT_LIMIT,
    ) -> NearbyHospitalsResponse: ...
