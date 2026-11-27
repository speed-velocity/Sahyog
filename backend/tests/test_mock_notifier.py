import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from backend.app.schemas.incidents import NotificationResultStatus
from backend.app.services.notifier import (
    EscalationNotifier,
    MockEscalationNotifier,
    NotificationResult,
    get_demo_notifier,
)
from backend.app.services.notifier.mock import MockEscalationNotifier as MockImpl
from backend.app.services.notifier.mock import (
    get_demo_notifier as mock_get_demo_notifier,
)
from backend.app.services.notifier.protocol import (
    EscalationNotifier as ProtocolNotifier,
)
from backend.app.services.notifier.protocol import (
    NotificationResult as ProtocolNotificationResult,
)


def test_notifier_package_reexports_protocol_and_result() -> None:
    assert EscalationNotifier is ProtocolNotifier
    assert NotificationResult is ProtocolNotificationResult
    assert MockEscalationNotifier is MockImpl
    assert get_demo_notifier is mock_get_demo_notifier


def test_mock_notifier_records_simulated_acceptance_without_claiming_delivery() -> None:
    fixed_time = datetime(2026, 11, 26, 2, 0, tzinfo=UTC)
    notifier: EscalationNotifier = MockEscalationNotifier(clock=lambda: fixed_time)
    incident_id = uuid4()
    attempt_id = uuid4()

    result = asyncio.run(
        notifier.send_escalation_notification(
            incident_id=incident_id,
            escalation_attempt_id=attempt_id,
            trigger_reason="VERIFICATION_TIMEOUT",
            idempotency_key="verification-timeout:test-1",
            context={"incident_id": str(incident_id)},
        )
    )

    assert isinstance(result, NotificationResult)
    assert result.status is NotificationResultStatus.ACCEPTED
    assert result.provider_reference == "simulated-mock:verification-timeout:test-1"
    assert result.failure_reason is None
    assert result.completed_at == fixed_time

    assert isinstance(notifier, MockEscalationNotifier)
    assert len(notifier.records) == 1
    record = notifier.records[0]
    assert record.simulated is True
    assert record.incident_id == incident_id
    assert record.escalation_attempt_id == attempt_id
    assert record.trigger_reason == "VERIFICATION_TIMEOUT"
    assert record.context == {"incident_id": str(incident_id)}


def test_mock_notifier_rejects_delivered_status() -> None:
    with pytest.raises(ValueError, match="DELIVERED"):
        MockEscalationNotifier(simulated_status=NotificationResultStatus.DELIVERED)


def test_mock_notifier_is_idempotent_on_idempotency_key() -> None:
    ticks = iter(
        [
            datetime(2026, 11, 26, 2, 0, 0, tzinfo=UTC),
            datetime(2026, 11, 26, 2, 0, 5, tzinfo=UTC),
        ]
    )
    notifier = MockEscalationNotifier(clock=lambda: next(ticks))
    incident_id = uuid4()
    attempt_id = uuid4()

    first = asyncio.run(
        notifier.send_escalation_notification(
            incident_id=incident_id,
            escalation_attempt_id=attempt_id,
            trigger_reason="VERIFICATION_TIMEOUT",
            idempotency_key="verification-timeout:same-key",
            context={"incident_id": str(incident_id)},
        )
    )
    second = asyncio.run(
        notifier.send_escalation_notification(
            incident_id=incident_id,
            escalation_attempt_id=attempt_id,
            trigger_reason="VERIFICATION_TIMEOUT",
            idempotency_key="verification-timeout:same-key",
            context={"incident_id": str(incident_id)},
        )
    )

    assert second == first
    assert len(notifier.records) == 1


def test_mock_notifier_bounds_in_memory_records() -> None:
    base = datetime(2026, 11, 26, 2, 0, tzinfo=UTC)
    index = 0

    def next_clock() -> datetime:
        nonlocal index
        index += 1
        return base + timedelta(seconds=index)

    notifier = MockEscalationNotifier(clock=next_clock, max_records=2)
    for key in ("k1", "k2", "k3"):
        asyncio.run(
            notifier.send_escalation_notification(
                incident_id=uuid4(),
                escalation_attempt_id=uuid4(),
                trigger_reason="VERIFICATION_TIMEOUT",
                idempotency_key=key,
                context={},
            )
        )

    assert [record.idempotency_key for record in notifier.records] == ["k2", "k3"]


def test_mock_notifier_supports_simulated_failure_and_validates_inputs() -> None:
    failing = MockEscalationNotifier(
        simulated_status=NotificationResultStatus.FAILED,
        failure_reason="simulated gateway error",
    )
    result = asyncio.run(
        failing.send_escalation_notification(
            incident_id=uuid4(),
            escalation_attempt_id=uuid4(),
            trigger_reason="VERIFICATION_TIMEOUT",
            idempotency_key="k-fail",
            context={},
        )
    )
    assert result.status is NotificationResultStatus.FAILED
    assert result.provider_reference is None
    assert result.failure_reason == "simulated gateway error"

    with pytest.raises(ValueError, match="blank"):
        asyncio.run(
            failing.send_escalation_notification(
                incident_id=uuid4(),
                escalation_attempt_id=uuid4(),
                trigger_reason="VERIFICATION_TIMEOUT",
                idempotency_key="   ",
                context={},
            )
        )

    naive_clock = MockEscalationNotifier(clock=lambda: datetime(2026, 11, 26, 2, 0))
    with pytest.raises(ValueError, match="timezone-aware"):
        asyncio.run(
            naive_clock.send_escalation_notification(
                incident_id=uuid4(),
                escalation_attempt_id=uuid4(),
                trigger_reason="VERIFICATION_TIMEOUT",
                idempotency_key="k-naive",
                context={},
            )
        )


def test_get_demo_notifier_returns_shared_bounded_simulated_instance() -> None:
    first_instance = get_demo_notifier()
    second_instance = get_demo_notifier()

    assert first_instance is second_instance
    assert isinstance(first_instance, MockEscalationNotifier)

    first_instance.clear()
    try:
        incident_id = uuid4()
        attempt_id = uuid4()
        first = asyncio.run(
            first_instance.send_escalation_notification(
                incident_id=incident_id,
                escalation_attempt_id=attempt_id,
                trigger_reason="VERIFICATION_TIMEOUT",
                idempotency_key="demo-factory-key",
                context={"incident_id": str(incident_id)},
            )
        )
        second = asyncio.run(
            second_instance.send_escalation_notification(
                incident_id=incident_id,
                escalation_attempt_id=attempt_id,
                trigger_reason="VERIFICATION_TIMEOUT",
                idempotency_key="demo-factory-key",
                context={"incident_id": str(incident_id)},
            )
        )

        assert first == second
        assert first.status is NotificationResultStatus.ACCEPTED
        assert first.provider_reference == "simulated-mock:demo-factory-key"
        assert len(first_instance.records) == 1
        assert first_instance.records[0].simulated is True
    finally:
        first_instance.clear()


def test_mock_notifier_accepts_max_results_positional_and_keyword() -> None:
    positional = MockEscalationNotifier(2)
    keyword = MockEscalationNotifier(max_results=2)

    for notifier in (positional, keyword):
        for key in ("a", "b", "c"):
            asyncio.run(
                notifier.send_escalation_notification(
                    incident_id=uuid4(),
                    escalation_attempt_id=uuid4(),
                    trigger_reason="VERIFICATION_TIMEOUT",
                    idempotency_key=key,
                    context={},
                )
            )
        assert [record.idempotency_key for record in notifier.records] == ["b", "c"]
