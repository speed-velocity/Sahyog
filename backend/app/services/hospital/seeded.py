"""Seeded fictional hospital directory for offline demonstration fallback."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

from backend.app.services.hospital.protocol import HospitalSeed

SEEDED_HOSPITAL_PROVIDER = "SEEDED_DEMO_DIRECTORY"
SEEDED_HOSPITAL_DISCLAIMER = (
    "Seeded demonstration hospital data only. No hospital has been contacted, "
    "is confirmed available, or has accepted an incident."
)


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
