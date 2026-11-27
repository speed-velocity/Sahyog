from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from backend.app.api.readings import (
    get_detector,
)
from backend.app.api.readings import (
    router as readings_router,
)
from backend.app.core.auth import require_active_principal
from backend.app.db.session import get_db
from backend.app.models.demo import DemoRun
from backend.app.models.incidents import Incident
from backend.app.models.readings import AnomalyEvent, HealthReading
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeReadingSession:
    def __init__(self, subject_id: UUID, run_id: UUID, run: DemoRun) -> None:
        self.subject_id = subject_id
        self.run_id = run_id
        self.demo_runs = {run_id: run}
        self.readings: list[HealthReading] = []
        self.anomaly_events: dict[UUID, AnomalyEvent] = {}
        self.incidents: list[Incident] = []

    def scalar(self, stmt):
        entity = stmt.column_descriptions[0]["entity"]
        params = stmt.compile().params
        if entity is DemoRun:
            run_id = next(
                (v for k, v in params.items() if "demo_run_id" in k),
                self.run_id,
            )
            return self.demo_runs.get(run_id)
        if entity is HealthReading:
            if getattr(stmt, "_order_by_clauses", None):
                matching = [
                    r
                    for r in self.readings
                    if r.subject_user_id == self.subject_id
                    and r.demo_run_id == self.run_id
                ]
                return max(matching, key=lambda r: r.observed_at) if matching else None
            key = next(
                (v for k, v in params.items() if "ingestion_idempotency_key" in k),
                None,
            )
            for r in self.readings:
                if (
                    r.subject_user_id == self.subject_id
                    and r.ingestion_idempotency_key == key
                ):
                    return r
            return None
        if entity is AnomalyEvent:
            for e in self.anomaly_events.values():
                return e
            return None
        if entity is Incident:
            return None
        return None

    def get(self, model, ident, **_kwargs):
        if model is AnomalyEvent:
            return self.anomaly_events.get(ident)
        if model is DemoRun:
            return self.demo_runs.get(ident)
        return None

    def add(self, obj) -> None:
        if isinstance(obj, HealthReading):
            self.readings.append(obj)
        elif isinstance(obj, AnomalyEvent):
            self.anomaly_events[obj.anomaly_event_id] = obj
        elif isinstance(obj, Incident):
            self.incidents.append(obj)

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


@pytest.fixture
def reading_context():
    subject_id = uuid4()
    run_id = uuid4()
    run = DemoRun(
        demo_run_id=run_id,
        subject_user_id=subject_id,
        current_generation=1,
    )
    session = FakeReadingSession(subject_id, run_id, run)
    detector = MagicMock()
    detector.detect.return_value = None

    app = FastAPI()
    app.include_router(readings_router)
    app.dependency_overrides[require_active_principal] = lambda: AuthenticatedPrincipal(
        user_id=subject_id, role=UserRole.SUBJECT
    )
    app.dependency_overrides[get_detector] = lambda: detector
    app.dependency_overrides[get_db] = lambda: session

    with TestClient(app) as client:
        yield client, session, detector, subject_id, run_id


def test_bpm_range_validation(reading_context) -> None:
    client, _session, detector, _subject_id, run_id = reading_context

    # Below minimum (19 BPM) -> 422
    resp_low = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 19,
            "observed_at": "2026-01-01T12:00:00Z",
            "ingestion_idempotency_key": "bpm-low",
        },
    )
    assert resp_low.status_code == 422
    assert "heart_rate_bpm must be between 20 and 250" in resp_low.json()["detail"]
    assert detector.detect.call_count == 0

    # Above maximum (251 BPM) -> 422
    resp_high = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 251,
            "observed_at": "2026-01-01T12:00:00Z",
            "ingestion_idempotency_key": "bpm-high",
        },
    )
    assert resp_high.status_code == 422
    assert "heart_rate_bpm must be between 20 and 250" in resp_high.json()["detail"]
    assert detector.detect.call_count == 0

    # Lower boundary (20 BPM) -> 202 accepted
    resp_min = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 20,
            "observed_at": "2026-01-01T12:00:01Z",
            "ingestion_idempotency_key": "bpm-min",
        },
    )
    assert resp_min.status_code == 202
    assert resp_min.json()["accepted"] is True
    assert detector.detect.call_count == 1

    # Upper boundary (250 BPM) -> 202 accepted
    resp_max = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 250,
            "observed_at": "2026-01-01T12:00:02Z",
            "ingestion_idempotency_key": "bpm-max",
        },
    )
    assert resp_max.status_code == 202
    assert resp_max.json()["accepted"] is True
    assert detector.detect.call_count == 2


def test_idempotent_duplicate_replay_does_not_rerun_detector(
    reading_context,
) -> None:
    client, _session, detector, _subject_id, run_id = reading_context

    payload = {
        "demo_run_id": str(run_id),
        "source_kind": "SIMULATED",
        "heart_rate_bpm": 72,
        "observed_at": "2026-01-01T12:00:00Z",
        "activity_context": "RESTING",
        "source_record_id": "rec-001",
        "ingestion_idempotency_key": "replay-key-1",
    }

    first_resp = client.post("/readings", json=payload)
    assert first_resp.status_code == 202
    first_data = first_resp.json()
    assert first_data["accepted"] is True
    assert detector.detect.call_count == 1

    # Second exact submission with same idempotency key
    second_resp = client.post("/readings", json=payload)
    assert second_resp.status_code == 202
    second_data = second_resp.json()
    assert second_data["accepted"] is True
    assert second_data["reading_id"] == first_data["reading_id"]
    # Detector must NOT be called again
    assert detector.detect.call_count == 1


def test_idempotent_replay_of_earlier_reading_when_newer_reading_exists(
    reading_context,
) -> None:
    client, _session, detector, _subject_id, run_id = reading_context

    payload_a = {
        "demo_run_id": str(run_id),
        "source_kind": "SIMULATED",
        "heart_rate_bpm": 70,
        "observed_at": "2026-01-01T12:00:00Z",
        "activity_context": "RESTING",
        "source_record_id": "rec-A",
        "ingestion_idempotency_key": "key-A",
    }
    payload_b = {
        "demo_run_id": str(run_id),
        "source_kind": "SIMULATED",
        "heart_rate_bpm": 75,
        "observed_at": "2026-01-01T12:00:10Z",
        "activity_context": "WALKING",
        "source_record_id": "rec-B",
        "ingestion_idempotency_key": "key-B",
    }

    # 1. Successfully submit reading A
    resp_a = client.post("/readings", json=payload_a)
    assert resp_a.status_code == 202
    data_a = resp_a.json()
    assert data_a["accepted"] is True
    assert detector.detect.call_count == 1

    # 2. Successfully submit a newer reading B in the same demo run
    resp_b = client.post("/readings", json=payload_b)
    assert resp_b.status_code == 202
    data_b = resp_b.json()
    assert data_b["accepted"] is True
    assert detector.detect.call_count == 2

    # 3. Replay reading A with its original idempotency key and identical payload.
    # Reading A's timestamp is 12:00:00Z, which is older than the latest reading B (12:00:10Z).
    # It must succeed as an idempotent replay without failing the monotonic check.
    resp_a_replay = client.post("/readings", json=payload_a)
    assert resp_a_replay.status_code == 202
    data_a_replay = resp_a_replay.json()
    assert data_a_replay["accepted"] is True
    assert data_a_replay["reading_id"] == data_a["reading_id"]

    # 4. Confirms the replay does not invoke the detector again
    assert detector.detect.call_count == 2


def test_idempotency_key_reuse_with_altered_payload_returns_409(
    reading_context,
) -> None:
    client, session, _detector, subject_id, run_id = reading_context

    base_payload = {
        "demo_run_id": str(run_id),
        "source_kind": "SIMULATED",
        "heart_rate_bpm": 80,
        "observed_at": "2026-01-01T12:00:00Z",
        "activity_context": "WALKING",
        "source_record_id": "rec-100",
        "ingestion_idempotency_key": "conflict-key",
    }

    init_resp = client.post("/readings", json=base_payload)
    assert init_resp.status_code == 202

    # Different BPM
    conflict_bpm = {**base_payload, "heart_rate_bpm": 85}
    resp = client.post("/readings", json=conflict_bpm)
    assert resp.status_code == 409
    assert (
        "ingestion_idempotency_key was already used with a different reading"
        in resp.json()["detail"]
    )

    # Different observed_at
    conflict_time = {**base_payload, "observed_at": "2026-01-01T12:00:05Z"}
    resp = client.post("/readings", json=conflict_time)
    assert resp.status_code == 409

    # Different activity_context
    conflict_activity = {**base_payload, "activity_context": "RUNNING"}
    resp = client.post("/readings", json=conflict_activity)
    assert resp.status_code == 409

    # Different source_record_id
    conflict_record = {**base_payload, "source_record_id": "rec-999"}
    resp = client.post("/readings", json=conflict_record)
    assert resp.status_code == 409

    # Different demo_run_id: create a second valid demo run for this subject
    run_id_2 = uuid4()
    session.demo_runs[run_id_2] = DemoRun(
        demo_run_id=run_id_2,
        subject_user_id=subject_id,
        current_generation=1,
    )
    conflict_run = {**base_payload, "demo_run_id": str(run_id_2)}
    resp = client.post("/readings", json=conflict_run)
    assert resp.status_code == 409
    assert (
        "ingestion_idempotency_key was already used with a different reading"
        in resp.json()["detail"]
    )

    # Different source_kind:
    # Seed an existing reading that was stored with a different source_kind
    key_source = "conflict-source-key"
    session.readings.append(
        HealthReading(
            reading_id=uuid4(),
            subject_user_id=subject_id,
            demo_run_id=run_id,
            run_generation=1,
            source_kind="DEVICE",
            heart_rate_bpm=80,
            observed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            received_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            activity_context="WALKING",
            source_record_id="rec-100",
            ingestion_idempotency_key=key_source,
        )
    )
    conflict_source = {
        **base_payload,
        "source_kind": "SIMULATED",
        "ingestion_idempotency_key": key_source,
    }
    resp = client.post("/readings", json=conflict_source)
    assert resp.status_code == 409
    assert (
        "ingestion_idempotency_key was already used with a different reading"
        in resp.json()["detail"]
    )


def test_strictly_monotonic_observation_timestamps(reading_context) -> None:
    client, _session, detector, _subject_id, run_id = reading_context

    t1 = "2026-01-01T12:00:10Z"
    r1 = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 70,
            "observed_at": t1,
            "ingestion_idempotency_key": "time-1",
        },
    )
    assert r1.status_code == 202
    assert detector.detect.call_count == 1

    # Equal timestamp (non-idempotent key) -> 422
    r_equal = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 71,
            "observed_at": t1,
            "ingestion_idempotency_key": "time-equal",
        },
    )
    assert r_equal.status_code == 422
    assert (
        "observed_at must be later than the latest reading" in r_equal.json()["detail"]
    )
    assert detector.detect.call_count == 1

    # Earlier timestamp -> 422
    r_earlier = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 71,
            "observed_at": "2026-01-01T12:00:09Z",
            "ingestion_idempotency_key": "time-earlier",
        },
    )
    assert r_earlier.status_code == 422
    assert (
        "observed_at must be later than the latest reading"
        in r_earlier.json()["detail"]
    )
    assert detector.detect.call_count == 1

    # Later timestamp -> 202 accepted
    r_later = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 72,
            "observed_at": "2026-01-01T12:00:11Z",
            "ingestion_idempotency_key": "time-later",
        },
    )
    assert r_later.status_code == 202
    assert detector.detect.call_count == 2


def test_observed_at_must_have_timezone(reading_context) -> None:
    client, _session, _detector, _subject_id, run_id = reading_context

    resp = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "SIMULATED",
            "heart_rate_bpm": 75,
            "observed_at": "2026-01-01T12:00:00",  # No timezone offset or Z
            "ingestion_idempotency_key": "tz-missing",
        },
    )
    assert resp.status_code == 422
    assert "observed_at must include a timezone" in resp.json()["detail"]


def test_only_simulated_readings_supported(reading_context) -> None:
    client, _session, _detector, _subject_id, run_id = reading_context

    resp = client.post(
        "/readings",
        json={
            "demo_run_id": str(run_id),
            "source_kind": "DEVICE",
            "heart_rate_bpm": 75,
            "observed_at": "2026-01-01T12:00:00Z",
            "ingestion_idempotency_key": "unsupported-source",
        },
    )
    assert resp.status_code == 422
    assert "Only SIMULATED readings are supported" in resp.json()["detail"]
