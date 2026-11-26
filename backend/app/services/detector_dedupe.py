"""Deterministic logical deduplication identity for detector anomalies.

The team approved canonical JSON with sorted keys, compact separators, UTF-8
encoding, UTC-normalized timestamps with fixed microsecond precision, and a
SHA-256 digest.

The exact canonical key names and the final ``dedupe_key`` string representation
(for example, whether the backend prefixes the digest) remain unapproved. This
module therefore implements the proposed key names from the confirmed logical
inputs and returns the raw lowercase SHA-256 hex digest. It does not add a prefix
or any database context to the core detector.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

__all__ = [
    "DeduplicationContext",
    "canonical_dedupe_payload",
    "dedupe_sha256",
]


def _validate_text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _validate_aware_timestamp(name: str, value: object) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _utc_microseconds(value: datetime) -> str:
    normalized = value.astimezone(UTC).replace(tzinfo=None)
    return normalized.isoformat(timespec="microseconds") + "Z"


@dataclass(frozen=True)
class DeduplicationContext:
    """Backend-supplied logical identity inputs for one detector anomaly.

    ``subject_id``, ``demo_run_id`` and ``generation`` are backend-owned context.
    ``detector_version`` and the observation window come from the detector
    result. IDs are treated as opaque canonical strings; callers must supply one
    stable representation.
    """

    subject_id: str
    demo_run_id: str
    generation: int
    detector_version: str
    window_start: datetime
    window_end: datetime

    def __post_init__(self) -> None:
        _validate_text("subject_id", self.subject_id)
        _validate_text("demo_run_id", self.demo_run_id)
        _validate_text("detector_version", self.detector_version)
        if isinstance(self.generation, bool) or not isinstance(self.generation, int):
            raise TypeError("generation must be an integer")
        if self.generation <= 0:
            raise ValueError("generation must be greater than zero")
        start = _validate_aware_timestamp("window_start", self.window_start)
        end = _validate_aware_timestamp("window_end", self.window_end)
        if end < start:
            raise ValueError("window_end must not be earlier than window_start")


def canonical_dedupe_payload(context: DeduplicationContext) -> str:
    """Return the proposed canonical JSON payload as a string.

    The payload uses the confirmed serialization method and the proposed key
    names ``subject_id``, ``demo_run_id``, ``generation``, ``detector_version``,
    ``window_start`` and ``window_end``. Key naming is not yet approved.
    """

    payload = {
        "subject_id": context.subject_id,
        "demo_run_id": context.demo_run_id,
        "generation": context.generation,
        "detector_version": context.detector_version,
        "window_start": _utc_microseconds(context.window_start),
        "window_end": _utc_microseconds(context.window_end),
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def dedupe_sha256(context: DeduplicationContext) -> str:
    """Return the raw lowercase SHA-256 hex digest of the canonical payload."""

    canonical = canonical_dedupe_payload(context)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
