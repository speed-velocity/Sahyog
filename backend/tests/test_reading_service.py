from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from backend.app.services.reading_service import persist_reading


class _RetrySession:
    def __init__(self, run, existing, event) -> None:
        self._values = iter((run, existing, event))

    def scalar(self, _statement):
        return next(self._values)


def test_duplicate_reading_replays_original_anomaly_event() -> None:
    subject_id = uuid4()
    run_id = uuid4()
    observed_at = datetime(2026, 1, 1, tzinfo=UTC)
    run = SimpleNamespace(current_generation=1)
    existing = SimpleNamespace(
        subject_user_id=subject_id,
        demo_run_id=run_id,
        run_generation=1,
        observed_at=observed_at,
    )
    event = SimpleNamespace(anomaly_event_id=uuid4())

    reading, replayed_event = persist_reading(
        _RetrySession(run, existing, event),
        subject_user_id=subject_id,
        demo_run_id=run_id,
        heart_rate_bpm=130,
        observed_at=observed_at,
        source_kind="SIMULATED",
        activity_context=None,
        source_record_id=None,
        ingestion_idempotency_key="retry-key",
        detector_result=None,
    )

    assert reading is existing
    assert replayed_event is event
