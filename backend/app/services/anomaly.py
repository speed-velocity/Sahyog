"""Deterministic heart-rate anomaly detector for SAHYOG.

This module is deliberately independent of FastAPI, SQLAlchemy, the API layer,
the scripts and hardware. It uses only the Python standard library and produces
no database identifiers, subject identifiers, demo-run identifiers, run
generations or backend lifecycle fields.

The detector is rule-based, not a trained model. All default values are proposed
demo parameters, not clinical thresholds. See ``docs/thresholds.md``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from typing import Deque, Literal, Optional, Tuple

__all__ = [
    "AnomalyDetector",
    "AnomalyEvent",
    "AnomalyEvidence",
    "AnomalyKind",
    "DetectorConfig",
    "DetectorSnapshot",
    "HrSample",
    "Thresholds",
    "compute_thresholds",
]

AnomalyKind = Literal["drop", "spike"]

_EVIDENCE_SAMPLE = Tuple[datetime, int]


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_finite(
    name: str,
    value: object,
    *,
    minimum: Optional[float] = None,
    strictly_positive: bool = False,
) -> None:
    if not _is_number(value):
        raise ValueError(f"{name} must be a finite number")
    try:
        numeric = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not isfinite(numeric):
        raise ValueError(f"{name} must be a finite number")
    if strictly_positive and numeric <= 0:
        raise ValueError(f"{name} must be greater than zero")
    if minimum is not None and numeric < minimum:
        raise ValueError(f"{name} must be greater than or equal to {minimum}")


def _require_int(name: str, value: object, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be greater than or equal to {minimum}")


@dataclass(frozen=True)
class DetectorConfig:
    """Configuration for :class:`AnomalyDetector`.

    Defaults are the proposed demo parameters in ``docs/thresholds.md``. They
    are not approved team-wide values and are not clinical thresholds.
    """

    z_threshold: float = 3.0
    std_floor_bpm: float = 2.0
    min_abs_delta_bpm: float = 15.0
    persistence_ms: int = 10_000
    min_consecutive_abnormal_samples: int = 5
    max_gap_ms: int = 5_000
    normal_confirm_samples: int = 2
    valid_bpm_min: int = 20
    valid_bpm_max: int = 250
    evidence_window_ms: int = 30_000
    max_evidence_samples: int = 60

    def __post_init__(self) -> None:
        _require_finite("z_threshold", self.z_threshold, strictly_positive=True)
        _require_finite("std_floor_bpm", self.std_floor_bpm, minimum=0.0)
        _require_finite(
            "min_abs_delta_bpm", self.min_abs_delta_bpm, strictly_positive=True
        )
        _require_int("persistence_ms", self.persistence_ms, minimum=0)
        _require_int(
            "min_consecutive_abnormal_samples",
            self.min_consecutive_abnormal_samples,
            minimum=1,
        )
        _require_int("max_gap_ms", self.max_gap_ms, minimum=0)
        _require_int("normal_confirm_samples", self.normal_confirm_samples, minimum=1)
        _require_int("valid_bpm_min", self.valid_bpm_min, minimum=0)
        _require_int("valid_bpm_max", self.valid_bpm_max, minimum=1)
        _require_int("evidence_window_ms", self.evidence_window_ms, minimum=0)
        _require_int("max_evidence_samples", self.max_evidence_samples, minimum=1)
        if self.valid_bpm_max <= self.valid_bpm_min:
            raise ValueError("valid_bpm_max must be greater than valid_bpm_min")


@dataclass(frozen=True)
class HrSample:
    """One heart-rate sample in whole beats per minute.

    ``ts`` is the sample's observed time. Naive datetimes are rejected by
    :meth:`AnomalyDetector.feed`; timezone-aware datetimes are normalized to UTC
    before comparison.
    """

    ts: datetime
    hr: int


@dataclass(frozen=True)
class Thresholds:
    """Computed thresholds for one baseline."""

    baseline_mean_bpm: float
    baseline_std_bpm: float
    effective_delta_bpm: float
    lower_threshold_bpm: float
    upper_threshold_bpm: float


@dataclass(frozen=True)
class AnomalyEvent:
    """Detector event conceptually compatible with the supplied Dart interface.

    ``started_at`` is the first abnormal sample timestamp of the consecutive
    abnormal run that satisfied persistence. ``last_hr`` is the heart rate of
    the sample that completed persistence. ``kind`` is ``"drop"`` or
    ``"spike"``.

    No database identifier, subject, demo run, run generation, detector result,
    severity, dedupe key or detector version is included.
    """

    started_at: datetime
    last_hr: int
    kind: AnomalyKind


@dataclass(frozen=True)
class AnomalyEvidence:
    """Diagnostic evidence retained internally for an emitted event.

    This is not part of the supplied Dart interface and is not a frozen backend
    API contract. It intentionally contains no database identifiers and no
    backend-owned lifecycle fields.
    """

    kind: AnomalyKind
    baseline_mean_bpm: float
    baseline_std_bpm: float
    effective_delta_bpm: float
    lower_threshold_bpm: float
    upper_threshold_bpm: float
    first_abnormal_at: datetime
    detected_at: datetime
    abnormal_duration_ms: int
    abnormal_sample_count: int
    extreme_heart_rate_bpm: int
    samples: Tuple[_EVIDENCE_SAMPLE, ...]


@dataclass(frozen=True)
class DetectorSnapshot:
    """Read-only diagnostic snapshot. Not a frontend or backend API contract."""

    baseline_mean_bpm: Optional[float]
    baseline_std_bpm: Optional[float]
    last_accepted_ts: Optional[datetime]
    accepted_sample_count: int
    rejected_sample_count: int
    active_episode_kind: Optional[AnomalyKind]
    episode_event_emitted: bool
    consecutive_abnormal_samples: int
    consecutive_normal_samples: int
    last_event_evidence: Optional[AnomalyEvidence]


def _validate_baseline_values(
    mean: object, std: object, config: DetectorConfig
) -> Tuple[float, float]:
    _require_finite("baseline mean", mean)
    _require_finite("baseline std", std, minimum=0.0)
    mean_f = float(mean)
    std_f = float(std)
    if mean_f < config.valid_bpm_min or mean_f > config.valid_bpm_max:
        raise ValueError(
            "baseline mean must be within the configured valid bpm range "
            f"({config.valid_bpm_min}..{config.valid_bpm_max})"
        )
    return mean_f, std_f


def compute_thresholds(
    mean: float, std: float, config: Optional[DetectorConfig] = None
) -> Thresholds:
    """Compute inclusive lower and upper anomaly thresholds.

    ``effective_delta = max(z_threshold * max(std, std_floor_bpm),
    min_abs_delta_bpm)``. The lower threshold is ``mean - effective_delta`` and
    the upper threshold is ``mean + effective_delta``.
    """

    cfg = config if config is not None else DetectorConfig()
    mean_f, std_f = _validate_baseline_values(mean, std, cfg)
    effective_delta = max(
        cfg.z_threshold * max(std_f, cfg.std_floor_bpm),
        cfg.min_abs_delta_bpm,
    )
    return Thresholds(
        baseline_mean_bpm=mean_f,
        baseline_std_bpm=std_f,
        effective_delta_bpm=effective_delta,
        lower_threshold_bpm=mean_f - effective_delta,
        upper_threshold_bpm=mean_f + effective_delta,
    )


class AnomalyDetector:
    """Stateful, deterministic heart-rate anomaly detector.

    Public detector behavior:

    * Samples are accepted only when the heart rate is an integer inside the
      configured valid range and the timestamp is a datetime comparable with the
      last accepted timestamp.
    * Samples that are invalid or not later than the last accepted sample are
      rejected. Only diagnostic rejection counters change.
    * No classification or event occurs until a valid baseline is supplied.
    * An event requires consecutive same-kind abnormal samples, the configured
      minimum sample count and the configured observed-time duration.
    * At most one event is emitted per continuous same-kind episode.
    * Normal readings never emit an event.
    * ``set_baseline`` closes any active episode without emitting and resets
      episode counters.

    The detector is single-threaded and not thread-safe. It does not implement
    the last-moments buffer or reply classification.
    """

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        self._config = config if config is not None else DetectorConfig()
        self._baseline_mean: Optional[float] = None
        self._baseline_std: Optional[float] = None
        self._last_accepted_ts: Optional[datetime] = None
        self._accepted_sample_count = 0
        self._rejected_sample_count = 0

        self._active_kind: Optional[AnomalyKind] = None
        self._episode_event_emitted = False
        self._abnormal_count = 0
        self._abnormal_start: Optional[datetime] = None
        self._abnormal_extreme: Optional[int] = None
        self._normal_count = 0
        self._evidence_samples: Deque[_EVIDENCE_SAMPLE] = deque(
            maxlen=self._config.max_evidence_samples
        )
        self._last_evidence: Optional[AnomalyEvidence] = None

    @property
    def config(self) -> DetectorConfig:
        """The immutable configuration used by this detector."""

        return self._config

    @property
    def thresholds(self) -> Optional[Thresholds]:
        """Current thresholds, or ``None`` when no baseline has been set."""

        if self._baseline_mean is None or self._baseline_std is None:
            return None
        return compute_thresholds(self._baseline_mean, self._baseline_std, self._config)

    @property
    def last_event_evidence(self) -> Optional[AnomalyEvidence]:
        """Evidence for the most recently emitted event, if any.

        Diagnostic only. It is not part of the supplied Dart interface and is
        not a frozen backend contract.
        """

        return self._last_evidence

    def set_baseline(self, mean: float, std: float) -> None:
        """Set or replace the explicit baseline.

        Invalid values raise ``ValueError`` and leave all detector state
        unchanged. A valid call closes any active episode without emitting and
        resets episode counters. It does not reset the last accepted timestamp,
        the sample counters or the retained evidence.
        """

        mean_f, std_f = _validate_baseline_values(mean, std, self._config)
        self._baseline_mean = mean_f
        self._baseline_std = std_f
        self._close_episode()

    def feed(self, sample: HrSample) -> Optional[AnomalyEvent]:
        """Feed one sample and return an event only if one is emitted.

        The method never raises for malformed sample values; it rejects them and
        returns ``None``. A rejection does not change classification or episode
        state, and does not change the last accepted timestamp.
        """

        if not isinstance(sample, HrSample):
            self._rejected_sample_count += 1
            return None

        ts = sample.ts
        hr = sample.hr
        if not isinstance(ts, datetime):
            self._rejected_sample_count += 1
            return None
        # Reject naive timestamps; require timezone-aware UTC.
        if ts.tzinfo is None or ts.utcoffset() is None:
            self._rejected_sample_count += 1
            return None
        # Normalize to UTC for consistent comparison.
        if ts.tzinfo is not UTC:
            ts = ts.astimezone(UTC)
        if (
            isinstance(hr, bool)
            or not isinstance(hr, int)
            or hr < self._config.valid_bpm_min
            or hr > self._config.valid_bpm_max
        ):
            self._rejected_sample_count += 1
            return None

        elapsed_ms: Optional[float] = None
        if self._last_accepted_ts is not None:
            elapsed_ms = self._milliseconds_between(self._last_accepted_ts, ts)
            if elapsed_ms is None or elapsed_ms <= 0.0:
                self._rejected_sample_count += 1
                return None
            if (
                self._abnormal_start is not None
                and self._milliseconds_between(self._abnormal_start, ts) is None
            ):
                self._rejected_sample_count += 1
                return None

        self._accepted_sample_count += 1
        self._last_accepted_ts = ts

        if self._baseline_mean is None or self._baseline_std is None:
            return None

        if elapsed_ms is not None and elapsed_ms > self._config.max_gap_ms:
            self._close_episode()

        thresholds = compute_thresholds(
            self._baseline_mean, self._baseline_std, self._config
        )

        if hr >= thresholds.upper_threshold_bpm:
            kind: Optional[AnomalyKind] = "spike"
        elif hr <= thresholds.lower_threshold_bpm:
            kind = "drop"
        else:
            kind = None

        if kind is None:
            self._handle_normal_sample()
            return None

        return self._handle_abnormal_sample(ts, hr, kind, thresholds)

    def reset(self) -> None:
        """Return the detector to its initial state.

        This clears the baseline, episode, counters, last accepted timestamp,
        evidence and the most recent evidence snapshot. Configuration is
        unchanged. The caller must call :meth:`set_baseline` again before any
        detection can occur.
        """

        self._baseline_mean = None
        self._baseline_std = None
        self._last_accepted_ts = None
        self._accepted_sample_count = 0
        self._rejected_sample_count = 0
        self._close_episode()
        self._last_evidence = None

    def snapshot(self) -> DetectorSnapshot:
        """Return a read-only diagnostic snapshot of detector state."""

        return DetectorSnapshot(
            baseline_mean_bpm=self._baseline_mean,
            baseline_std_bpm=self._baseline_std,
            last_accepted_ts=self._last_accepted_ts,
            accepted_sample_count=self._accepted_sample_count,
            rejected_sample_count=self._rejected_sample_count,
            active_episode_kind=self._active_kind,
            episode_event_emitted=self._episode_event_emitted,
            consecutive_abnormal_samples=self._abnormal_count,
            consecutive_normal_samples=self._normal_count,
            last_event_evidence=self._last_evidence,
        )

    def _handle_normal_sample(self) -> None:
        self._abnormal_count = 0
        self._abnormal_start = None
        self._abnormal_extreme = None
        self._evidence_samples.clear()

        if self._active_kind is None:
            self._normal_count = 0
            return

        self._normal_count += 1
        if self._normal_count >= self._config.normal_confirm_samples:
            self._close_episode()

    def _handle_abnormal_sample(
        self,
        ts: datetime,
        hr: int,
        kind: AnomalyKind,
        thresholds: Thresholds,
    ) -> Optional[AnomalyEvent]:
        if self._active_kind is not None and self._active_kind != kind:
            self._close_episode()

        if self._active_kind is None:
            self._active_kind = kind
            self._episode_event_emitted = False
            self._normal_count = 0
            self._abnormal_count = 1
            self._abnormal_start = ts
            self._abnormal_extreme = hr
            self._evidence_samples.clear()
            self._evidence_samples.append((ts, hr))
        else:
            self._normal_count = 0
            if self._abnormal_count == 0 or self._abnormal_start is None:
                self._abnormal_start = ts
                self._abnormal_extreme = hr
                self._evidence_samples.clear()
            self._abnormal_count += 1
            if self._abnormal_extreme is None:
                self._abnormal_extreme = hr
            elif kind == "spike":
                self._abnormal_extreme = max(self._abnormal_extreme, hr)
            else:
                self._abnormal_extreme = min(self._abnormal_extreme, hr)
            self._evidence_samples.append((ts, hr))
            self._prune_evidence_window(ts)

        if (
            not self._episode_event_emitted
            and self._abnormal_start is not None
            and self._abnormal_count >= self._config.min_consecutive_abnormal_samples
        ):
            duration_ms = self._milliseconds_between(self._abnormal_start, ts)
            if duration_ms is None:
                return None
            if duration_ms >= self._config.persistence_ms:
                self._episode_event_emitted = True
                self._last_evidence = AnomalyEvidence(
                    kind=kind,
                    baseline_mean_bpm=thresholds.baseline_mean_bpm,
                    baseline_std_bpm=thresholds.baseline_std_bpm,
                    effective_delta_bpm=thresholds.effective_delta_bpm,
                    lower_threshold_bpm=thresholds.lower_threshold_bpm,
                    upper_threshold_bpm=thresholds.upper_threshold_bpm,
                    first_abnormal_at=self._abnormal_start,
                    detected_at=ts,
                    abnormal_duration_ms=int(duration_ms),
                    abnormal_sample_count=self._abnormal_count,
                    extreme_heart_rate_bpm=self._abnormal_extreme
                    if self._abnormal_extreme is not None
                    else hr,
                    samples=tuple(self._evidence_samples),
                )
                return AnomalyEvent(
                    started_at=self._abnormal_start,
                    last_hr=hr,
                    kind=kind,
                )

        return None

    def _close_episode(self) -> None:
        self._active_kind = None
        self._episode_event_emitted = False
        self._abnormal_count = 0
        self._abnormal_start = None
        self._abnormal_extreme = None
        self._normal_count = 0
        self._evidence_samples.clear()

    def _prune_evidence_window(self, latest_ts: datetime) -> None:
        while self._evidence_samples:
            oldest_ts = self._evidence_samples[0][0]
            age_ms = self._milliseconds_between(oldest_ts, latest_ts)
            if age_ms is None or age_ms <= self._config.evidence_window_ms:
                return
            self._evidence_samples.popleft()

    @staticmethod
    def _milliseconds_between(earlier: datetime, later: datetime) -> Optional[float]:
        try:
            return (later - earlier).total_seconds() * 1000.0
        except (TypeError, OverflowError):
            return None
