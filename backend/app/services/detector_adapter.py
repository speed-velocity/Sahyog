"""Adapter boundary for Prasiddh's authoritative detector."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class DetectorReading(BaseModel):
    observed_at: datetime
    heart_rate_bpm: int
    activity_context: str | None = None


class DetectorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anomaly_kind: str | None = None
    detected_at: datetime
    window_start: datetime | None = None
    window_end: datetime | None = None
    severity: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    explanation: str | None = Field(default=None, max_length=1000)
    detector_version: str | None = Field(default=None, max_length=64)
    evidence: list[dict[str, str | int | float]] = Field(
        default_factory=list, max_length=32
    )


class Detector(Protocol):
    def detect(self, readings: list[DetectorReading]) -> DetectorResult:
        """Return one authoritative detector result for the supplied window."""


def canonical_dedupe_key(
    *,
    subject_user_id: str,
    demo_run_id: str,
    run_generation: int,
    result: DetectorResult,
) -> str:
    payload = {
        "demo_run_id": demo_run_id,
        "detector_version": result.detector_version,
        "kind": result.anomaly_kind,
        "run_generation": run_generation,
        "subject_user_id": subject_user_id,
        "window_end": _timestamp(result.window_end),
        "window_start": _timestamp(result.window_start),
    }
    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def detector_result_value(anomaly_kind: str | None) -> str | None:
    return {"spike": "HR_SPIKE", "drop": "HR_DROP"}.get(anomaly_kind)
