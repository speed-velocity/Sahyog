"""Authoritative detector provider and bounded session lifecycle."""

from __future__ import annotations

from collections import OrderedDict
from threading import RLock
from uuid import UUID

from backend.app.core.config import get_settings
from backend.app.services.detector_adapter import Detector
from backend.app.services.detector_backend_contract import BackendDetector


class DetectorSessionProvider:
    """Own one detector session per subject/run/generation.

    Detector sessions are stateful and not thread-safe, so the lock also
    serializes calls for a cache entry. The cache is bounded to prevent a
    long-running demo server from retaining arbitrary historical runs.
    """

    def __init__(self, max_sessions: int, baseline_mean: float, baseline_std: float):
        if max_sessions < 1:
            raise ValueError("detector session cache size must be positive")
        self._max_sessions = max_sessions
        self._baseline_mean = baseline_mean
        self._baseline_std = baseline_std
        self._sessions: OrderedDict[tuple[UUID, UUID, int], BackendDetector] = (
            OrderedDict()
        )
        self._lock = RLock()

    def get(
        self, *, subject_user_id: UUID, demo_run_id: UUID, run_generation: int
    ) -> Detector:
        key = (subject_user_id, demo_run_id, run_generation)
        with self._lock:
            detector = self._sessions.pop(key, None)
            if detector is None:
                detector = BackendDetector(self._baseline_mean, self._baseline_std)
            self._sessions[key] = detector
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)
            return _LockedDetector(detector, self._lock)


class _LockedDetector:
    def __init__(self, detector: BackendDetector, cache_lock: RLock):
        self._detector = detector
        self._cache_lock = cache_lock

    def detect(self, readings):
        with self._cache_lock:
            return self._detector.detect(readings)


_provider: DetectorSessionProvider | None = None
_provider_lock = RLock()


def get_detector_provider() -> DetectorSessionProvider:
    global _provider
    settings = get_settings()
    with _provider_lock:
        if _provider is None:
            _provider = DetectorSessionProvider(
                settings.detector_session_cache_size,
                settings.detector_baseline_mean_bpm,
                settings.detector_baseline_std_bpm,
            )
        return _provider


def reset_detector_provider_for_tests() -> None:
    global _provider
    with _provider_lock:
        _provider = None
