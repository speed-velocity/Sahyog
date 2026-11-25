"""Confirmed initial incident lifecycle vocabulary."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class IncidentStatus(StrEnum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ESCALATION_IN_PROGRESS = "ESCALATION_IN_PROGRESS"
    ESCALATED = "ESCALATED"
    RESOLVED_FALSE_ALARM = "RESOLVED_FALSE_ALARM"
    RESOLVED = "RESOLVED"


class VerificationResponseValue(StrEnum):
    I_AM_OK = "I_AM_OK"


class IncidentTransition(StrEnum):
    I_AM_OK = "I_AM_OK"
    VERIFICATION_TIMEOUT = "VERIFICATION_TIMEOUT"
    ESCALATION_SUCCEEDED = "ESCALATION_SUCCEEDED"
    AUTHORIZED_RESOLUTION = "AUTHORIZED_RESOLUTION"


class NotificationResultStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class VerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: VerificationResponseValue
    idempotency_key: str
    request_reference: str | None = None
