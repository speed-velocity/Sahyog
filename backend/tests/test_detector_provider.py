from datetime import UTC, datetime, timedelta
from uuid import uuid4

from backend.app.services.detector_adapter import DetectorReading
from backend.app.services.detector_provider import (
    get_detector_provider,
    reset_detector_provider_for_tests,
)


def test_detector_session_isolated_by_run_generation() -> None:
    reset_detector_provider_for_tests()
    provider = get_detector_provider()
    subject = uuid4()
    run = uuid4()

    first = provider.get(subject_user_id=subject, demo_run_id=run, run_generation=1)
    second = provider.get(subject_user_id=subject, demo_run_id=run, run_generation=1)
    fresh_generation = provider.get(
        subject_user_id=subject, demo_run_id=run, run_generation=2
    )

    assert first is not second
    first_result = first.detect(
        [
            DetectorReading(
                observed_at=datetime(2026, 1, 1, tzinfo=UTC),
                heart_rate_bpm=130,
            )
        ]
    )
    assert first_result.anomaly_kind is None
    assert (
        fresh_generation.detect(
            [
                DetectorReading(
                    observed_at=datetime(2026, 1, 1, tzinfo=UTC),
                    heart_rate_bpm=72,
                )
            ]
        ).anomaly_kind
        is None
    )

    for i in range(1, 6):
        result = second.detect(
            [
                DetectorReading(
                    observed_at=datetime(2026, 1, 1, tzinfo=UTC)
                    + timedelta(seconds=i * 2),
                    heart_rate_bpm=130,
                )
            ]
        )
    assert result.anomaly_kind == "spike"
