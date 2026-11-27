"""Escalation notifier package preserving the shared notifier boundary."""

from backend.app.services.notifier.mock import (
    MockEscalationNotifier,
    SimulatedEscalationRecord,
    get_demo_notifier,
)
from backend.app.services.notifier.protocol import (
    EscalationNotifier,
    NotificationResult,
)

__all__ = [
    "EscalationNotifier",
    "MockEscalationNotifier",
    "NotificationResult",
    "SimulatedEscalationRecord",
    "get_demo_notifier",
]
