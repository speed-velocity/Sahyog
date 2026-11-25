from datetime import UTC, datetime

from backend.app.schemas.incidents import NotificationResultStatus
from backend.app.services.notifier import NotificationResult


def test_notifier_result_has_explicit_provider_outcome() -> None:
    result = NotificationResult(
        status=NotificationResultStatus.ACCEPTED,
        provider_reference="mock-1",
        failure_reason=None,
        completed_at=datetime.now(UTC),
    )

    assert result.status is NotificationResultStatus.ACCEPTED
