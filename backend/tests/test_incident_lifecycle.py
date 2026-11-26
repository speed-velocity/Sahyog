import pytest
from backend.app.schemas.incidents import IncidentStatus, IncidentTransition
from backend.app.services.incident_lifecycle import (
    InvalidIncidentTransition,
    transition_incident,
)


def test_false_alarm_transition() -> None:
    result = transition_incident(
        IncidentStatus.PENDING_VERIFICATION,
        IncidentTransition.I_AM_OK,
    )

    assert result.current_status is IncidentStatus.RESOLVED_FALSE_ALARM


def test_timeout_then_escalation_transition() -> None:
    pending = transition_incident(
        IncidentStatus.PENDING_VERIFICATION,
        IncidentTransition.VERIFICATION_TIMEOUT,
    )
    escalated = transition_incident(
        pending.current_status,
        IncidentTransition.ESCALATION_SUCCEEDED,
    )

    assert escalated.current_status is IncidentStatus.ESCALATED


def test_terminal_status_rejects_new_event() -> None:
    with pytest.raises(InvalidIncidentTransition):
        transition_incident(
            IncidentStatus.RESOLVED_FALSE_ALARM,
            IncidentTransition.VERIFICATION_TIMEOUT,
        )
