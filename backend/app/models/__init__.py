"""Explicit model registration for shared SQLAlchemy metadata discovery."""

from backend.app.db.base import Base
from backend.app.models.auth import AuthIdentity, CaregiverAuthorization
from backend.app.models.demo import DemoRun
from backend.app.models.identity import User
from backend.app.models.incidents import (
    EscalationAttempt,
    Incident,
    IncidentAnomalyEvent,
    IncidentTimelineEvent,
    VerificationResponse,
)
from backend.app.models.location import LocationSnapshotRecord
from backend.app.models.readings import AnomalyEvent, HealthReading

__all__ = [
    "AnomalyEvent",
    "AuthIdentity",
    "Base",
    "CaregiverAuthorization",
    "DemoRun",
    "EscalationAttempt",
    "HealthReading",
    "Incident",
    "IncidentAnomalyEvent",
    "IncidentTimelineEvent",
    "LocationSnapshotRecord",
    "User",
    "VerificationResponse",
]
