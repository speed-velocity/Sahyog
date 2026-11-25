"""Tests for the bounded transient monitoring buffer."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.anomaly_integration import DetectorReading
from backend.app.services.last_moments_buffer import LastMomentsBuffer

UTC = timezone.utc
BASE_TS = datetime(2026, 1, 1, tzinfo=UTC)


def reading(t_ms: int, heart_rate_bpm: int = 72) -> DetectorReading:
    return DetectorReading(
        observed_at=BASE_TS + timedelta(milliseconds=t_ms),
        heart_rate_bpm=heart_rate_bpm,
    )


class BoundsTests(unittest.TestCase):
    def test_sample_count_is_bounded(self) -> None:
        buffer = LastMomentsBuffer(max_samples=3, retention_ms=60_000)
        for index in range(5):
            self.assertTrue(buffer.append(reading(index * 1000, 70 + index)))
        self.assertEqual(len(buffer), 3)
        self.assertEqual(
            [sample.heart_rate_bpm for sample in buffer.recent()],
            [72, 73, 74],
        )

    def test_retention_keeps_boundary_and_drops_older_samples(self) -> None:
        buffer = LastMomentsBuffer(max_samples=10, retention_ms=3000)
        for index in range(6):
            buffer.append(reading(index * 1000, 70 + index))
        self.assertEqual(
            [sample.observed_at for sample in buffer.recent()],
            [reading(index * 1000).observed_at for index in range(2, 6)],
        )
        buffer.append(reading(6000, 76))
        self.assertEqual(
            [sample.observed_at for sample in buffer.recent()],
            [reading(index * 1000).observed_at for index in range(3, 7)],
        )

    def test_zero_retention_keeps_only_latest(self) -> None:
        buffer = LastMomentsBuffer(max_samples=10, retention_ms=0)
        buffer.append(reading(0))
        buffer.append(reading(1000, 73))
        self.assertEqual(len(buffer), 1)
        self.assertEqual(buffer.recent()[0].heart_rate_bpm, 73)

    def test_max_samples_and_retention_both_apply(self) -> None:
        buffer = LastMomentsBuffer(max_samples=2, retention_ms=5000)
        for index in range(4):
            buffer.append(reading(index * 1000))
        self.assertEqual(len(buffer), 2)
        self.assertEqual(buffer.recent()[-1], reading(3000))

    def test_invalid_constructor_values_are_rejected(self) -> None:
        for max_samples in (0, -1, True, 1.5):
            with self.subTest(max_samples=max_samples):
                with self.assertRaises(ValueError):
                    LastMomentsBuffer(max_samples=max_samples)
        for retention_ms in (-1, True, 1.5):
            with self.subTest(retention_ms=retention_ms):
                with self.assertRaises(ValueError):
                    LastMomentsBuffer(retention_ms=retention_ms)


class OrderingTests(unittest.TestCase):
    def test_duplicate_and_out_of_order_samples_are_rejected(self) -> None:
        buffer = LastMomentsBuffer()
        self.assertTrue(buffer.append(reading(1000, 72)))
        self.assertFalse(buffer.append(reading(1000, 73)))
        self.assertFalse(buffer.append(reading(500, 74)))
        self.assertTrue(buffer.append(reading(2000, 75)))
        self.assertEqual(buffer.rejected_sample_count, 2)
        self.assertEqual(
            [sample.heart_rate_bpm for sample in buffer.recent()],
            [72, 75],
        )

    def test_naive_timestamp_cannot_be_constructed(self) -> None:
        with self.assertRaises(ValueError):
            DetectorReading(datetime(2026, 1, 1), 72)

    def test_wrong_sample_type_raises_without_mutation(self) -> None:
        buffer = LastMomentsBuffer()
        buffer.append(reading(0, 72))
        before = buffer.snapshot()
        with self.assertRaises(TypeError):
            buffer.append(object())  # type: ignore[arg-type]
        self.assertEqual(buffer.snapshot(), before)


class NormalizationTests(unittest.TestCase):
    def test_offset_aware_timestamps_are_stored_in_utc(self) -> None:
        offset = timezone(timedelta(hours=5, minutes=30))
        buffer = LastMomentsBuffer()
        buffer.append(
            DetectorReading(
                observed_at=datetime(2026, 1, 1, 5, 30, tzinfo=offset),
                heart_rate_bpm=72,
            )
        )
        stored = buffer.recent()[0]
        self.assertEqual(stored.observed_at, BASE_TS)
        self.assertEqual(stored.observed_at.tzinfo, UTC)

    def test_utc_equivalents_are_ordered_as_instants(self) -> None:
        offset = timezone(timedelta(hours=-4))
        buffer = LastMomentsBuffer()
        self.assertTrue(
            buffer.append(
                DetectorReading(
                    observed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                    heart_rate_bpm=70,
                )
            )
        )
        self.assertTrue(
            buffer.append(
                DetectorReading(
                    observed_at=datetime(2025, 12, 31, 20, 0, 1, tzinfo=offset),
                    heart_rate_bpm=71,
                )
            )
        )
        self.assertEqual(buffer.recent()[-1].heart_rate_bpm, 71)


class RetrievalTests(unittest.TestCase):
    def test_recent_limit_returns_latest_in_chronological_order(self) -> None:
        buffer = LastMomentsBuffer(max_samples=10)
        for index in range(5):
            buffer.append(reading(index * 1000, 70 + index))
        self.assertEqual(
            [sample.heart_rate_bpm for sample in buffer.recent(2)],
            [73, 74],
        )
        self.assertEqual(buffer.recent(0), ())
        with self.assertRaises(ValueError):
            buffer.recent(-1)

    def test_window_is_inclusive_and_bounded(self) -> None:
        buffer = LastMomentsBuffer(max_samples=10)
        for index in range(6):
            buffer.append(reading(index * 1000, 70 + index))
        result = buffer.window(reading(1000).observed_at, reading(3000).observed_at)
        self.assertEqual(
            [sample.heart_rate_bpm for sample in result],
            [71, 72, 73],
        )
        self.assertEqual(
            buffer.window(reading(1000).observed_at, reading(5000).observed_at)[-1],
            reading(5000, 75),
        )

    def test_window_normalizes_offsets(self) -> None:
        offset = timezone(timedelta(hours=5, minutes=30))
        buffer = LastMomentsBuffer()
        buffer.append(reading(0, 70))
        buffer.append(reading(1000, 71))
        result = buffer.window(
            datetime(2026, 1, 1, 5, 30, tzinfo=offset),
            datetime(2026, 1, 1, 5, 30, 1, tzinfo=offset),
        )
        self.assertEqual([sample.heart_rate_bpm for sample in result], [70, 71])

    def test_window_rejects_invalid_bounds(self) -> None:
        buffer = LastMomentsBuffer()
        with self.assertRaises(ValueError):
            buffer.window(reading(1000).observed_at, reading(0).observed_at)
        with self.assertRaises(ValueError):
            buffer.window(datetime(2026, 1, 1), reading(0).observed_at)
        with self.assertRaises(TypeError):
            buffer.window("start", reading(0).observed_at)

    def test_snapshot_is_compact_evidence(self) -> None:
        buffer = LastMomentsBuffer(max_samples=10)
        for index, rate in enumerate((80, 72, 64)):
            buffer.append(reading(index * 1000, rate))
        snapshot = buffer.snapshot()
        self.assertEqual(len(snapshot.samples), 3)
        self.assertEqual(snapshot.first_observed_at, BASE_TS)
        self.assertEqual(snapshot.last_observed_at, BASE_TS + timedelta(seconds=2))
        self.assertEqual(snapshot.min_heart_rate_bpm, 64)
        self.assertEqual(snapshot.max_heart_rate_bpm, 80)
        self.assertEqual(snapshot.rejected_sample_count, 0)

    def test_empty_snapshot_has_no_values(self) -> None:
        snapshot = LastMomentsBuffer().snapshot()
        self.assertEqual(snapshot.samples, ())
        self.assertIsNone(snapshot.first_observed_at)
        self.assertIsNone(snapshot.last_observed_at)
        self.assertIsNone(snapshot.min_heart_rate_bpm)
        self.assertIsNone(snapshot.max_heart_rate_bpm)


class LifecycleTests(unittest.TestCase):
    def test_reset_clears_samples_and_rejections(self) -> None:
        buffer = LastMomentsBuffer()
        buffer.append(reading(0, 72))
        buffer.append(reading(0, 73))
        self.assertEqual(len(buffer), 1)
        self.assertEqual(buffer.rejected_sample_count, 1)
        buffer.reset()
        self.assertEqual(len(buffer), 0)
        self.assertEqual(buffer.rejected_sample_count, 0)
        self.assertEqual(buffer.snapshot().samples, ())

    def test_old_context_samples_do_not_survive_reset(self) -> None:
        buffer = LastMomentsBuffer(retention_ms=60_000)
        buffer.append(reading(0, 72))
        buffer.append(reading(1000, 73))
        buffer.reset()
        buffer.append(reading(2000, 74))
        self.assertEqual([sample.heart_rate_bpm for sample in buffer.recent()], [74])


if __name__ == "__main__":
    unittest.main()
