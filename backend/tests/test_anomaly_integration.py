"""Tests for the typed detector integration interface."""

from __future__ import annotations

import sys
import unittest
from dataclasses import fields
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.anomaly import HrSample
from backend.app.services.anomaly_integration import (
    DETECTOR_VERSION,
    AnomalyDetectorSession,
    DetectedAnomaly,
    DetectorReading,
    DetectorResult,
    map_detector_result,
)

BASE_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def reading(t_ms: int, heart_rate_bpm: int) -> DetectorReading:
    return DetectorReading(
        observed_at=BASE_TS + timedelta(milliseconds=t_ms),
        heart_rate_bpm=heart_rate_bpm,
    )


def batch(timeline: list[tuple[int, int]]) -> list[DetectorReading]:
    return [reading(t_ms, heart_rate_bpm) for t_ms, heart_rate_bpm in timeline]


def make_session(
    mean: float = 72.0,
    std: float = 4.0,
) -> AnomalyDetectorSession:
    return AnomalyDetectorSession(mean, std)


class DetectorReadingTests(unittest.TestCase):
    def test_conversion_preserves_timestamp_and_rate(self) -> None:
        original = reading(1234, 78)
        sample = original.to_hr_sample()
        self.assertIsInstance(sample, HrSample)
        self.assertEqual(sample.ts, original.observed_at)
        self.assertEqual(sample.hr, original.heart_rate_bpm)
        self.assertEqual(DetectorReading.from_hr_sample(sample), original)

    def test_timezone_aware_datetime_is_required(self) -> None:
        with self.assertRaises(ValueError):
            DetectorReading(datetime(2026, 1, 1), 72)
        with self.assertRaises(TypeError):
            DetectorReading("2026-01-01T00:00:00Z", 72)

    def test_integer_heart_rate_is_required(self) -> None:
        for invalid in (72.0, True, "72", None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(TypeError):
                    DetectorReading(BASE_TS, invalid)

    def test_naive_hr_sample_conversion_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DetectorReading.from_hr_sample(HrSample(datetime(2026, 1, 1), 72))


class DetectorSessionTests(unittest.TestCase):
    def test_empty_batch_is_a_noop(self) -> None:
        session = make_session()
        before = session.snapshot()
        result = session.detect([])
        self.assertEqual(result, DetectorResult())
        self.assertFalse(result.has_anomaly)
        self.assertEqual(result.anomaly_events, ())
        self.assertEqual(session.snapshot(), before)

    def test_single_reading_is_accepted_without_an_event(self) -> None:
        session = make_session()
        result = session.detect([reading(0, 72)])
        self.assertFalse(result.has_anomaly)
        self.assertEqual(result.accepted_readings, 1)
        self.assertEqual(result.rejected_readings, 0)

    def test_normal_sequence_emits_no_anomaly(self) -> None:
        session = make_session()
        result = session.detect(batch([(index * 1000, 72) for index in range(10)]))
        self.assertFalse(result.has_anomaly)
        self.assertEqual(result.accepted_readings, 10)
        self.assertEqual(result.rejected_readings, 0)

    def test_sustained_spike_maps_to_hr_spike(self) -> None:
        session = make_session()
        result = session.detect(batch([(index * 1000, 130) for index in range(11)]))
        self.assertTrue(result.has_anomaly)
        self.assertEqual(len(result.anomalies), 1)
        anomaly = result.anomalies[0]
        self.assertEqual(anomaly.detector_result, "HR_SPIKE")
        self.assertEqual(anomaly.event.kind, "spike")
        self.assertIsNone(anomaly.severity)
        self.assertEqual(anomaly.detector_version, DETECTOR_VERSION)
        self.assertEqual(anomaly.observation_window_start, BASE_TS)
        self.assertEqual(
            anomaly.observation_window_end, BASE_TS + timedelta(seconds=10)
        )
        self.assertEqual(result.anomaly_events, (anomaly.event,))

    def test_sustained_drop_maps_to_hr_drop(self) -> None:
        session = make_session()
        result = session.detect(batch([(index * 1000, 45) for index in range(11)]))
        self.assertEqual(len(result.anomalies), 1)
        self.assertEqual(result.anomalies[0].detector_result, "HR_DROP")
        self.assertEqual(result.anomalies[0].event.kind, "drop")

    def test_multiple_events_retain_separate_evidence(self) -> None:
        session = make_session()
        timeline = [
            *((index * 1000, 130) for index in range(11)),
            (11000, 72),
            (12000, 72),
            *((index * 1000, 130) for index in range(13, 24)),
        ]
        result = session.detect(batch(timeline))
        self.assertEqual(len(result.anomalies), 2)
        first, second = result.anomalies
        self.assertEqual(first.event.started_at, BASE_TS)
        self.assertEqual(first.evidence.detected_at, BASE_TS + timedelta(seconds=10))
        self.assertEqual(second.event.started_at, BASE_TS + timedelta(seconds=13))
        self.assertEqual(second.evidence.detected_at, BASE_TS + timedelta(seconds=23))
        self.assertNotEqual(first.evidence.samples, second.evidence.samples)

    def test_state_persists_across_calls(self) -> None:
        session = make_session()
        first = session.detect(batch([(index * 1000, 130) for index in range(5)]))
        self.assertFalse(first.has_anomaly)
        self.assertEqual(first.accepted_readings, 5)

        second = session.detect(batch([(index * 1000, 130) for index in range(5, 11)]))
        self.assertEqual(len(second.anomalies), 1)
        self.assertEqual(second.anomalies[0].event.started_at, BASE_TS)
        self.assertEqual(
            second.anomalies[0].evidence.detected_at,
            BASE_TS + timedelta(seconds=10),
        )

    def test_invalid_and_out_of_order_readings_are_counted(self) -> None:
        session = make_session()
        result = session.detect(
            [
                reading(0, 72),
                reading(-1000, 72),
                reading(1000, 300),
                reading(2000, 72),
            ]
        )
        self.assertFalse(result.has_anomaly)
        self.assertEqual(result.accepted_readings, 2)
        self.assertEqual(result.rejected_readings, 2)

    def test_wrong_element_type_raises_before_mutating_state(self) -> None:
        session = make_session()
        session.detect(batch([(0, 72)]))
        before = session.snapshot()
        with self.assertRaises(TypeError):
            session.detect([reading(1000, 72), object()])  # type: ignore[list-item]
        self.assertEqual(session.snapshot(), before)

    def test_invalid_baseline_prevents_session_creation(self) -> None:
        with self.assertRaises(ValueError):
            AnomalyDetectorSession(float("nan"), 4.0)
        with self.assertRaises(ValueError):
            AnomalyDetectorSession(72.0, -1.0)

    def test_detector_version_is_carried_into_events(self) -> None:
        session = AnomalyDetectorSession(72.0, 4.0, detector_version="contract-test-v1")
        result = session.detect(batch([(index * 1000, 130) for index in range(11)]))
        self.assertEqual(result.anomalies[0].detector_version, "contract-test-v1")


class ResultContractTests(unittest.TestCase):
    def test_result_contains_no_confidence_or_database_fields(self) -> None:
        anomaly_fields = {field.name for field in fields(DetectedAnomaly)}
        self.assertNotIn("confidence", anomaly_fields)
        self.assertFalse(
            {
                "reading_id",
                "subject_id",
                "demo_run_id",
                "incident_id",
                "anomaly_event_id",
                "run_generation",
                "dedupe_key",
            }.intersection(anomaly_fields)
        )

    def test_mapping_rejects_unknown_kind(self) -> None:
        with self.assertRaises(ValueError):
            map_detector_result("unknown")  # type: ignore[arg-type]

    def test_result_rejects_negative_counts(self) -> None:
        with self.assertRaises(ValueError):
            DetectorResult(accepted_readings=-1)


if __name__ == "__main__":
    unittest.main()
