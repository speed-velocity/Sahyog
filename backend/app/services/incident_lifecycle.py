"""Pure incident lifecycle validation.

Database writes and timeline persistence belong around this state machine so every
caller applies the same transition rules.
"""

from dataclasses import dataclass

from backend.app.schemas.incidents import IncidentStatus, IncidentTransition


class InvalidIncidentTransition(ValueError):
    """Raised when an incident event is not valid for its current status."""


_TRANSITIONS: dict[tuple[IncidentStatus, IncidentTransition], IncidentStatus] = {
    (
        IncidentStatus.PENDING_VERIFICATION,
        IncidentTransition.I_AM_OK,
    ): IncidentStatus.RESOLVED_FALSE_ALARM,
    (
        IncidentStatus.PENDING_VERIFICATION,
        IncidentTransition.VERIFICATION_TIMEOUT,
    ): IncidentStatus.ESCALATION_IN_PROGRESS,
    (
        IncidentStatus.ESCALATION_IN_PROGRESS,
        IncidentTransition.ESCALATION_SUCCEEDED,
    ): IncidentStatus.ESCALATED,
    (
        IncidentStatus.ESCALATED,
        IncidentTransition.AUTHORIZED_RESOLUTION,
    ): IncidentStatus.RESOLVED,
}


@dataclass(frozen=True)
class TransitionResult:
    previous_status: IncidentStatus
    current_status: IncidentStatus


def transition_incident(
    current_status: IncidentStatus, event: IncidentTransition
) -> TransitionResult:
    """Validate and apply one lifecycle event without performing persistence."""

    next_status = _TRANSITIONS.get((current_status, event))
    if next_status is None:
        raise InvalidIncidentTransition(
            f"event {event.value!r} is invalid for status {current_status.value!r}"
        )
    return TransitionResult(current_status, next_status)
