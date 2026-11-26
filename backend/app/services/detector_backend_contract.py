"""Backend-facing single-result contract for the Role 1 detector.

The backend reading route on ``origin/backend`` commit ``7de901b`` calls a
``Detector`` once per reading and expects one ``DetectorResult``. It uses the
result's internal ``anomaly_kind`` (``"spike"`` or ``"drop"``) when it maps and
persists an anomaly event. The batch-oriented interface in
``anomaly_integration.py`` remains the Role 1 source of detector state.

This module deliberately keeps the backend route and persistence code out of
Role 1. Shubhankar owns the route, session cache, baseline source and database
transaction. A single facade instance must be retained for one active
subject/demo-run/generation context; it is stateful and not thread-safe.

The facade accepts backend-shaped readings, including ``activity_context``,
which the detector ignores. It returns a result with the exact backend fields.
If the installed backend adapter is available, its Pydantic types are used
directly; otherwise equivalent local fallback types are provided so Role 1 can
test this branch in isolation.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.services.anomaly_integration import (
    DETECTOR_VERSION,
    AnomalyDetectorSession,
    DetectorConfig,
    DetectorReading as IntegrationDetectorReading,
    DetectorSnapshot,
    DetectedAnomaly,
    Thresholds,
)

try:
    from backend.app.services.detector_adapter import (
        DetectorReading as BackendDetectorReading,
        DetectorResult as BackendDetectorResult,
    )
except ModuleNotFoundError:

    class BackendDetectorReading(BaseModel):
        observed_at: datetime
        heart_rate_bpm: int
        activity_context: str | None = None

    class BackendDetectorResult(BaseModel):
        model_config = ConfigDict(extra="forbid")

        anomaly_kind: str | None = None
        detected_at: datetime
        window_start: datetime | None = None
        window_end: datetime | None = None
        severity: str | None = Field(
            default=None,
            pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$",
        )
        explanation: str | None = Field(default=None, max_length=1000)
        detector_version: str | None = Field(default=None, max_length=64)
        evidence: list[dict[str, str | int | float]] = Field(
            default_factory=list,
            max_length=32,
        )


__all__ = [
    "BACKEND_EVIDENCE_LIMIT",
    "BackendDetector",
    "BackendDetectorContractError",
    "BackendDetectorReading",
    "BackendDetectorResult",
    "DETECTOR_VERSION",
]

BACKEND_EVIDENCE_LIMIT = 32


class BackendDetectorContractError(RuntimeError):
    """The backend's one-result-per-call contract cannot be satisfied."""


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validate_reading(reading: BackendDetectorReading) -> None:
    if not isinstance(reading.observed_at, datetime):
        raise TypeError("observed_at must be a datetime")
    if reading.observed_at.tzinfo is None or reading.observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    if isinstance(reading.heart_rate_bpm, bool) or not isinstance(
        reading.heart_rate_bpm, int
    ):
        raise TypeError("heart_rate_bpm must be an integer")
    if reading.activity_context is not None and not isinstance(
        reading.activity_context, str
    ):
        raise TypeError("activity_context must be a string or None")


def _coerce_reading(value: object) -> BackendDetectorReading:
    if isinstance(value, BackendDetectorReading):
        reading = value
    elif isinstance(value, Mapping):
        reading = BackendDetectorReading(**value)
    else:
        try:
            observed_at = value.observed_at
            heart_rate_bpm = value.heart_rate_bpm
        except AttributeError as exc:
            raise TypeError(
                "readings must contain DetectorReading-like objects"
            ) from exc
        reading = BackendDetectorReading(
            observed_at=observed_at,
            heart_rate_bpm=heart_rate_bpm,
            activity_context=getattr(value, "activity_context", None),
        )
    _validate_reading(reading)
    return reading


def _coerce_readings(readings: Sequence[Any]) -> list[BackendDetectorReading]:
    if isinstance(readings, (str, bytes, bytearray)) or not isinstance(
        readings, Sequence
    ):
        raise TypeError("readings must be a sequence of DetectorReading values")
    if not readings:
        raise ValueError(
            "at least one reading is required because the backend result "
            "requires detected_at"
        )
    return [_coerce_reading(reading) for reading in readings]


def _evidence(samples: Sequence[tuple[datetime, int]]) -> list[dict[str, str | int]]:
    return [
        {
            "observed_at": _timestamp(observed_at),
            "heart_rate_bpm": heart_rate_bpm,
        }
        for observed_at, heart_rate_bpm in samples[-BACKEND_EVIDENCE_LIMIT:]
    ]


def _explanation(anomaly: DetectedAnomaly) -> str:
    evidence = anomaly.evidence
    if evidence.kind == "spike":
        relation = "above the configured upper threshold"
        threshold = evidence.upper_threshold_bpm
    else:
        relation = "below the configured lower threshold"
        threshold = evidence.lower_threshold_bpm
    explanation = (
        f"Rule-based demo detector: sustained heart-rate {evidence.kind} with "
        f"extreme {evidence.extreme_heart_rate_bpm} bpm {relation} "
        f"({threshold:.1f} bpm); {evidence.abnormal_sample_count} consecutive "
        f"abnormal samples over {evidence.abnormal_duration_ms} ms."
    )
    if len(evidence.samples) > BACKEND_EVIDENCE_LIMIT:
        explanation += (
            f" Evidence is limited to the {BACKEND_EVIDENCE_LIMIT} most recent samples."
        )
    return explanation


class BackendDetector:
    """Stateful adapter for the backend's single-result detector protocol.

    One instance belongs to one active subject/demo-run/generation context. The
    backend must cache it rather than creating it per HTTP request. The detector
    is single-threaded and not thread-safe.

    ``detect`` accepts one or more readings but can return only one backend
    anomaly result. If a call would produce more than one event, it raises
    :class:`BackendDetectorContractError` and leaves detector state unchanged.
    The backend route currently supplies exactly one reading per call.
    """

    def __init__(
        self,
        baseline_mean: float,
        baseline_std: float,
        config: Optional[DetectorConfig] = None,
        *,
        detector_version: str = DETECTOR_VERSION,
    ) -> None:
        self._session = AnomalyDetectorSession(
            baseline_mean,
            baseline_std,
            config,
            detector_version=detector_version,
        )
        self._detector_version = detector_version

    @property
    def detector_version(self) -> str:
        return self._detector_version

    @property
    def thresholds(self) -> Optional[Thresholds]:
        return self._session.thresholds

    def snapshot(self) -> DetectorSnapshot:
        """Return diagnostic state. This is not a backend API payload."""

        return self._session.snapshot()

    def detect(
        self, readings: Sequence[BackendDetectorReading]
    ) -> BackendDetectorResult:
        """Return the backend's single detector result for this call.

        The whole call is evaluated on a copy of detector state. A contract
        error therefore cannot consume readings or advance episode state.
        Core-detector rejections (invalid BPM or non-increasing timestamps) are
        counted by the session and produce a no-anomaly result; backend
        ingestion remains responsible for its own validation and idempotency.
        """

        normalized = _coerce_readings(readings)
        integration_readings = [
            IntegrationDetectorReading(
                observed_at=reading.observed_at,
                heart_rate_bpm=reading.heart_rate_bpm,
            )
            for reading in normalized
        ]

        trial = copy.deepcopy(self._session)
        batch_result = trial.detect(integration_readings)
        if len(batch_result.anomalies) > 1:
            raise BackendDetectorContractError(
                "backend detector contract supports at most one anomaly per "
                f"call; received {len(batch_result.anomalies)}"
            )
        self._session = trial

        if batch_result.anomalies:
            return self._anomaly_result(batch_result.anomalies[0])

        last_accepted = trial.snapshot().last_accepted_ts
        detected_at = last_accepted or normalized[-1].observed_at
        return BackendDetectorResult(
            detected_at=_utc(detected_at),
            detector_version=self._detector_version,
        )

    def _anomaly_result(self, anomaly: DetectedAnomaly) -> BackendDetectorResult:
        evidence = anomaly.evidence
        return BackendDetectorResult(
            anomaly_kind=anomaly.event.kind,
            detected_at=_utc(evidence.detected_at),
            window_start=_utc(evidence.first_abnormal_at),
            window_end=_utc(evidence.detected_at),
            severity=anomaly.severity,
            explanation=_explanation(anomaly),
            detector_version=anomaly.detector_version,
            evidence=_evidence(evidence.samples),
        )
