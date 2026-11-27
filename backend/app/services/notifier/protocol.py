"""Notifier boundary; transport implementation remains integration-owned."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.app.schemas.incidents import NotificationResultStatus


@dataclass(frozen=True)
class NotificationResult:
    status: NotificationResultStatus
    provider_reference: str | None
    failure_reason: str | None
    completed_at: datetime


class EscalationNotifier(Protocol):
    async def send_escalation_notification(
        self,
        *,
        incident_id: UUID,
        escalation_attempt_id: UUID,
        trigger_reason: str,
        idempotency_key: str,
        context: dict[str, str],
    ) -> NotificationResult:
        """Send one logical escalation request."""
