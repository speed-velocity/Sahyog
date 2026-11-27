"""In-memory simulated notifier for local and demonstration escalations."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from uuid import UUID

from backend.app.core.clock import utc_now
from backend.app.schemas.incidents import NotificationResultStatus
from backend.app.services.notifier.protocol import (
    EscalationNotifier,
    NotificationResult,
)

DEFAULT_MAX_MOCK_RECORDS = 256


@dataclass(frozen=True)
class SimulatedEscalationRecord:
    """Bounded in-memory record of one simulated escalation request."""

    incident_id: UUID
    escalation_attempt_id: UUID
    trigger_reason: str
    idempotency_key: str
    provider_reference: str | None
    status: NotificationResultStatus
    failure_reason: str | None
    recorded_at: datetime
    context: dict[str, str]
    simulated: bool = True


class MockEscalationNotifier:
    """Simulated EscalationNotifier that performs no external network I/O."""

    def __init__(
        self,
        max_results: int | None = None,
        *,
        clock: Callable[[], datetime] = utc_now,
        max_records: int = DEFAULT_MAX_MOCK_RECORDS,
        simulated_status: NotificationResultStatus = NotificationResultStatus.ACCEPTED,
        failure_reason: str | None = None,
    ) -> None:
        effective_max_records = max_results if max_results is not None else max_records
        if effective_max_records < 1:
            raise ValueError("max_records must be at least 1")
        if simulated_status is NotificationResultStatus.DELIVERED:
            raise ValueError(
                "MockEscalationNotifier must never claim real delivery (DELIVERED)"
            )
        self._clock = clock
        self._max_records = effective_max_records
        self._simulated_status = simulated_status
        self._failure_reason = failure_reason
        self._records: OrderedDict[
            str, tuple[SimulatedEscalationRecord, NotificationResult]
        ] = OrderedDict()
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
        """Record one simulated escalation notification without external delivery."""

        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be blank")

        with self._lock:
            existing = self._records.get(idempotency_key)
            if existing is not None:
                return existing[1]

            completed_at = self._now()
            provider_reference = (
                None
                if self._simulated_status is NotificationResultStatus.FAILED
                else f"simulated-mock:{idempotency_key}"
            )
            failure_reason = self._failure_reason or (
                "Simulated notification failure"
                if self._simulated_status is NotificationResultStatus.FAILED
                else None
            )
            result = NotificationResult(
                status=self._simulated_status,
                provider_reference=provider_reference,
                failure_reason=failure_reason,
                completed_at=completed_at,
            )
            record = SimulatedEscalationRecord(
                incident_id=incident_id,
                escalation_attempt_id=escalation_attempt_id,
                trigger_reason=trigger_reason,
                idempotency_key=idempotency_key,
                provider_reference=provider_reference,
                status=self._simulated_status,
                failure_reason=failure_reason,
                recorded_at=completed_at,
                context=dict(context),
                simulated=True,
            )
            self._records[idempotency_key] = (record, result)
            while len(self._records) > self._max_records:
                self._records.popitem(last=False)
            return result

    @property
    def records(self) -> tuple[SimulatedEscalationRecord, ...]:
        """Return recorded simulated attempts in insertion order."""

        with self._lock:
            return tuple(entry[0] for entry in self._records.values())

    def clear(self) -> None:
        """Clear recorded simulated attempts."""

        with self._lock:
            self._records.clear()

    def _now(self) -> datetime:
        current = self._clock()
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("notifier clock must return a timezone-aware datetime")
        return current.astimezone(UTC)


_demo_notifier = MockEscalationNotifier()


def get_demo_notifier() -> EscalationNotifier:
    """Return the shared bounded, simulated notifier for local demo runs."""

    return _demo_notifier
