import asyncio
import inspect
from uuid import uuid4

from backend.app.services.notifier import MockEscalationNotifier
from backend.app.workers.timeout import process_expired_incidents, run_timeout_worker


def test_timeout_worker_is_async_and_bounded_by_limit() -> None:
    assert inspect.iscoroutinefunction(process_expired_incidents)
    assert "limit" in inspect.signature(process_expired_incidents).parameters
    assert inspect.iscoroutinefunction(run_timeout_worker)


def test_demo_notifier_is_idempotent() -> None:
    notifier = MockEscalationNotifier()
    first = asyncio.run(
        notifier.send_escalation_notification(
            incident_id=uuid4(),
            escalation_attempt_id=uuid4(),
            trigger_reason="VERIFICATION_TIMEOUT",
            idempotency_key="demo-key",
            context={},
        )
    )
    second = asyncio.run(
        notifier.send_escalation_notification(
            incident_id=uuid4(),
            escalation_attempt_id=uuid4(),
            trigger_reason="VERIFICATION_TIMEOUT",
            idempotency_key="demo-key",
            context={},
        )
    )
    assert first.status.value == "ACCEPTED"
    assert second == first
