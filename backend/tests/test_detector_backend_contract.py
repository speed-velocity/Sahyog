"""Tests for the backend-facing single-result detector contract."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.anomaly import DetectorConfig
from backend.app.services.detector_backend_contract import (
    BACKEND_EVIDENCE_LIMIT,
    DETECTOR_VERSION,
    BackendDetector,
    BackendDetectorContractError,
    BackendDetectorReading,
)

UTC = timezone.utc
BASE_TS = datetime(2026, 1, 1, tzinfo=UTC)
RESULT_FIELDS = {
    "anomaly_kind",
    "detected_at",
    "window_start",
    "window_end",
    "severity",
    "explanation",
    "detector_version",
    "evidence",
}


def reading(
    t_ms: int,
    heart_rate_bpm: int = 72,
    activity_context: str | None = None,
) -> BackendDetectorReading:
    return BackendDetectorReading(
        observed_at=BASE_TS + timedelta(milliseconds=t_ms),
        heart_rate_bpm=heart_rate_bpm,
        activity_context=activity_context,
    )


def batch(timeline: list[tuple[int, int]]) -> list[BackendDetectorReading]:
    return [reading(t_ms, heart_rate_bpm) for t_ms, heart_rate_bpm in timeline]


def make_detector(**kwargs: object) -> BackendDetector:
    return BackendDetector(72.0, 4.0, **kwargs)  # type: ignore[arg-type]


class NormalResultTests(unittest.TestCase):
    def test_normal_reading_returns_exact_backend_shape(self) -> None:
        result = make_detector().detect([reading(0, 72)])
        self.assertEqual(set(result.model_dump()), RESULT_FIELDS)
        self.assertIsNone(result.anomaly_kind)
        self.assertEqual(result.detected_at, BASE_TS)
        self.assertEqual(result.detected_at.tzinfo, UTC)
        self.assertIsNone(result.window_start)
        self.assertIsNone(result.window_end)
        self.assertIsNone(result.severity)
        self.assertIsNone(result.explanation)
        self.assertEqual(result.detector_version, DETECTOR_VERSION)
        self.assertEqual(result.evidence, [])

    def test_normal_batch_uses_last_accepted_timestamp(self) -> None:
        detector = make_detector()
        result = detector.detect(
            [
                reading(0, 72),
                reading(1000, 73),
                reading(2000, 300),
            ]
        )
        self.assertIsNone(result.anomaly_kind)
        self.assertEqual(result.detected_at, BASE_TS + timedelta(seconds=1))
        self.assertEqual(detector.snapshot().rejected_sample_count, 1)

    def test_activity_context_is_accepted_and_ignored(self) -> None:
        detector = make_detector()
        result = detector.detect([reading(0, 72, "walking")])
        self.assertIsNone(result.anomaly_kind)
        self.assertEqual(detector.snapshot().accepted_sample_count, 1)
        self.assertEqual(set(result.model_dump()), RESULT_FIELDS)


class AnomalyResultTests(unittest.TestCase):
    def test_sustained_spike_returns_one_backend_result(self) -> None:
        result = make_detector().detect(
            batch([(index * 1000, 130) for index in range(11)])
        )
        self.assertEqual(result.anomaly_kind, "spike")
        self.assertEqual(result.detected_at, BASE_TS + timedelta(seconds=10))
        self.assertEqual(result.window_start, BASE_TS)
        self.assertEqual(result.window_end, BASE_TS + timedelta(seconds=10))
        self.assertIsNone(result.severity)
        self.assertEqual(result.detector_version, DETECTOR_VERSION)
        self.assertIn("spike", result.explanation)
        self.assertIn("upper threshold", result.explanation)
        self.assertEqual(len(result.evidence), 11)
        self.assertEqual(
            set(result.evidence[-1]),
            {"observed_at", "heart_rate_bpm"},
        )
        self.assertEqual(result.evidence[-1]["heart_rate_bpm"], 130)

    def test_sustained_drop_returns_one_backend_result(self) -> None:
        result = make_detector().detect(
            batch([(index * 1000, 45) for index in range(11)])
        )
        self.assertEqual(result.anomaly_kind, "drop")
        self.assertIn("drop", result.explanation)
        self.assertIn("lower threshold", result.explanation)
        self.assertEqual(result.evidence[-1]["heart_rate_bpm"], 45)

    def test_result_contains_no_backend_ids_or_confidence(self) -> None:
        result = make_detector().detect(
            batch([(index * 1000, 130) for index in range(11)])
        )
        dumped = result.model_dump()
        self.assertNotIn("confidence", dumped)
        self.assertFalse(
            {
                "reading_id",
                "subject_id",
                "demo_run_id",
                "incident_id",
                "anomaly_event_id",
                "run_generation",
                "dedupe_key",
            }.intersection(dumped)
        )


class SessionTests(unittest.TestCase):
    def test_state_persists_across_calls(self) -> None:
        detector = make_detector()
        first = detector.detect(batch([(index * 1000, 130) for index in range(5)]))
        self.assertIsNone(first.anomaly_kind)

        second = detector.detect(batch([(index * 1000, 130) for index in range(5, 11)]))
        self.assertEqual(second.anomaly_kind, "spike")
        self.assertEqual(second.window_start, BASE_TS)
        self.assertEqual(second.detected_at, BASE_TS + timedelta(seconds=10))

    def test_custom_detector_version_is_carried(self) -> None:
        detector = make_detector(detector_version="contract-facade-v1")
        result = detector.detect([reading(0, 72)])
        self.assertEqual(result.detector_version, "contract-facade-v1")

    def test_offset_timestamps_are_normalized_to_utc(self) -> None:
        offset = timezone(timedelta(hours=5, minutes=30))
        detector = make_detector()
        result = detector.detect(
            [
                BackendDetectorReading(
                    observed_at=datetime(2026, 1, 1, 5, 30, tzinfo=offset),
                    heart_rate_bpm=72,
                )
            ]
        )
        self.assertEqual(result.detected_at, BASE_TS)
        self.assertEqual(result.detected_at.tzinfo, UTC)


class ContractFailureTests(unittest.TestCase):
    def test_multiple_anomalies_raise_without_mutating_state(self) -> None:
        detector = make_detector()
        timeline = [
            *((index * 1000, 130) for index in range(11)),
            (11000, 72),
            (12000, 72),
            *((index * 1000, 130) for index in range(13, 24)),
        ]
        before = detector.snapshot()
        with self.assertRaises(BackendDetectorContractError):
            detector.detect(batch(timeline))
        self.assertEqual(detector.snapshot(), before)

    def test_empty_batch_is_rejected_without_mutating_state(self) -> None:
        detector = make_detector()
        before = detector.snapshot()
        with self.assertRaises(ValueError):
            detector.detect([])
        self.assertEqual(detector.snapshot(), before)

    def test_wrong_item_type_is_rejected_without_mutating_state(self) -> None:
        detector = make_detector()
        before = detector.snapshot()
        with self.assertRaises(TypeError):
            detector.detect([reading(0, 72), object()])  # type: ignore[list-item]
        self.assertEqual(detector.snapshot(), before)

    def test_non_sequence_input_is_rejected(self) -> None:
        detector = make_detector()
        with self.assertRaises(TypeError):
            detector.detect(reading(0, 72))  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            detector.detect("not-a-batch")  # type: ignore[arg-type]

    def test_naive_timestamp_is_rejected_without_mutating_state(self) -> None:
        detector = make_detector()
        before = detector.snapshot()
        with self.assertRaises(ValueError):
            detector.detect(
                [
                    BackendDetectorReading(
                        observed_at=datetime(2026, 1, 1),
                        heart_rate_bpm=72,
                    )
                ]
            )
        self.assertEqual(detector.snapshot(), before)


class EvidenceTests(unittest.TestCase):
    def test_evidence_is_capped_to_backend_limit(self) -> None:
        config = DetectorConfig(
            persistence_ms=32_000,
            min_consecutive_abnormal_samples=5,
            evidence_window_ms=60_000,
            max_evidence_samples=60,
        )
        detector = BackendDetector(72.0, 4.0, config)
        result = detector.detect(batch([(index * 1000, 130) for index in range(40)]))
        self.assertEqual(len(result.evidence), BACKEND_EVIDENCE_LIMIT)
        self.assertEqual(
            result.evidence[-1],
            {
                "observed_at": (BASE_TS + timedelta(seconds=32))
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
                "heart_rate_bpm": 130,
            },
        )
        self.assertIn("32 most recent samples", result.explanation)

    def test_evidence_timestamps_are_utc_strings(self) -> None:
        result = make_detector().detect(
            batch([(index * 1000, 130) for index in range(11)])
        )
        for entry in result.evidence:
            self.assertIsInstance(entry["observed_at"], str)
            self.assertTrue(entry["observed_at"].endswith("Z"))
            self.assertIsInstance(entry["heart_rate_bpm"], int)


if __name__ == "__main__":
    unittest.main()
