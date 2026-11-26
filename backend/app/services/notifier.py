"""Notifier boundary; transport implementation remains integration-owned."""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
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


class MockEscalationNotifier:
    """Local demo notifier; records accepted requests without external delivery."""

    def __init__(self, max_results: int = 1024) -> None:
        self._results: OrderedDict[str, NotificationResult] = OrderedDict()
        self._max_results = max(1, max_results)
        self._lock = RLock()

    async def send_escalation_notification(
        self,
        *,
        incident_id: UUID,
        escalation_attempt_id: UUID,
        trigger_reason: str,
        idempotency_key: str,
        context: dict[str, str],
    ) -> NotificationResult:
        del incident_id, escalation_attempt_id, trigger_reason, context
        with self._lock:
            existing = self._results.get(idempotency_key)
            if existing is not None:
                return existing
            result = NotificationResult(
                status=NotificationResultStatus.ACCEPTED,
                provider_reference=f"mock://escalation/{idempotency_key}",
                failure_reason=None,
                completed_at=datetime.now(UTC),
            )
            self._results[idempotency_key] = result
            while len(self._results) > self._max_results:
                self._results.popitem(last=False)
            return result


_demo_notifier = MockEscalationNotifier()


def get_demo_notifier() -> EscalationNotifier:
    return _demo_notifier
