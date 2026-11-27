"""Tests for the deterministic SAHYOG heart-rate anomaly detector.

Run from the repository root with:

    py -3.12 -m unittest backend.tests.test_anomaly -v
"""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.anomaly import (
    AnomalyDetector,
    AnomalyEvent,
    AnomalyEvidence,
    DetectorConfig,
    HrSample,
    compute_thresholds,
)

VECTORS_PATH = REPO_ROOT / "docs" / "anomaly_vectors.json"
BASE_TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def ms_to_dt(t_ms: int) -> datetime:
    return BASE_TS + timedelta(milliseconds=t_ms)


def dt_to_ms(value: datetime) -> int:
    delta = value - BASE_TS
    return int(delta.total_seconds() * 1000)


def config_from_document(document: dict) -> DetectorConfig:
    return DetectorConfig(**document["detector_config"])


def make_detector(
    mean: float | None = 72.0,
    std: float = 4.0,
    config: DetectorConfig | None = None,
) -> AnomalyDetector:
    detector = AnomalyDetector(config)
    if mean is not None:
        detector.set_baseline(mean, std)
    return detector


def feed(
    detector: AnomalyDetector,
    timeline: list[tuple[int, int]],
) -> list[AnomalyEvent]:
    events: list[AnomalyEvent] = []
    for t_ms, hr in timeline:
        event = detector.feed(HrSample(ms_to_dt(t_ms), hr))
        if event is not None:
            events.append(event)
    return events


def expand_vector(vector: dict) -> list[tuple[int, int]]:
    if "runs" in vector and "samples" in vector:
        raise ValueError(f"{vector['id']} defines both runs and samples")
    if "runs" in vector:
        samples: list[tuple[int, int]] = []
        for run in vector["runs"]:
            step = run["step_ms"]
            if step <= 0:
                raise ValueError(f"{vector['id']} has a non-positive step_ms")
            t_ms = run["from_ms"]
            while t_ms <= run["to_ms"]:
                samples.append((t_ms, run["heart_rate_bpm"]))
                t_ms += step
        return samples
    if "samples" in vector:
        return [
            (sample["t_ms"], sample["heart_rate_bpm"]) for sample in vector["samples"]
        ]
    raise ValueError(f"{vector['id']} defines neither runs nor samples")


class SharedVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
        cls.vectors = cls.document["vectors"]

    def test_vector_document_structure(self) -> None:
        self.assertEqual(self.document["schema_version"], "sahyog.anomaly_vectors.v1")
        self.assertTrue(self.document["status"].startswith("PROPOSED"))
        self.assertEqual(config_from_document(self.document), DetectorConfig())
        ids = [vector["id"] for vector in self.vectors]
        self.assertEqual(len(ids), len(set(ids)))
        required_coverage = {
            "normal_steady_30s",
            "sustained_spike",
            "sustained_drop",
            "gap_breaks_episode",
            "out_of_order_sample_rejected",
            "invalid_bpm_rejected",
            "no_baseline_no_events",
            "threshold_lower_exact_boundary",
            "threshold_lower_just_above",
            "threshold_upper_exact_boundary",
            "threshold_upper_just_below",
            "kind_change_starts_new_episode",
            "baseline_replacement_closes_episode",
        }
        self.assertTrue(required_coverage.issubset(set(ids)))
        for vector in self.vectors:
            with self.subTest(vector=vector["id"]):
                self.assertTrue(vector["description"])
                self.assertIn("baseline_bpm", vector)
                self.assertIn("expected", vector)
                self.assertEqual(
                    len(vector["expected"]["events"]),
                    vector["expected"]["event_count"],
                )
                if "runs" in vector:
                    self.assertNotIn("samples", vector)
                else:
                    self.assertIn("samples", vector)

    def test_all_vectors_match_expected_behavior(self) -> None:
        for vector in self.vectors:
            with self.subTest(vector=vector["id"]):
                config = replace(
                    config_from_document(self.document),
                    **vector.get("config_overrides", {}),
                )
                detector = AnomalyDetector(config)
                baseline = vector["baseline_bpm"]
                if baseline is not None:
                    detector.set_baseline(baseline["mean"], baseline["std"])

                replacements = sorted(
                    vector.get("baseline_replacements", []),
                    key=lambda replacement: replacement["before_t_ms"],
                )
                replacement_index = 0
                produced: list[tuple[AnomalyEvent, AnomalyEvidence]] = []

                for t_ms, hr in expand_vector(vector):
                    while (
                        replacement_index < len(replacements)
                        and t_ms >= replacements[replacement_index]["before_t_ms"]
                    ):
                        replacement = replacements[replacement_index]
                        detector.set_baseline(replacement["mean"], replacement["std"])
                        replacement_index += 1

                    event = detector.feed(HrSample(ms_to_dt(t_ms), hr))
                    if event is not None:
                        evidence = detector.last_event_evidence
                        self.assertIsNotNone(evidence)
                        produced.append((event, evidence))

                self.assertEqual(replacement_index, len(replacements))
                expected = vector["expected"]
                self.assertEqual(len(produced), expected["event_count"], vector["id"])

                for (event, evidence), expected_event in zip(
                    produced, expected["events"]
                ):
                    self.assertEqual(event.kind, expected_event["kind"])
                    self.assertEqual(
                        dt_to_ms(event.started_at), expected_event["started_at_ms"]
                    )
                    self.assertEqual(
                        dt_to_ms(evidence.detected_at),
                        expected_event["detected_at_ms"],
                    )
                    self.assertEqual(event.last_hr, expected_event["last_hr"])
                    self.assertEqual(
                        evidence.abnormal_duration_ms,
                        expected_event["abnormal_duration_ms"],
                    )
                    self.assertEqual(
                        evidence.abnormal_sample_count,
                        expected_event["abnormal_sample_count"],
                    )
                    self.assertEqual(
                        evidence.extreme_heart_rate_bpm,
                        expected_event["extreme_heart_rate_bpm"],
                    )
                    self.assertEqual(evidence.kind, event.kind)
                    self.assertEqual(evidence.first_abnormal_at, event.started_at)
                    self.assertTrue(evidence.samples)
                    self.assertEqual(
                        evidence.samples[-1],
                        (evidence.detected_at, event.last_hr),
                    )
                    self.assertLessEqual(
                        len(evidence.samples), config.max_evidence_samples
                    )
                    self.assertLessEqual(
                        dt_to_ms(evidence.detected_at)
                        - dt_to_ms(evidence.samples[0][0]),
                        config.evidence_window_ms,
                    )
                    thresholds = compute_thresholds(
                        evidence.baseline_mean_bpm,
                        evidence.baseline_std_bpm,
                        config,
                    )
                    self.assertEqual(
                        evidence.effective_delta_bpm,
                        thresholds.effective_delta_bpm,
                    )
                    self.assertEqual(
                        evidence.lower_threshold_bpm,
                        thresholds.lower_threshold_bpm,
                    )
                    self.assertEqual(
                        evidence.upper_threshold_bpm,
                        thresholds.upper_threshold_bpm,
                    )

                snapshot = detector.snapshot()
                expected_state = expected["final_state"]
                self.assertEqual(
                    snapshot.accepted_sample_count,
                    expected_state["accepted_sample_count"],
                )
                self.assertEqual(
                    dt_to_ms(snapshot.last_accepted_ts),
                    expected_state["last_accepted_t_ms"],
                )
                self.assertEqual(
                    snapshot.active_episode_kind,
                    expected_state["active_episode_kind"],
                )
                self.assertEqual(
                    snapshot.episode_event_emitted,
                    expected_state["event_emitted_in_episode"],
                )
                self.assertEqual(
                    snapshot.consecutive_abnormal_samples,
                    expected_state["consecutive_abnormal_samples"],
                )
                self.assertEqual(
                    snapshot.consecutive_normal_samples,
                    expected_state["consecutive_normal_samples"],
                )
                self.assertEqual(
                    snapshot.rejected_sample_count,
                    expected["rejected_sample_count"],
                )


class ThresholdTests(unittest.TestCase):
    def test_default_thresholds_use_min_abs_delta(self) -> None:
        thresholds = compute_thresholds(72.0, 4.0)
        self.assertEqual(thresholds.effective_delta_bpm, 15.0)
        self.assertEqual(thresholds.lower_threshold_bpm, 57.0)
        self.assertEqual(thresholds.upper_threshold_bpm, 87.0)

    def test_z_margin_dominates_above_std_floor(self) -> None:
        thresholds = compute_thresholds(72.0, 10.0)
        self.assertEqual(thresholds.effective_delta_bpm, 30.0)
        self.assertEqual(thresholds.lower_threshold_bpm, 42.0)
        self.assertEqual(thresholds.upper_threshold_bpm, 102.0)

    def test_std_floor_protects_zero_std(self) -> None:
        thresholds = compute_thresholds(72.0, 0.0)
        self.assertEqual(thresholds.effective_delta_bpm, 15.0)

    def test_custom_config_changes_thresholds(self) -> None:
        config = DetectorConfig(
            z_threshold=2.0, std_floor_bpm=1.0, min_abs_delta_bpm=5.0
        )
        thresholds = compute_thresholds(60.0, 4.0, config)
        self.assertEqual(thresholds.effective_delta_bpm, 8.0)
        self.assertEqual(thresholds.lower_threshold_bpm, 52.0)
        self.assertEqual(thresholds.upper_threshold_bpm, 68.0)

    def test_lower_boundary_is_inclusive(self) -> None:
        detector = make_detector()
        events = feed(detector, [(index * 1000, 57) for index in range(11)])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "drop")
        self.assertEqual(dt_to_ms(events[0].started_at), 0)
        self.assertEqual(events[0].last_hr, 57)

    def test_upper_boundary_is_inclusive(self) -> None:
        detector = make_detector()
        events = feed(detector, [(index * 1000, 87) for index in range(11)])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "spike")
        self.assertEqual(events[0].last_hr, 87)

    def test_values_one_bpm_inside_boundaries_are_normal(self) -> None:
        for heart_rate in (58, 86):
            with self.subTest(heart_rate=heart_rate):
                detector = make_detector()
                events = feed(
                    detector, [(index * 1000, heart_rate) for index in range(21)]
                )
                self.assertEqual(events, [])
                self.assertIsNone(detector.snapshot().active_episode_kind)

    def test_threshold_validation(self) -> None:
        invalid = [
            (10.0, 4.0),
            (260.0, 4.0),
            (72.0, -1.0),
            (72.0, float("nan")),
            (72.0, float("inf")),
            (float("nan"), 4.0),
            (float("inf"), 4.0),
            ("72", 4.0),
            (True, 4.0),
            (72.0, True),
        ]
        for mean, std in invalid:
            with self.subTest(mean=mean, std=std):
                with self.assertRaises(ValueError):
                    compute_thresholds(mean, std)


class ConfigurationValidationTests(unittest.TestCase):
    def test_invalid_config_values_are_rejected(self) -> None:
        invalid_overrides = [
            {"z_threshold": 0},
            {"z_threshold": -1},
            {"z_threshold": float("nan")},
            {"z_threshold": True},
            {"std_floor_bpm": -1},
            {"std_floor_bpm": float("inf")},
            {"min_abs_delta_bpm": 0},
            {"persistence_ms": -1},
            {"persistence_ms": 1.5},
            {"persistence_ms": True},
            {"min_consecutive_abnormal_samples": 0},
            {"max_gap_ms": -1},
            {"normal_confirm_samples": 0},
            {"valid_bpm_min": -1},
            {"valid_bpm_max": 0},
            {"valid_bpm_min": 100, "valid_bpm_max": 100},
            {"evidence_window_ms": -1},
            {"max_evidence_samples": 0},
        ]
        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    DetectorConfig(**overrides)

    def test_valid_custom_config_is_accepted(self) -> None:
        config = DetectorConfig(
            z_threshold=2.5,
            std_floor_bpm=1.0,
            min_abs_delta_bpm=10.0,
            persistence_ms=5000,
            min_consecutive_abnormal_samples=3,
            max_gap_ms=2000,
            normal_confirm_samples=3,
            valid_bpm_min=30,
            valid_bpm_max=220,
            evidence_window_ms=10000,
            max_evidence_samples=20,
        )
        detector = AnomalyDetector(config)
        self.assertIs(detector.config, config)

    def test_overflowing_numeric_values_are_rejected(self) -> None:
        huge = 10**400
        with self.assertRaises(ValueError):
            DetectorConfig(z_threshold=huge)
        with self.assertRaises(ValueError):
            compute_thresholds(huge, 4.0)
        with self.assertRaises(ValueError):
            AnomalyDetector().set_baseline(huge, 4.0)


class BaselineTests(unittest.TestCase):
    def test_detector_has_no_thresholds_without_baseline(self) -> None:
        detector = AnomalyDetector()
        self.assertIsNone(detector.thresholds)
        events = feed(detector, [(index * 1000, 130) for index in range(31)])
        self.assertEqual(events, [])
        snapshot = detector.snapshot()
        self.assertIsNone(snapshot.baseline_mean_bpm)
        self.assertIsNone(snapshot.active_episode_kind)
        self.assertEqual(snapshot.accepted_sample_count, 31)

    def test_set_baseline_enables_thresholds(self) -> None:
        detector = AnomalyDetector()
        detector.set_baseline(80, 5)
        thresholds = detector.thresholds
        self.assertIsNotNone(thresholds)
        self.assertEqual(thresholds.lower_threshold_bpm, 65.0)
        self.assertEqual(thresholds.upper_threshold_bpm, 95.0)

    def test_invalid_baseline_values_are_rejected(self) -> None:
        invalid = [
            (float("nan"), 4.0),
            (float("inf"), 4.0),
            (float("-inf"), 4.0),
            (72.0, -0.1),
            (72.0, float("nan")),
            (19, 4.0),
            (251, 4.0),
            ("72", 4.0),
            (True, 4.0),
            (72.0, True),
        ]
        for mean, std in invalid:
            with self.subTest(mean=mean, std=std):
                detector = AnomalyDetector()
                with self.assertRaises(ValueError):
                    detector.set_baseline(mean, std)
                self.assertIsNone(detector.thresholds)

    def test_invalid_baseline_does_not_change_active_state(self) -> None:
        detector = make_detector()
        feed(detector, [(0, 130)])
        before = detector.snapshot()
        with self.assertRaises(ValueError):
            detector.set_baseline(float("nan"), 4.0)
        self.assertEqual(detector.snapshot(), before)
        self.assertEqual(detector.thresholds.lower_threshold_bpm, 57.0)

    def test_baseline_replacement_closes_episode_without_event(self) -> None:
        detector = make_detector()
        events = feed(detector, [(index * 1000, 130) for index in range(5)])
        self.assertEqual(events, [])
        self.assertEqual(detector.snapshot().active_episode_kind, "spike")

        detector.set_baseline(120, 4)
        snapshot = detector.snapshot()
        self.assertIsNone(snapshot.active_episode_kind)
        self.assertFalse(snapshot.episode_event_emitted)
        self.assertEqual(snapshot.consecutive_abnormal_samples, 0)
        self.assertIsNone(snapshot.last_event_evidence)
        self.assertEqual(snapshot.last_accepted_ts, ms_to_dt(4000))

        events = feed(detector, [(5000, 130)])
        self.assertEqual(events, [])
        self.assertIsNone(detector.snapshot().active_episode_kind)


class SampleValidationTests(unittest.TestCase):
    def test_non_sample_is_rejected(self) -> None:
        detector = make_detector()
        self.assertIsNone(detector.feed(None))
        self.assertEqual(detector.snapshot().rejected_sample_count, 1)

    def test_invalid_heart_rates_are_rejected(self) -> None:
        detector = make_detector()
        invalid_values = (0, 19, 251, 300, 72.0, True, "72", None)
        for heart_rate in invalid_values:
            with self.subTest(heart_rate=heart_rate):
                self.assertIsNone(detector.feed(HrSample(BASE_TS, heart_rate)))
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.accepted_sample_count, 0)
        self.assertEqual(snapshot.rejected_sample_count, len(invalid_values))
        self.assertIsNone(snapshot.last_accepted_ts)

    def test_non_datetime_timestamp_is_rejected(self) -> None:
        detector = make_detector()
        self.assertIsNone(detector.feed(HrSample("2026-01-01T00:00:00Z", 72)))
        self.assertEqual(detector.snapshot().rejected_sample_count, 1)

    def test_naive_timestamps_are_rejected(self) -> None:
        detector = make_detector()
        naive_start = datetime(2026, 1, 1, 0, 0, 0)
        # Naive timestamps must be rejected; the detector requires UTC-aware timestamps.
        self.assertIsNone(detector.feed(HrSample(naive_start, 72)))
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.accepted_sample_count, 0)
        self.assertEqual(snapshot.rejected_sample_count, 1)
        self.assertIsNone(snapshot.last_accepted_ts)

        # Aware UTC timestamps are accepted (sample counted) even when no anomaly
        # is emitted — normal readings return None from feed but increment
        # accepted_sample_count.
        result = detector.feed(HrSample(BASE_TS, 72))
        self.assertIsNone(result)
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.accepted_sample_count, 1)
        self.assertEqual(snapshot.rejected_sample_count, 1)
        self.assertEqual(snapshot.last_accepted_ts, BASE_TS)

        # A later aware timestamp is also accepted.
        result = detector.feed(HrSample(BASE_TS + timedelta(seconds=1), 72))
        self.assertIsNone(result)
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.accepted_sample_count, 2)
        self.assertEqual(snapshot.rejected_sample_count, 1)

    def test_equal_and_out_of_order_samples_are_rejected(self) -> None:
        detector = make_detector()
        detector.feed(HrSample(ms_to_dt(0), 72))
        detector.feed(HrSample(ms_to_dt(0), 72))
        detector.feed(HrSample(ms_to_dt(-1000), 72))
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.accepted_sample_count, 1)
        self.assertEqual(snapshot.rejected_sample_count, 2)
        self.assertEqual(snapshot.last_accepted_ts, ms_to_dt(0))

    def test_rejections_do_not_change_episode_state(self) -> None:
        detector = make_detector()
        feed(detector, [(0, 72), (1000, 130)])
        before = detector.snapshot()
        detector.feed(HrSample(ms_to_dt(500), 130))
        after = detector.snapshot()
        self.assertEqual(after.accepted_sample_count, before.accepted_sample_count)
        self.assertEqual(after.last_accepted_ts, before.last_accepted_ts)
        self.assertEqual(after.active_episode_kind, before.active_episode_kind)
        self.assertEqual(
            after.consecutive_abnormal_samples,
            before.consecutive_abnormal_samples,
        )
        self.assertEqual(
            after.consecutive_normal_samples, before.consecutive_normal_samples
        )
        self.assertEqual(after.episode_event_emitted, before.episode_event_emitted)
        self.assertEqual(after.rejected_sample_count, 1)

        detector.feed(HrSample(ms_to_dt(2000), 300))
        after = detector.snapshot()
        self.assertEqual(after.accepted_sample_count, before.accepted_sample_count)
        self.assertEqual(after.last_accepted_ts, before.last_accepted_ts)
        self.assertEqual(after.active_episode_kind, before.active_episode_kind)
        self.assertEqual(
            after.consecutive_abnormal_samples,
            before.consecutive_abnormal_samples,
        )
        self.assertEqual(after.rejected_sample_count, 2)

    def test_rejected_sample_does_not_advance_last_accepted_time(self) -> None:
        detector = make_detector()
        feed(detector, [(0, 72)])
        detector.feed(HrSample(ms_to_dt(5000), 300))
        detector.feed(HrSample(ms_to_dt(1000), 72))
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.accepted_sample_count, 2)
        self.assertEqual(snapshot.last_accepted_ts, ms_to_dt(1000))


class PersistenceTests(unittest.TestCase):
    def test_event_waits_for_duration_after_minimum_count(self) -> None:
        config = DetectorConfig(
            persistence_ms=10000, min_consecutive_abnormal_samples=3
        )
        detector = make_detector(config=config)
        self.assertEqual(feed(detector, [(0, 130), (1000, 130), (2000, 130)]), [])
        events = feed(detector, [(5000, 130), (8000, 130), (10000, 130)])
        self.assertEqual(len(events), 1)
        self.assertEqual(dt_to_ms(events[0].started_at), 0)
        self.assertEqual(dt_to_ms(detector.last_event_evidence.detected_at), 10000)

    def test_event_waits_for_minimum_count_after_duration(self) -> None:
        config = DetectorConfig(
            persistence_ms=10000, min_consecutive_abnormal_samples=10
        )
        detector = make_detector(config=config)
        events = feed(detector, [(index * 2000, 130) for index in range(6)])
        self.assertEqual(events, [])
        events = feed(detector, [(index * 2000, 130) for index in range(6, 10)])
        self.assertEqual(len(events), 1)
        self.assertEqual(dt_to_ms(events[0].started_at), 0)
        self.assertEqual(dt_to_ms(detector.last_event_evidence.detected_at), 18000)
        self.assertEqual(detector.last_event_evidence.abnormal_sample_count, 10)

    def test_normal_sample_restarts_persistence_run(self) -> None:
        detector = make_detector()
        events = feed(detector, [(index * 1000, 130) for index in range(5)])
        self.assertEqual(events, [])
        self.assertEqual(detector.snapshot().consecutive_abnormal_samples, 5)
        events = feed(detector, [(5000, 72)])
        self.assertEqual(events, [])
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.active_episode_kind, "spike")
        self.assertEqual(snapshot.consecutive_abnormal_samples, 0)
        self.assertEqual(snapshot.consecutive_normal_samples, 1)

        events = feed(detector, [(t_ms, 130) for t_ms in range(6000, 17000, 1000)])
        self.assertEqual(len(events), 1)
        self.assertEqual(dt_to_ms(events[0].started_at), 6000)
        self.assertEqual(dt_to_ms(detector.last_event_evidence.detected_at), 16000)
        self.assertEqual(len(events), 1)

    def test_only_one_event_per_episode(self) -> None:
        detector = make_detector()
        events = feed(detector, [(index * 1000, 130) for index in range(31)])
        self.assertEqual(len(events), 1)
        self.assertEqual(dt_to_ms(events[0].started_at), 0)
        self.assertTrue(detector.snapshot().episode_event_emitted)
        self.assertEqual(detector.snapshot().consecutive_abnormal_samples, 31)

    def test_normal_confirmation_closes_episode(self) -> None:
        detector = make_detector()
        events = feed(detector, [(index * 1000, 130) for index in range(11)])
        self.assertEqual(len(events), 1)
        feed(detector, [(11000, 72)])
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.active_episode_kind, "spike")
        self.assertEqual(snapshot.consecutive_normal_samples, 1)
        feed(detector, [(12000, 72)])
        snapshot = detector.snapshot()
        self.assertIsNone(snapshot.active_episode_kind)
        self.assertEqual(snapshot.consecutive_normal_samples, 0)

    def test_gap_equal_to_max_gap_preserves_run(self) -> None:
        config = DetectorConfig(max_gap_ms=5000)
        detector = make_detector(config=config)
        events = feed(
            detector,
            [
                (0, 130),
                (1000, 130),
                (2000, 130),
                (3000, 130),
                (4000, 130),
                (9000, 130),
                (10000, 130),
            ],
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(dt_to_ms(events[0].started_at), 0)
        self.assertEqual(detector.last_event_evidence.abnormal_sample_count, 7)

    def test_gap_greater_than_max_gap_breaks_run(self) -> None:
        config = DetectorConfig(max_gap_ms=5000)
        detector = make_detector(config=config)
        events = feed(detector, [(index * 1000, 130) for index in range(5)])
        self.assertEqual(events, [])
        events = feed(detector, [(index * 1000, 130) for index in range(10, 21)])
        self.assertEqual(len(events), 1)
        self.assertEqual(dt_to_ms(events[0].started_at), 10000)
        self.assertEqual(dt_to_ms(detector.last_event_evidence.detected_at), 20000)

    def test_kind_change_starts_new_episode(self) -> None:
        detector = make_detector()
        events = feed(detector, [(index * 1000, 130) for index in range(5)])
        self.assertEqual(events, [])
        events = feed(detector, [(index * 1000, 45) for index in range(5, 16)])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "drop")
        self.assertEqual(dt_to_ms(events[0].started_at), 5000)
        self.assertEqual(dt_to_ms(detector.last_event_evidence.detected_at), 15000)

    def test_event_last_hr_is_the_completing_sample(self) -> None:
        detector = make_detector()
        timeline = [
            (0, 100),
            (1000, 130),
            (2000, 140),
            (3000, 150),
            (4000, 160),
            (5000, 170),
            (6000, 180),
            (7000, 190),
            (8000, 200),
            (9000, 210),
            (10000, 220),
        ]
        events = feed(detector, timeline)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].last_hr, 220)
        evidence = detector.last_event_evidence
        self.assertEqual(evidence.extreme_heart_rate_bpm, 220)
        self.assertEqual(evidence.first_abnormal_at, ms_to_dt(0))


class EvidenceAndResetTests(unittest.TestCase):
    def test_event_contract_has_no_backend_fields(self) -> None:
        event_fields = {field.name for field in fields(AnomalyEvent)}
        self.assertEqual(event_fields, {"started_at", "last_hr", "kind"})
        forbidden = {
            "detector_result",
            "severity",
            "dedupe_key",
            "detector_version",
            "incident_id",
            "subject_id",
            "demo_run_id",
            "generation_id",
        }
        self.assertFalse(forbidden.intersection(event_fields))
        evidence_fields = {field.name for field in fields(AnomalyEvidence)}
        self.assertFalse(forbidden.intersection(evidence_fields))

    def test_evidence_is_bounded_by_max_samples(self) -> None:
        config = DetectorConfig(max_evidence_samples=5)
        detector = make_detector(config=config)
        events = feed(detector, [(index * 1000, 130) for index in range(11)])
        self.assertEqual(len(events), 1)
        evidence = detector.last_event_evidence
        self.assertEqual(len(evidence.samples), 5)
        self.assertEqual(evidence.samples[0][0], ms_to_dt(6000))
        self.assertEqual(evidence.samples[-1][0], ms_to_dt(10000))

    def test_evidence_window_prunes_old_samples(self) -> None:
        config = DetectorConfig(evidence_window_ms=3000)
        detector = make_detector(config=config)
        events = feed(detector, [(index * 1000, 130) for index in range(11)])
        self.assertEqual(len(events), 1)
        evidence = detector.last_event_evidence
        self.assertEqual(evidence.samples[0][0], ms_to_dt(7000))
        self.assertEqual(evidence.samples[-1][0], ms_to_dt(10000))
        self.assertEqual(len(evidence.samples), 4)

    def test_reset_clears_state_but_keeps_config(self) -> None:
        config = DetectorConfig(max_gap_ms=4000)
        detector = make_detector(config=config)
        feed(detector, [(index * 1000, 130) for index in range(11)])
        self.assertIsNotNone(detector.snapshot().last_event_evidence)
        detector.reset()
        self.assertEqual(detector.snapshot(), AnomalyDetector(config).snapshot())
        self.assertEqual(detector.snapshot().rejected_sample_count, 0)
        self.assertIsNone(detector.last_event_evidence)
        events = feed(detector, [(0, 130)])
        self.assertEqual(events, [])
        self.assertIsNone(detector.snapshot().active_episode_kind)

    def test_baseline_replacement_keeps_last_accepted_time(self) -> None:
        detector = make_detector()
        feed(detector, [(0, 72)])
        detector.set_baseline(120, 4)
        snapshot = detector.snapshot()
        self.assertEqual(snapshot.last_accepted_ts, ms_to_dt(0))
        self.assertEqual(snapshot.accepted_sample_count, 1)
        events = feed(detector, [(1000, 130)])
        self.assertEqual(events, [])
        self.assertEqual(detector.snapshot().accepted_sample_count, 2)


if __name__ == "__main__":
    unittest.main()
