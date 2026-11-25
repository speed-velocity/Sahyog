# SAHYOG Detector Integration Contract

**Project:** SAHYOG - Detect. Verify. Respond.
**Document:** `docs/detector_integration_contract.md`
**Owner:** Prasiddh (Role 1 - AI/ML and health monitoring)
**Last updated:** 2026-11-25
**Status:** `IMPLEMENTED` and `TESTED` at unit level; `NOT INTEGRATED`.
**Branch:** `Ai/ml-and-monitoring`
**Backend target inspected:** `origin/backend` at `7de901b`
**Companions:** `docs/thresholds.md`, `docs/integration_gaps.md`,
`handoff/prasiddh.md`

> This is an integration contract for Role 1 code, not a frozen backend API
> schema. A field is only approved when it is marked **TEAM-CONFIRMED**. Code
> marked **IMPLEMENTED** may still be awaiting backend integration. Items marked
> **PROPOSED** or **UNRESOLVED** must not be treated as agreed backend contracts.

---

## 1. Purpose and scope

This document defines the boundary between the SAHYOG backend and the Role 1
detector, buffer, deduplication helper, and verification-reply classifier.

It covers:

- input readings and state ownership;
- baseline and configuration handling;
- deterministic heart-rate anomaly semantics;
- detector output types and approved vocabulary;
- logical deduplication;
- bounded recent-reading evidence;
- verification reply classification;
- backend, dashboard, and database integration boundaries.

It does not define the backend reading route, incident state machine,
verification endpoint, escalation, SQLAlchemy models, migrations, dashboard API,
or Flutter UI. Those remain with their owners.

No backend adapter, backend route, ORM model, migration, dashboard file, or
Flutter file was created or modified by Role 1.

## 2. Authority and status language

Priority used for this document:

1. Latest team decisions supplied in the Phase 2/3 task prompt.
2. `PRD.md` and `SYSTEM_DESIGN.md`.
3. `TEAM.md` ownership.
4. Shared and individual handoffs.
5. Inspected remote schemas and code.
6. Existing Role 1 code.

Status labels:

| Label | Meaning |
|---|---|
| **TEAM-CONFIRMED** | Approved boundary or vocabulary from the latest team decision; implementation may still be pending. |
| **IMPLEMENTED** | Present in Role 1 code and covered by unit tests on this branch. |
| **PROPOSED** | A concrete Role 1 proposal awaiting owner approval. |
| **UNRESOLVED** | A required decision is missing; do not silently choose a contract. |
| **BLOCKED** | Implementation or verification depends on a missing component owned by another role. |

The backend adapter remains owned by Shubhankar. The detector code must not be
wired into a route by Role 1.

## 3. Integration boundary

### 3.1 Confirmed ownership

**TEAM-CONFIRMED:**

- Backend adapter location: `backend.app.services.detector_adapter`.
- Backend entry expectation: `detect(readings: Sequence[DetectorReading]) -> DetectorResult`.
- The backend loads the active demo run, validates/authorises the run context,
  locks the relevant row, validates the generation, and persists the generation
  snapshot.
- Backend ownership includes `subject_user_id`, `demo_run_id`,
  `run_generation`, `reading_id`, `anomaly_event_id`, `incident_id`,
  `received_at`, persistence, and incident orchestration.
- The detector must not generate or accept authoritative values for those
  backend-owned fields.
- The backend must not accept `run_generation` from the mobile client or the
  reading endpoint.

### 3.2 Current implementation status

**IMPLEMENTED:** `backend/app/services/anomaly_integration.py` provides a typed
stateful wrapper:

```python
class AnomalyDetectorSession:
    def __init__(
        self,
        baseline_mean: float,
        baseline_std: float,
        config: DetectorConfig | None = None,
        *,
        detector_version: str = "sahyog-hr-threshold-v1",
    ) -> None: ...

    def detect(self, readings: Sequence[DetectorReading]) -> DetectorResult: ...
```

**INSPECTED (backend-owned):** `origin/backend` at `7de901b` now contains
`backend/app/services/detector_adapter.py`. It defines:

- Pydantic `DetectorReading(observed_at, heart_rate_bpm, activity_context=None)`.
- Pydantic single-result `DetectorResult` with `anomaly_kind`, required
  `detected_at`, optional `window_start`, `window_end`, `severity`,
  `explanation`, `detector_version`, and `evidence: list[dict[...]]` capped at
  32 entries.
- A `Detector` protocol whose `detect()` returns one result for the supplied
  readings.
- Backend-owned `canonical_dedupe_key()` and `detector_result_value()` helpers.
- `backend/app/api/readings.py` currently returns HTTP 503 from
  `get_detector()`: no authoritative provider is configured.

The backend adapter is not merged into this working branch. Role 1 must not
modify `backend/app/services/detector_adapter.py`, `backend/app/api/readings.py`,
or backend persistence. Shubhankar owns provider registration, session caching,
baseline provisioning, and database orchestration.

**IMPLEMENTED (Role 1 facade):** `backend/app/services/detector_backend_contract.py`
provides `BackendDetector`, a stateful adapter for the backend's one-result
protocol. It returns the backend Pydantic types when the backend adapter is
available, with equivalent local fallback types for isolated Role 1 testing.
The Role 1 batch session remains in `anomaly_integration.py`.

**PROPOSED:** The adapter owns the backend-context lookup and session lifecycle;
the Role 1 session owns only detector state. One `BackendDetector`/session must be
retained for one `(subject_user_id, demo_run_id, run_generation)` context and
must not be shared across generations. The detector is single-threaded and not
thread-safe. `get_detector()` currently creates a fresh dependency per request,
so Shubhankar must cache the facade or its backing session before integration.

## 4. Input contract

### 4.1 `DetectorReading`

**IMPLEMENTED** in `anomaly_integration.py`:

| Field | Type | Rule |
|---|---|---|
| `observed_at` | `datetime` | Must be timezone-aware. The backend is the source of the canonical timestamp. |
| `heart_rate_bpm` | `int` | Must be an integer; `bool` is rejected. |

The type deliberately contains **no** reading ID, subject/run/generation ID,
incident ID, anomaly-event ID, `received_at`, or activity field. Those are
backend-owned.

**BACKEND TARGET:** the backend's own `DetectorReading` additionally accepts
`activity_context: str | None = None`. The backend-facing facade accepts that
shape and ignores the activity value because the current detector has no
activity-dependent rule. The batch `anomaly_integration.DetectorReading` remains
unchanged.

**TEAM-CONFIRMED:** The backend owns timestamp normalization to UTC. The
integration type validates awareness but does not rewrite the caller's datetime;
the core detector compares instants, and the deduplication helper normalizes UTC
explicitly.

**IMPLEMENTED compatibility:**

- `DetectorReading.to_hr_sample()` produces the existing `HrSample(ts, hr)`.
- `DetectorReading.from_hr_sample(sample)` converts back and rejects naive
  timestamps.
- The existing `HrSample` and `feed()` interfaces remain available; they are not
  removed by this contract.

### 4.2 Batch semantics

`detect(readings)` accepts an ordered sequence of `DetectorReading` values.

**IMPLEMENTED:**

- `[]` is a no-op and returns an empty `DetectorResult`.
- Every supplied item is type-checked before any sample is fed. A malformed
  element raises before that call mutates detector state.
- The whole supplied sequence is fed in order; one call may produce zero, one,
  or multiple anomalies.
- State persists across calls on the same session. Do not construct a new
  detector for every reading or every batch.
- An empty batch does not reset state or counters.
- Accepted/rejected counts returned by `DetectorResult` describe **this call
  only**, not cumulative counters.

**Core detector behaviour preserved:**

- Invalid BPM, invalid timestamp, duplicate timestamps, and out-of-order
  timestamps are rejected by the core detector without changing classification
  state.
- The backend remains responsible for ingestion-level validation such as
  staleness relative to wall-clock time, authentication, and source validation.
- The detector does not silently swallow exceptions; validation and mapping
  errors are raised.

### 4.3 Backend-facing single-result facade

**IMPLEMENTED:** `backend/app/services/detector_backend_contract.py`.

```python
BackendDetector(
    baseline_mean: float,
    baseline_std: float,
    config: DetectorConfig | None = None,
    *,
    detector_version: str = "sahyog-hr-threshold-v1",
)

BackendDetector.detect(
    readings: Sequence[DetectorReading],
) -> BackendDetectorResult
```

The facade mirrors the backend adapter at `7de901b`:

| Result field | Role 1 value |
|---|---|
| `anomaly_kind` | Internal lowercase `"spike"` or `"drop"`, or `None` |
| `detected_at` | UTC-aware event time, or the last accepted reading time when no anomaly exists |
| `window_start` | First abnormal sample time for an anomaly |
| `window_end` | Event detection time for an anomaly |
| `severity` | `None` until an assignment policy is approved |
| `explanation` | Deterministic, rule-based summary grounded in evidence |
| `detector_version` | Proposed `sahyog-hr-threshold-v1` |
| `evidence` | At most the 32 most recent samples, each with UTC timestamp and integer BPM |

Rules:

- `anomaly_kind` is not the frontend/incident vocabulary; the backend maps it
  through its existing `detector_result_value()` to `HR_SPIKE`/`HR_DROP`.
- The backend route supplies one reading per call. The facade can accept a
  short sequence for testing, but raises `BackendDetectorContractError` if the
  call would produce more than one anomaly. It never silently discards an
  event. The call is evaluated on copied state, so a contract failure does not
  advance the detector.
- Empty input raises `ValueError` because the backend result requires
  `detected_at`; the backend route never sends an empty window.
- Naive timestamps and malformed reading objects are rejected before detector
  state changes.
- Core-detector rejections (invalid BPM, duplicate/out-of-order timestamps)
  produce a no-anomaly result. The backend remains responsible for ingestion
  validation and idempotency; the backend result has no rejected-count field.
- The facade is stateful across calls. The backend must retain one instance per
  run/generation; creating one in `get_detector()` per request would reset
  episode state.
- Evidence is diagnostic and transient. No ORM, migration, dashboard, or
  backend route is added by Role 1.

## 5. Baseline and session lifecycle

### 5.1 Baseline input

**PROPOSED and IMPLEMENTED:** the integration session requires an explicit
baseline at construction:

```text
baseline_mean (finite bpm)
baseline_std  (finite, >= 0)
```

The session calls the core `set_baseline` once and does not learn or adapt the
baseline during the session. Invalid baseline values raise `ValueError` and no
session is created. A baseline change on an existing core detector closes an
active episode without emitting.

**UNRESOLVED:** Who computes the baseline, whether it is fixed at run start or
recomputed, and where it is stored remain backend/product decisions. The
detector does not invent a baseline.

### 5.2 Session isolation

**PROPOSED and IMPLEMENTED:** create a new `AnomalyDetectorSession` when the
subject, demo run, or run generation changes. The wrapper holds no IDs, so the
backend must enforce isolation.

**UNRESOLVED:** The backend's exact session map, eviction policy, concurrency
locking, and lifecycle across HTTP requests. The detector is not safe for
concurrent calls.

## 6. Thresholds and configuration

**PROPOSED demo parameters, not clinical thresholds.** They are implemented in
the core detector and remain subject to owner approval.

| Parameter | Proposed value | Meaning |
|---|---:|---|
| `z_threshold` | `3.0` | Standard-deviation margin |
| `std_floor_bpm` | `2.0` | Minimum std used in the z margin |
| `min_abs_delta_bpm` | `15.0` | Minimum absolute deviation |
| `persistence_ms` | `10000` | Sustained abnormal observed time |
| `min_consecutive_abnormal_samples` | `5` | Minimum consecutive same-kind abnormal samples |
| `max_gap_ms` | `5000` | Gap that closes an episode |
| `normal_confirm_samples` | `2` | Normal samples required to close an episode |
| `valid_bpm_min` | `20` | Demo validation lower bound |
| `valid_bpm_max` | `250` | Demo validation upper bound |
| `evidence_window_ms` | `30000` | Maximum event evidence window |
| `max_evidence_samples` | `60` | Maximum event evidence samples |

Formula:

```text
effective_delta = max(z_threshold * max(std, std_floor_bpm), min_abs_delta_bpm)
spike threshold = mean + effective_delta   (inclusive)
drop threshold  = mean - effective_delta   (inclusive)
```

With `mean=72`, `std=4`, the proposed thresholds are `87` (spike) and `57`
(drop). No value is clinically derived.

## 7. Episode and event semantics

**IMPLEMENTED** in the core detector and covered by shared vectors:

1. A single abnormal sample does not emit an event.
2. An event requires both the configured consecutive sample count and the
   configured observed-time persistence.
3. Threshold comparisons are inclusive.
4. A normal sample resets the consecutive-abnormal run and its start; the active
   episode closes only after the configured number of consecutive normal
   samples.
5. A gap greater than `max_gap_ms` closes an active episode and resets
   normal-confirmation counters. Missing data cannot prove sustained
   abnormality.
6. A kind change from spike to drop (or reverse) closes the prior episode and
   starts a new one.
7. At most one event is emitted per continuous same-kind episode. Further
   abnormal samples in that episode do not duplicate the event.
8. A later sustained abnormal episode may emit a new event after the prior
   episode closes.
9. The event itself remains only:

```text
AnomalyEvent(started_at, last_hr, kind)
```

where `kind` is the internal lowercase `"spike"` or `"drop"`.

## 8. Output contract

### 8.1 Python types

**IMPLEMENTED:**

```text
DetectedAnomaly(
    event: AnomalyEvent,
    evidence: AnomalyEvidence,
    detector_result: "HR_SPIKE" | "HR_DROP",
    severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | None = None,
    detector_version: str = "sahyog-hr-threshold-v1",
)

DetectorResult(
    anomalies: tuple[DetectedAnomaly, ...] = (),
    accepted_readings: int = 0,
    rejected_readings: int = 0,
)
```

`DetectorResult.has_anomaly` and `DetectorResult.anomaly_events` are read-only
helpers. Evidence is captured immediately after each core event, before the next
reading is fed, so multiple events in one call retain distinct evidence.

Evidence field names from the core detector:

```text
kind
baseline_mean_bpm
baseline_std_bpm
effective_delta_bpm
lower_threshold_bpm
upper_threshold_bpm
first_abnormal_at
detected_at
abnormal_duration_ms
abnormal_sample_count
extreme_heart_rate_bpm
samples  # bounded tuple of (observed_at, heart_rate_bpm)
```

The `DetectedAnomaly` type contains no `confidence`, database ID, subject, demo
run, generation, incident ID, `dedupe_key`, or `received_at`.

### 8.2 Proposed backend mapping

**PROPOSED:** the backend maps `kind` through one place to
`detector_result` using the approved vocabulary. The Role 1 helper is
`map_detector_result(kind)`.

**CONFIRMED BY INSPECTION:** the backend at `7de901b` uses
`evidence.detected_at` as its `detected_at` source, `first_abnormal_at` as the
observation-window start, and `detected_at` as the window end. It expects one
result per `detect()` call and maps `anomaly_kind` through
`detector_result_value()`.

**IMPLEMENTED:** the backend-facing facade uses those exact fields and returns
one result. Evidence is bounded to 32 samples for the backend shape; the backend
does not currently persist the evidence list, and Utkarsh has not approved an
evidence migration. The Python dataclass in `anomaly_integration.py` remains a
Role 1 internal batch type, not a transport schema.

## 9. Result, severity, and confidence vocabulary

| Item | Status | Decision |
|---|---|---|
| `detector_result` values | **TEAM-CONFIRMED** | `HR_SPIKE` and `HR_DROP` |
| Internal kind | **IMPLEMENTED** | Lowercase `spike` / `drop`; do not rename internally without need |
| Severity vocabulary | **TEAM-CONFIRMED** | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| Severity assignment | **UNRESOLVED** | No policy is approved; severity is optional |
| Automatic `CRITICAL` | **TEAM-CONFIRMED negative** | Do not auto-assign |
| Confidence | **TEAM-CONFIRMED negative** | No confidence score is calculated or exposed |
| `detector_version` value | **PROPOSED** | `sahyog-hr-threshold-v1`; not an approved production version |

Role 1 code supports optional `severity` values but always defaults to `None`.
The backend must not infer severity from magnitude, duration, or an unreviewed
rule until a policy is approved. The detector must never fabricate a confidence
score.

`DETECTOR_VERSION` is currently a proposed module constant used to label
detector output. It is not approval of a versioning scheme or a backend-assigned
version contract.

## 10. Deduplication contract

### 10.1 Approved method

**TEAM-CONFIRMED** logical identity method:

1. Compose a canonical JSON payload.
2. Sort keys.
3. Use compact separators.
4. Encode as UTF-8.
5. Normalize timestamps to UTC.
6. Use fixed microsecond precision.
7. Hash with SHA-256.

The method is deterministic and must not depend on local timezone or JSON
whitespace.

### 10.2 Proposed inputs and unresolved naming

**PROPOSED input fields:** `subject_id`, `demo_run_id`, `generation`,
`detector_version`, `window_start`, `window_end`.

**PROPOSED source:** backend supplies `subject_id`, `demo_run_id`, and
`generation`; the detector supplies `detector_version` and the observation
window.

**CONFIRMED BY INSPECTION:** `origin/backend` at `7de901b` already owns
`canonical_dedupe_key()`. Its payload fields are `demo_run_id`,
`detector_version`, `kind`, `run_generation`, `subject_user_id`, `window_end`,
and `window_start`; it returns a raw SHA-256 digest with no prefix. The backend
also owns the dedupe-key unique scope and run generation. Role 1 must not wrap or
duplicate that function in the integrated path.

**IMPLEMENTED (reference only):** `backend/app/services/detector_dedupe.py`
provides `DeduplicationContext`, `canonical_dedupe_payload`, and `dedupe_sha256`
using the earlier proposed key names. It is not connected to the backend and is
retained as a deterministic reference/test helper. The backend's implementation
is authoritative.

The database unique constraint remains
`(demo_run_id, run_generation, dedupe_key)`. Run isolation is a backend
responsibility; the detector must not generate `run_generation`.

## 11. Evidence and recent-reading buffer

### 11.1 Event evidence

**TEAM-CONFIRMED:** detector evidence is bounded and transient for the initial
prototype. It is not a durable telemetry table.

**IMPLEMENTED:** the core detector retains bounded abnormal-episode samples for
the most recent emitted event. Evidence is cleared/overwritten by later detector
events and is not a general normal-monitoring history.

**UNRESOLVED:** whether any evidence is persisted, where it is stored, and which
migration adds it. DO NOT modify ORM models or Alembic migrations; do not create
`anomaly_readings` or a `last_moments` table. Utkarsh owns the migration
decision.

### 11.2 `LastMomentsBuffer`

**IMPLEMENTED:** `backend/app/services/last_moments_buffer.py` provides a
separate, bounded, in-memory recent-reading buffer.

**Why separate:** the core detector's evidence is abnormal-only and event-scoped;
it cannot supply recent normal readings or a pre-incident monitoring window. No
existing general buffer was found to reuse.

Defaults and rules:

| Item | Proposed/implemented behaviour |
|---|---|
| Maximum samples | `60` by default; caller-configurable |
| Retention | `30_000 ms` by default; caller-configurable |
| Ordering | Reject duplicates and out-of-order timestamps; count rejections |
| Timezone | Normalize accepted samples to UTC |
| Retrieval | `recent(limit)` in chronological order |
| Detection window | `window(start, end)`, inclusive |
| Evidence | `snapshot()` with first/last time, min/max bpm, rejection count |
| Memory | `deque` bounded by count; older samples pruned by retention |
| Persistence | None; in-memory only |
| Reset | `reset()` clears samples and rejection count |

**PROPOSED:** one buffer belongs to one backend lifecycle context. The backend
must create a new buffer or call `reset()` when the subject/demo-run/generation
changes. The buffer stores no IDs and has no generation token.

**UNRESOLVED:** exact buffer defaults, whether the backend needs this buffer in
the first prototype, and how it is exposed to the dashboard. The dashboard must
query backend-owned recent readings rather than treating detector evidence as a
live stream.

## 12. Verification reply classifier

**IMPLEMENTED:** `backend/app/services/reply_classifier.py`.

**Interface:**

```text
ReplyResult = ok | notOk | unrecognised
ReplyClassifier().classify(reply: str) -> ReplyResult
```

**TEAM-CONFIRMED verification context:**

- Backend action: `I_AM_OK`.
- Frontend may classify `ok`, `notOk`, and `unrecognised`.
- `notOk` is frontend-only and has no approved backend status.
- Silence is a backend verification timeout, not a classifier result.

**IMPLEMENTED classification rules:**

- Normalize Unicode NFKC, case, surrounding whitespace, punctuation, and
  apostrophe variants.
- Check negative safety phrases before positive phrases.
- Use phrase/token boundaries; do not classify substrings such as `helpful` or
  `notokay` as approved phrases.
- Return `unrecognised` for empty, whitespace-only, unrelated, or incomplete
  text.

Minimum approved positive phrases:

```text
I'm okay
I am okay
I'm fine
I'm safe
```

Minimum approved negative phrases:

```text
I'm not okay
I need help
Help me
No, I need help.
```

Implementation also accepts close variants such as `I'm OK`, `I am safe`, and
the curly-apostrophe form; these variants must be kept aligned with Flutter. The
critical invariant is that `I'm not okay` must never classify as `ok`.

**TEAM-CONFIRMED:** Flutter must preserve the same behaviour. Aditya's Flutter
files must not be modified by Role 1. The classifier does not submit a
verification response or change incident state.

## 13. Detection status versus incident lifecycle

| Surface | Values | Owner/status |
|---|---|---|
| Reading response `detection_status` | `NORMAL`, `ANOMALY_DETECTED` | **TEAM-CONFIRMED**; backend response contract |
| Detector `detector_result` | `HR_SPIKE`, `HR_DROP` | **TEAM-CONFIRMED**; detector-result vocabulary |
| Incident lifecycle | `ANOMALY_DETECTED`, `VERIFICATION_PENDING`, `FALSE_ALARM_RESOLVED`, `ESCALATED`, `RESOLVED` | Backend-owned; exact persistence/API mapping remains with Shubhankar |
| Dashboard statuses | `NORMAL`, `MONITORING`, `ANOMALY_DETECTED`, `VERIFICATION_PENDING`, `FALSE_ALARM_RESOLVED`, `ESCALATED`, `RESOLVED`, plus `RUNNING`/`COMPLETED` run labels | Actual `dashboard/src/lib/status.ts`; backend/API confirmation still required |

`ANOMALY_DETECTED` in the reading response is not by itself proof of a persisted
incident status. `NORMAL` means no anomaly indicated; it is not an incident
resolution. Do not collapse detection, verification, and escalation into one
field.

No `NOT_OK` backend status exists. No `ACKNOWLEDGED` or `CONFIRMED_EMERGENCY`
transition is approved. Earlier dashboard alias proposals are not present in the
actual inspected branch; do not implement aliases without owner confirmation.

## 14. Invariants and tests

### 14.1 Required invariants

1. The core detector remains independent of FastAPI, SQLAlchemy, APIs, databases,
   hardware, Flutter, and backend IDs.
2. A session is stateful across calls and is never instantiated per reading.
3. Empty batches do not mutate state.
4. Multiple events in one batch retain separate evidence.
5. Invalid or out-of-order readings do not change classification state.
6. `HR_SPIKE` maps only from `spike`; `HR_DROP` maps only from `drop`.
7. No confidence is produced; severity defaults to `None`.
8. Deduplication is deterministic and does not depend on JSON key order or local
   timezone.
9. The buffer remains bounded and rejects samples outside ordering/lifecycle
   expectations.
10. The classifier prefers negative safety intent and never treats silence as a
    positive reply.

### 14.2 Test status on this branch

| Suite | Command | Result |
|---|---|---|
| Core detector/vectors | `py -3.12 -m unittest backend.tests.test_anomaly -v` | PASS - 39 tests |
| Typed integration | `py -3.12 -m unittest backend.tests.test_anomaly_integration -v` | PASS - 18 tests |
| Deduplication | `py -3.12 -m unittest backend.tests.test_detector_dedupe -v` | PASS - 14 tests |
| Last moments buffer | `py -3.12 -m unittest backend.tests.test_last_moments_buffer -v` | PASS - 18 tests |
| Reply classifier | `py -3.12 -m unittest backend.tests.test_reply_classifier -v` | PASS - 13 tests |
| Backend contract facade | `py -3.12 -m unittest backend.tests.test_detector_backend_contract -v` | PASS - 16 tests |
| Combined suites | Module invocation for all six suites | PASS - 118 tests |
| Compile check | `py -3.12 -m compileall -q backend` | PASS |

These are unit tests only. The backend adapter exists on `origin/backend` at
`7de901b`, but it is not merged into this branch and no running backend/database
is available here, so no live integration test is claimed. An ad hoc
compatibility check loaded that adapter via `git show` and confirmed the facade
returns its `DetectorResult` and maps the anomaly kind correctly. `pytest`, Ruff,
Flutter, and a runnable backend application are not available in this
environment.

## 15. Unresolved decisions and readiness

| Decision | Owner | Status/impact |
|---|---|---|
| Register a detector provider in `get_detector()` | Shubhankar | **BLOCKED**; route still returns 503 |
| Retain the stateful facade per run/generation and supply a baseline | Shubhankar | **UNRESOLVED**; must not instantiate per request |
| Backend result Pydantic shape and one-result-per-call behavior | Shubhankar | **CONFIRMED BY INSPECTION** at `7de901b`; facade matches |
| Multiple anomalies in one backend call | Shubhankar + Prasiddh | **UNRESOLVED**; facade raises rather than dropping events |
| Severity assignment policy | Shubhankar + Utkarsh | **UNRESOLVED**; vocabulary approved, assignment is not |
| Baseline computation/persistence ownership | Shubhankar | **UNRESOLVED** |
| Evidence persistence or migration | Utkarsh | **UNRESOLVED**; backend result carries bounded evidence but does not persist it |
| Dashboard/incident backend APIs and integration | Shubhankar + Vaishnavi | **BLOCKED**; dashboard uses mock contract |
| Incident status aliases/dashboard mapping | Shubhankar + Vaishnavi | **UNRESOLVED**; actual branch uses canonical lifecycle strings, no approved aliases |
| Flutter classifier parity and timestamp source | Aditya | **BLOCKED**; no Flutter project inspected/modified |
| Clinical validity | Product owner | **NOT CLAIMED**; demo rules only |

**Readiness:** Role 1 code, including the backend-facing facade, is unit-tested
and ready to be consumed by the backend owner. It is **not integrated**, **not
backend-tested against a running application/database**, and **not approved as a
clinical or production detector**.

**End of `docs/detector_integration_contract.md`.**
