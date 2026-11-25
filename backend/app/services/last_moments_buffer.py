"""Bounded transient monitoring buffer for recent heart-rate readings.

The core detector's evidence buffer is event-scoped: it retains only abnormal
samples for one emitted event and clears on normal readings. It cannot provide a
general recent-reading window before an incident. This separate buffer fills that
Role 1 monitoring need without persisting telemetry or adding database context.

One buffer belongs to one backend lifecycle context. Create a new buffer (or call
``reset``) when the subject/demo-run/generation context changes.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Deque, Optional, Tuple

from backend.app.services.anomaly_integration import DetectorReading

__all__ = [
    "BufferEvidence",
    "LastMomentsBuffer",
]


def _validate_aware(name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _validate_non_negative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


@dataclass(frozen=True)
class BufferEvidence:
    """Compact, bounded snapshot of buffered readings."""

    samples: Tuple[DetectorReading, ...]
    first_observed_at: Optional[datetime]
    last_observed_at: Optional[datetime]
    min_heart_rate_bpm: Optional[int]
    max_heart_rate_bpm: Optional[int]
    rejected_sample_count: int


class LastMomentsBuffer:
    """Ordered, UTC-normalized, count- and time-bounded reading buffer.

    The buffer is not thread-safe. It stores no subject/run/generation IDs and
    does not persist anything. Out-of-order or duplicate timestamps are rejected
    and counted; invalid reading objects raise ``TypeError`` before any change.
    """

    def __init__(self, max_samples: int = 60, retention_ms: int = 30_000) -> None:
        max_samples = _validate_non_negative_int("max_samples", max_samples)
        if max_samples < 1:
            raise ValueError("max_samples must be at least 1")
        retention_ms = _validate_non_negative_int("retention_ms", retention_ms)
        self._max_samples = max_samples
        self._retention_ms = retention_ms
        self._samples: Deque[DetectorReading] = deque(maxlen=max_samples)
        self._rejected_sample_count = 0

    @property
    def max_samples(self) -> int:
        return self._max_samples

    @property
    def retention_ms(self) -> int:
        return self._retention_ms

    @property
    def rejected_sample_count(self) -> int:
        return self._rejected_sample_count

    def append(self, reading: DetectorReading) -> bool:
        """Append one reading if it is newer than the latest stored reading.

        Returns ``True`` when stored and ``False`` when rejected as a duplicate
        or out-of-order timestamp. Rejections increment
        ``rejected_sample_count``. A wrong object type raises ``TypeError``.
        """

        if not isinstance(reading, DetectorReading):
            raise TypeError("reading must be a DetectorReading")

        observed_at = reading.observed_at.astimezone(UTC)
        if self._samples and observed_at <= self._samples[-1].observed_at:
            self._rejected_sample_count += 1
            return False

        normalized = DetectorReading(
            observed_at=observed_at,
            heart_rate_bpm=reading.heart_rate_bpm,
        )
        self._samples.append(normalized)
        self._prune(normalized.observed_at)
        return True

    def recent(self, limit: Optional[int] = None) -> Tuple[DetectorReading, ...]:
        """Return buffered readings in chronological order.

        ``limit=None`` returns all current samples. ``limit=0`` returns an empty
        tuple. A negative or non-integer limit raises ``ValueError``.
        """

        if limit is None:
            return tuple(self._samples)
        limit = _validate_non_negative_int("limit", limit)
        if limit == 0:
            return ()
        return tuple(self._samples)[-limit:]

    def window(
        self,
        start: datetime,
        end: datetime,
    ) -> Tuple[DetectorReading, ...]:
        """Return samples with ``start <= observed_at <= end`` (inclusive)."""

        start = _validate_aware("start", start).astimezone(UTC)
        end = _validate_aware("end", end).astimezone(UTC)
        if end < start:
            raise ValueError("end must not be earlier than start")
        return tuple(
            sample for sample in self._samples if start <= sample.observed_at <= end
        )

    def snapshot(self) -> BufferEvidence:
        """Return a compact evidence summary of the currently retained samples."""

        samples = tuple(self._samples)
        if not samples:
            return BufferEvidence(
                samples=(),
                first_observed_at=None,
                last_observed_at=None,
                min_heart_rate_bpm=None,
                max_heart_rate_bpm=None,
                rejected_sample_count=self._rejected_sample_count,
            )
        rates = [sample.heart_rate_bpm for sample in samples]
        return BufferEvidence(
            samples=samples,
            first_observed_at=samples[0].observed_at,
            last_observed_at=samples[-1].observed_at,
            min_heart_rate_bpm=min(rates),
            max_heart_rate_bpm=max(rates),
            rejected_sample_count=self._rejected_sample_count,
        )

    def reset(self) -> None:
        """Clear all samples and rejection counters for a new lifecycle context."""

        self._samples.clear()
        self._rejected_sample_count = 0

    def __len__(self) -> int:
        return len(self._samples)

    def _prune(self, latest: datetime) -> None:
        cutoff = latest - timedelta(milliseconds=self._retention_ms)
        while self._samples and self._samples[0].observed_at < cutoff:
            self._samples.popleft()
