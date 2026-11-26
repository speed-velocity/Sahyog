"""Integration-facing types for the SAHYOG heart-rate anomaly detector.

This module is Role 1-owned. It wraps :class:`AnomalyDetector` with a typed,
stateful batch interface that the backend adapter can consume. It deliberately
does not know about databases, subject/run identifiers, incident lifecycle or
persistence.

Approved detector-result values are ``HR_SPIKE`` and ``HR_DROP``. Severity is
optional and currently never assigned; confidence is not supported.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Tuple

from backend.app.services.anomaly import (
    AnomalyDetector,
    AnomalyEvent,
    AnomalyEvidence,
    AnomalyKind,
    DetectorConfig,
    DetectorSnapshot,
    HrSample,
    Thresholds,
)

__all__ = [
    "DETECTOR_RESULT_BY_KIND",
    "DETECTOR_VERSION",
    "AnomalyDetectorSession",
    "DetectedAnomaly",
    "DetectorReading",
    "DetectorResult",
    "DetectorResultValue",
    "Severity",
    "map_detector_result",
]

# Proposed implementation label. Shubhankar/Utkarsh have not approved this exact
# string; it is carried so the backend can persist a detector version and build
# deduplication identities. It is not a clinical or model version.
DETECTOR_VERSION = "sahyog-hr-threshold-v1"

DetectorResultValue = Literal["HR_SPIKE", "HR_DROP"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

DETECTOR_RESULT_BY_KIND: dict[AnomalyKind, DetectorResultValue] = {
    "spike": "HR_SPIKE",
    "drop": "HR_DROP",
}


def map_detector_result(kind: AnomalyKind) -> DetectorResultValue:
    """Map the core detector's internal kind to the approved result value."""

    try:
        return DETECTOR_RESULT_BY_KIND[kind]
    except KeyError as exc:
        raise ValueError(f"unsupported anomaly kind: {kind!r}") from exc


@dataclass(frozen=True)
class DetectorReading:
    """One backend-supplied reading for detection.

    ``observed_at`` must be timezone-aware. The datetime is not converted to UTC
    here; the core detector compares instants, and the deduplication helper
    normalizes timestamps explicitly. ``heart_rate_bpm`` must be an integer.

    The backend owns reading IDs, subject/run/generation identifiers and receipt
    timestamps; they are intentionally absent from this type.
    """

    observed_at: datetime
    heart_rate_bpm: int

    def __post_init__(self) -> None:
        if not isinstance(self.observed_at, datetime):
            raise TypeError("observed_at must be a datetime")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        if isinstance(self.heart_rate_bpm, bool) or not isinstance(
            self.heart_rate_bpm, int
        ):
            raise TypeError("heart_rate_bpm must be an integer")

    def to_hr_sample(self) -> HrSample:
        """Convert to the core detector's backward-compatible sample type."""

        return HrSample(ts=self.observed_at, hr=self.heart_rate_bpm)

    @classmethod
    def from_hr_sample(cls, sample: HrSample) -> "DetectorReading":
        """Convert a core sample to the integration type.

        Raises ``TypeError`` if ``sample`` is not an ``HrSample`` and
        ``ValueError`` if its timestamp is naive.
        """

        if not isinstance(sample, HrSample):
            raise TypeError("sample must be an HrSample")
        return cls(observed_at=sample.ts, heart_rate_bpm=sample.hr)


@dataclass(frozen=True)
class DetectedAnomaly:
    """One emitted anomaly with its event and immediately captured evidence.

    ``detector_result`` is the approved backend-facing value. ``severity`` is
    optional and is always ``None`` until an assignment policy is approved.
    ``confidence`` is intentionally absent because no calibrated value exists.
    """

    event: AnomalyEvent
    evidence: AnomalyEvidence
    detector_result: DetectorResultValue
    severity: Optional[Severity] = None
    detector_version: str = DETECTOR_VERSION

    def __post_init__(self) -> None:
        if self.event.kind != self.evidence.kind:
            raise ValueError("event and evidence kinds must match")
        expected = map_detector_result(self.event.kind)
        if self.detector_result != expected:
            raise ValueError("detector_result does not match the event kind")
        if not isinstance(self.detector_version, str) or not self.detector_version:
            raise ValueError("detector_version must be a non-empty string")
        if self.severity is not None and self.severity not in (
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        ):
            raise ValueError(f"unsupported severity: {self.severity!r}")

    @property
    def observation_window_start(self) -> datetime:
        """Proposed start of the logical anomaly observation window."""

        return self.evidence.first_abnormal_at

    @property
    def observation_window_end(self) -> datetime:
        """Proposed end of the logical anomaly observation window."""

        return self.evidence.detected_at


@dataclass(frozen=True)
class DetectorResult:
    """Result of one ``detect`` call.

    An empty ``anomalies`` tuple means no anomaly was detected. A tuple with one
    item means one event; multiple items represent multiple independent episodes
    in the supplied sequence. ``accepted_readings`` and ``rejected_readings``
    count only readings supplied in this call, not cumulative detector state.
    """

    anomalies: Tuple[DetectedAnomaly, ...] = ()
    accepted_readings: int = 0
    rejected_readings: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "anomalies", tuple(self.anomalies))
        for name, value in (
            ("accepted_readings", self.accepted_readings),
            ("rejected_readings", self.rejected_readings),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    @property
    def has_anomaly(self) -> bool:
        return bool(self.anomalies)

    @property
    def anomaly_events(self) -> Tuple[AnomalyEvent, ...]:
        return tuple(anomaly.event for anomaly in self.anomalies)


class AnomalyDetectorSession:
    """Stateful integration wrapper around :class:`AnomalyDetector`.

    One instance must be scoped by the backend to one active
    subject/demo-run/generation context. The session retains episode state across
    successive ``detect`` calls. Create a new session for a new run or
    generation; do not reuse an instance across contexts.

    The constructor requires an explicit baseline. Invalid baseline values raise
    ``ValueError`` and no session is created. The session is single-threaded and
    not thread-safe.
    """

    def __init__(
        self,
        baseline_mean: float,
        baseline_std: float,
        config: Optional[DetectorConfig] = None,
        *,
        detector_version: str = DETECTOR_VERSION,
    ) -> None:
        if not isinstance(detector_version, str) or not detector_version:
            raise ValueError("detector_version must be a non-empty string")
        detector = AnomalyDetector(config)
        detector.set_baseline(baseline_mean, baseline_std)
        self._detector = detector
        self._detector_version = detector_version

    @property
    def detector_version(self) -> str:
        return self._detector_version

    @property
    def thresholds(self) -> Optional[Thresholds]:
        """Current computed thresholds, or ``None`` only if state is corrupted."""

        return self._detector.thresholds

    def snapshot(self) -> DetectorSnapshot:
        """Diagnostic state snapshot. Not a backend API payload."""

        return self._detector.snapshot()

    def detect(self, readings: Sequence[DetectorReading]) -> DetectorResult:
        """Feed an ordered batch and return all anomalies it emits.

        The call preserves detector state across invocations. Empty input is a
        no-op and returns an empty result. Every item must be a
        ``DetectorReading``; a wrong item type raises ``TypeError`` before any
        state changes. Invalid bpm values and out-of-order/duplicate timestamps
        are rejected by the core detector and reported in ``rejected_readings``.

        Evidence is captured immediately after each event, before the next
        reading is fed, so multiple events in one batch retain distinct evidence.
        """

        if isinstance(readings, (str, bytes, bytearray)) or not isinstance(
            readings, Sequence
        ):
            raise TypeError("readings must be a sequence of DetectorReading")
        for index, reading in enumerate(readings):
            if not isinstance(reading, DetectorReading):
                raise TypeError(f"readings[{index}] must be a DetectorReading")

        before = self._detector.snapshot()
        anomalies: list[DetectedAnomaly] = []

        for reading in readings:
            event = self._detector.feed(reading.to_hr_sample())
            if event is None:
                continue
            evidence = self._detector.last_event_evidence
            if evidence is None:
                raise RuntimeError("detector emitted an event without evidence")
            anomalies.append(
                DetectedAnomaly(
                    event=event,
                    evidence=evidence,
                    detector_result=map_detector_result(event.kind),
                    severity=None,
                    detector_version=self._detector_version,
                )
            )

        after = self._detector.snapshot()
        return DetectorResult(
            anomalies=tuple(anomalies),
            accepted_readings=(
                after.accepted_sample_count - before.accepted_sample_count
            ),
            rejected_readings=(
                after.rejected_sample_count - before.rejected_sample_count
            ),
        )
