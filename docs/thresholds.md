# SAHYOG - Anomaly Detection Thresholds and Decision Record

**Project:** SAHYOG - Detect. Verify. Respond.
**Document:** `docs/thresholds.md`
**Owner:** Prasiddh (Role 1 - AI/ML and health monitoring)
**Last updated:** 2026-11-25
**Status:** Detector and backend-facing facade `IMPLEMENTED` and unit-tested;
thresholds are **PROPOSED demo parameters**, not clinical thresholds. Integration
is `NOT INTEGRATED`.
**Companion:** `docs/detector_integration_contract.md` and
`docs/integration_gaps.md`

> **No value in this document is a clinical threshold or medical advice.** SAHYOG
> is a simulated prototype. The detector is a deterministic rule-based system, not
> a trained model and not a medical device.

This revision keeps the detector semantics from Phase 1/1.5 and replaces stale
open questions with the Phase 2/3 team decisions. Detection thresholds and vector
expectations remain Role 1 proposals unless a table explicitly says otherwise.

---

## 1. Purpose

This document records:

1. The confirmed integration context relevant to the detector.
2. The proposed rule-based heart-rate detector semantics.
3. Every proposed numerical parameter and its status.
4. The boundary between detector output and backend/dashboard contracts.
5. The unresolved decisions and the owner of each decision.
6. The implementation and test status on branch `Ai/ml-and-monitoring`.

It does not claim that the backend provider is registered, that an API route is
live, that database persistence/dashboard APIs are implemented, that Flutter is
mirrored, or that the incident state machine is integrated. The backend adapter
exists on `origin/backend` at `7de901b`; Role 1 provides a facade that matches its
single-result shape but does not modify backend-owned files.

## 2. Authority and status language

Priority:

1. Latest team decisions supplied in the Phase 2/3 prompt.
2. `PRD.md` and `SYSTEM_DESIGN.md`.
3. `TEAM.md` ownership.
4. Shared and individual handoffs.
5. Inspected remote schema and code.
6. Existing Role 1 code.

| Label | Meaning |
|---|---|
| **TEAM-CONFIRMED** | Approved boundary or vocabulary; implementation may still be pending. |
| **IMPLEMENTED** | Present in Role 1 code and covered by unit tests. |
| **PROPOSED** | Role 1 proposal awaiting approval. |
| **UNRESOLVED** | No owner decision yet; do not silently choose a contract. |
| **BLOCKED** | Depends on a missing component owned by another role. |

## 3. Confirmed integration context

### 3.1 Backend boundary

**TEAM-CONFIRMED:**

- Canonical route: `POST /api/v1/readings`.
- The normal response contains `reading_id`, `demo_run_id`, `accepted`, and
  `detection_status: "NORMAL"`.
- The anomaly response additionally contains `anomaly_event_id` and
  `incident_id`, with `detection_status: "ANOMALY_DETECTED"`.
- `NORMAL` and `ANOMALY_DETECTED` are detection-response values, not incident
  lifecycle states.
- Adapter location: `backend.app.services.detector_adapter`.
- Expected entry point:
  `detect(readings: Sequence[DetectorReading]) -> DetectorResult`.
- The backend loads the active demo run, locks the relevant row, validates the
  generation, and persists the generation snapshot.
- Backend owns `subject_user_id`, `demo_run_id`, `run_generation`, `reading_id`,
  `anomaly_event_id`, `incident_id`, `received_at`, persistence, and incident
  orchestration.
- The detector must not create or accept authoritative values for those fields.
- `run_generation` must not be accepted from the mobile client or reading
  endpoint.

**INSPECTED:** `origin/backend` at `7de901b` contains the adapter, Pydantic
schemas, reading route, persistence service, and a `get_detector()` placeholder
that still returns HTTP 503. The adapter is not merged into this working branch.

**BLOCKED:** no registered detector provider or running backend/database exists
on this branch; a live end-to-end reading test cannot be claimed.

### 3.2 Result and severity vocabulary

**TEAM-CONFIRMED:**

- Detector-result values: `HR_SPIKE` and `HR_DROP`.
- Internal detector kinds remain lowercase `spike` and `drop`; map them in one
  integration layer.
- Severity vocabulary: `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
- Severity is optional, and no assignment policy is approved. Do not fabricate,
  auto-assign, or mark every anomaly `CRITICAL`.
- No calibrated confidence score exists. Do not calculate, expose, persist, or
  display a confidence value.

**PROPOSED:** `detector_version = "sahyog-hr-threshold-v1"`. This is a Role 1
label, not an approved production version scheme.

### 3.3 Database context

The inspected remote integration branch
`origin/Software-integration-and-database` at `4df7d3b` contains ORM models only;
no migrations or API routes were found there.

Relevant `AnomalyEvent` fields:

`anomaly_event_id`, `subject_user_id`, required `demo_run_id` and
`run_generation`, `detected_at`, `detector_result`, optional `severity`, optional
`explanation`, optional `detector_version`, and `dedupe_key`.

Confirmed constraints relevant to Role 1:

- Unique on `(demo_run_id, run_generation, dedupe_key)`.
- `detector_result` and `dedupe_key` are required `Text`.
- `severity`, `explanation`, and `detector_version` are nullable `Text`.
- No CHECK constraint was found for allowed `detector_result`, `severity`, or
  incident status values; application-level approval is still required.
- No anomaly-event-to-reading association exists. Do not invent
  `anomaly_readings`.
- No anomaly evidence or last-moments persistence column was confirmed.
- Do not modify ORM models or migrations; Utkarsh owns that decision.

### 3.4 Dashboard and location context

`origin/Dashboard-and-location` was fetched and inspected read-only at
`c3afb24` (`feat: complete dashboard and location modules`). It contains the
dashboard, backend location service/API, and location tests.

Actual dashboard `status.ts` uses:

`NORMAL`, `MONITORING`, `ANOMALY_DETECTED`, `VERIFICATION_PENDING`,
`FALSE_ALARM_RESOLVED`, `ESCALATED`, `RESOLVED`, plus run labels `RUNNING` and
`COMPLETED`. Unknown values are displayed verbatim. The earlier proposed aliases
`DETECTED`, `PENDING_VERIFICATION`, `ACKNOWLEDGED`, `CONFIRMED_EMERGENCY`, and
`FALSE_ALARM` are not present in that file.

The dashboard severity display map uses `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`,
but this does not approve a severity-assignment policy.

The dashboard calls `/dashboard/overview`, `/incidents`, `/incidents/{id}`,
`/hospitals/nearby`, and `/location/latest` under `/api/v1`. The inspected branch
has no backend `main.py`, dashboard API, or incident API. Location routes exist
but are not mounted. Full gaps are recorded in `docs/integration_gaps.md`.

The dashboard handoff claims HEAD `ee5baed` and uncommitted changes; the actual
remote HEAD is `c3afb24`. Treat that handoff as stale until Vaishnavi reconciles
it.

## 4. Detector scope and definitions

Scope: one heart-rate value in whole bpm, simulated source only.

| Term | Proposed definition |
|---|---|
| Baseline | Externally supplied mean and standard deviation of normal resting heart rate for the demo subject/run. |
| Spike | A sample at or above the upper threshold. |
| Drop | A sample at or below the lower threshold. |
| Abnormal sample | A spike or a drop. |
| Sustained abnormality | Enough consecutive same-kind abnormal samples spanning enough observed time. |
| Episode | One continuous period of same-kind abnormal samples, not separated by the normal confirmation rule or a data gap. |
| Event | The detector's one structured output per episode that satisfies persistence. |
| Gap | Elapsed observed time between consecutive accepted samples greater than the configured maximum. |
| Stale sample | A sample rejected by the backend because it is too old relative to backend current time. Backend-owned, not detector-owned. |
| Out-of-order sample | A sample whose `observed_at` is not later than the last accepted sample. |

The detector does not know about subjects, runs, generations, reading IDs,
incidents, verification, escalation, or database rows.

## 5. Baseline and detector state

Proposed and implemented:

1. The baseline is explicit. The detector does not invent a default and does not
   adapt or learn during a run.
2. `set_baseline(mean, std)` replaces the pair atomically. Invalid values raise
   `ValueError` and leave the previous baseline unchanged.
3. Validation requires finite values, `std >= 0`, and a mean within the demo BPM
   range.
4. Without a valid baseline, no event can be emitted.
5. Replacing a baseline closes an active episode without emitting and resets
   episode counters. It does not reset the last accepted timestamp or retained
   evidence.
6. `reset()` clears baseline, counters, timestamps, evidence, and episode state.
7. The integration session requires a baseline at construction; no session is
   created with an invalid baseline.

The Phase 1 Python API uses `set_baseline`, `feed`, `reset`, and `snapshot`.
The Dart-facing `setBaseline` mirror is not implemented because no Flutter project
is present in this workspace.

**UNRESOLVED:** who computes the baseline, whether it is fixed at run start or
recomputed, and where it is stored. The detector must not assume a value.

## 6. Threshold semantics and proposed parameters

Formula:

```text
effective_delta = max(z_threshold * max(std, std_floor_bpm), min_abs_delta_bpm)
upper threshold  = mean + effective_delta   (inclusive)
lower threshold  = mean - effective_delta   (inclusive)
```

Every row is a **PROPOSED** demo parameter, not a clinical value.

| Parameter | Proposed value | Interpretation | Status |
|---|---:|---|---|
| `z_threshold` | `3.0` | Standard deviations from baseline | PROPOSED |
| `std_floor_bpm` | `2.0` | Minimum std used in z calculation | PROPOSED |
| `min_abs_delta_bpm` | `15` | Absolute bpm deviation also required | PROPOSED |
| `persistence_ms` | `10000` | Sustained abnormal observed time | PROPOSED |
| `min_consecutive_abnormal_samples` | `5` | Minimum abnormal samples in episode | PROPOSED |
| `max_gap_ms` | `5000` | Gap that breaks an episode | PROPOSED |
| `normal_confirm_samples` | `2` | Normal samples required to close an episode | PROPOSED |
| `valid_bpm_min` | `20` | Demo validation lower bound | PROPOSED |
| `valid_bpm_max` | `250` | Demo validation upper bound | PROPOSED |
| `evidence_window_ms` | `30000` | Maximum evidence window per event | PROPOSED |
| `max_evidence_samples` | `60` | Maximum evidence samples per event | PROPOSED |

With baseline `mean=72`, `std=4`:

- `effective_delta = max(3.0 * 4, 15) = 15 bpm`
- spike threshold = `87 bpm` (inclusive)
- drop threshold = `57 bpm` (inclusive)

`sampling_interval_ms` belongs to the simulator and is not detector
configuration. The separate `LastMomentsBuffer` defaults (`60` samples, `30_000`
ms retention) are proposed/implemented monitoring defaults, not detector
thresholds.

## 7. Episode semantics

Implemented and covered by shared vectors:

1. A single noisy spike or drop never emits an event.
2. An event requires both:
   - at least `min_consecutive_abnormal_samples` consecutive same-kind abnormal
     samples; and
   - at least `persistence_ms` of observed time from the first abnormal sample in
     the current consecutive run.
3. Duration is measured on sample `observed_at` timestamps, not wall-clock time
   and not `received_at`.
4. A normal sample resets the consecutive-abnormal count and run start. The
   duration guard must be re-established.
5. An active episode closes after `normal_confirm_samples` consecutive normal
   samples. This hysteresis prevents one noisy normal sample from ending an
   episode.
6. A gap greater than `max_gap_ms` closes any active episode and resets
   normal-confirmation counters. Missing data cannot prove sustained abnormality.
7. A kind change from spike to drop (or reverse) closes the previous episode and
   starts a new one.
8. At most one event is emitted per continuous same-kind episode. Further
   abnormal samples in that episode do not produce duplicate events.
9. A later sustained episode may emit a new event after the prior episode closes.
10. Out-of-order, duplicate, invalid, or mixed naive/aware samples are rejected
    without changing classification state. The backend separately owns staleness
    checks and ingestion validation.

The core detector compares datetimes as instants and rejects mixed naive/aware
values. **TEAM-CONFIRMED:** the backend normalizes timestamps to UTC. The
integration type requires an aware datetime; the deduplication helper normalizes
UTC explicitly.

## 8. Event and evidence output

The core event remains:

```text
AnomalyEvent(started_at, last_hr, kind)
```

- `started_at`: first abnormal sample timestamp of the run that satisfied
  persistence.
- `last_hr`: heart rate of the sample that completed persistence.
- `kind`: internal lowercase `spike` or `drop`.

The event contains no IDs, subject/run/generation, severity, confidence, dedupe
key, or detector version.

Implemented event-time evidence:

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

Evidence is diagnostic, bounded, transient, and captured immediately after an
emitted event. It is not a durable API contract and is not an anomaly-reading
association.

**PROPOSED backend mapping:**

- `kind` -> `HR_SPIKE` / `HR_DROP` through one mapping helper.
- `evidence.detected_at` -> proposed backend `detected_at`.
- `first_abnormal_at` / `detected_at` -> proposed logical observation window.
- `severity` -> omitted until approved.
- `confidence` -> never fabricated.
- `dedupe_key`, IDs, run generation, subject, and incident references ->
  backend-owned.

**CONFIRMED BY INSPECTION:** the backend calls the detector synchronously in
`POST /api/v1/readings`, expects one Pydantic `DetectorResult`, and does not
persist the evidence list. The result requires `detected_at` even for no anomaly;
the Role 1 facade supplies the last accepted reading time in that case.

**IMPLEMENTED:** `backend/app/services/detector_backend_contract.py` maps a
single anomaly to `anomaly_kind` (`"spike"`/`"drop"`), UTC `detected_at`,
`window_start`/`window_end`, optional severity, deterministic explanation,
detector version, and at most 32 recent evidence samples. The backend maps the
kind to `HR_SPIKE`/`HR_DROP` and owns persistence/deduplication. If one call
would produce more than one anomaly, the facade raises rather than dropping
events.

## 9. Integration-facing result types

Implemented in `backend/app/services/anomaly_integration.py`:

```text
DetectedAnomaly(
    event,
    evidence,
    detector_result,     # "HR_SPIKE" | "HR_DROP"
    severity=None,       # optional approved vocabulary; no assignment policy
    detector_version="sahyog-hr-threshold-v1",
)

DetectorResult(
    anomalies=(),        # zero, one, or multiple independent episodes
    accepted_readings=0, # this call only
    rejected_readings=0, # this call only
)
```

`DetectorResult.has_anomaly` and `.anomaly_events` are conveniences. The session
is stateful across calls and is not thread-safe. Empty batches do not mutate
state. Multiple events in one batch retain distinct evidence.

The typed integration interface intentionally has no database context, confidence,
or dedupe key.

The backend-facing facade is separate:

```text
BackendDetector(baseline_mean, baseline_std, config=None, ...)
BackendDetector.detect(readings) -> BackendDetectorResult
```

It accepts backend-shaped readings (including `activity_context`), persists
state across calls, and returns the backend's exact result field names. It uses
the backend Pydantic classes when they are available and equivalent local
fallback classes for isolated unit tests. It is stateful and not thread-safe;
backend code must retain one instance per active run/generation context.

## 10. Deduplication boundary

**TEAM-CONFIRMED method:** canonical JSON, sorted keys, compact separators,
UTF-8, UTC-normalized timestamps, fixed microsecond precision, SHA-256.

**PROPOSED inputs:** `subject_id`, `demo_run_id`, `generation`,
`detector_version`, `window_start`, `window_end`.

**PROPOSED source:** backend supplies subject/run/generation; detector supplies
version and observation window.

**IMPLEMENTED (reference only):** `backend/app/services/detector_dedupe.py`
provides a backend-context dataclass, canonical payload, and raw lowercase
SHA-256 digest. It adds no prefix and is not called by the core detector.

**CONFIRMED BY INSPECTION:** `origin/backend` at `7de901b` already implements the
authoritative `canonical_dedupe_key()` with `subject_user_id`, `demo_run_id`,
`run_generation`, `kind`, `detector_version`, `window_start`, and `window_end`.
The backend owns the final key and unique scope. Do not introduce a competing
dedupe function in the integrated path or assume an `anomaly:v1:` prefix. The
database unique scope remains `(demo_run_id, run_generation, dedupe_key)` and
`run_generation` remains backend-owned.

## 11. Evidence, monitoring buffer, and verification

### 11.1 Recent-reading buffer

The core detector's evidence is abnormal-only and event-scoped; it cannot supply
current/live BPM or a normal-monitoring history.

**IMPLEMENTED:** `backend/app/services/last_moments_buffer.py` is a separate,
bounded, in-memory buffer with:

- `60` default samples and `30_000` ms default retention;
- UTC-normalized, ordered timestamps;
- duplicate/out-of-order rejection and counters;
- `recent(limit)`, inclusive `window(start, end)`, and compact `snapshot()`;
- `reset()` for lifecycle isolation;
- no persistence and no subject/run/generation IDs.

The backend must create a new buffer or reset it when the subject/demo-run/
generation changes. Whether this buffer is required in the first prototype and
how it is exposed to the dashboard remain unresolved. The dashboard must query
backend readings, not treat detector evidence as a live stream.

### 11.2 Reply classifier

**IMPLEMENTED:** `backend/app/services/reply_classifier.py` returns `ok`,
`notOk`, or `unrecognised` and follows the team-confirmed verification context:

- backend action: `I_AM_OK`;
- `notOk` is frontend-only and has no backend status;
- silence is a backend timeout, not a classifier result.

Normalization handles case, whitespace, punctuation, apostrophes, and Unicode
NFKC. Negative safety phrases are checked first. The critical invariant is that
`I'm not okay` never returns `ok`. The classifier does not submit a response or
change incident state. Flutter must preserve equivalent behavior; Aditya's files
must not be modified by Role 1.

## 12. Deterministic vectors and tests

`docs/anomaly_vectors.json` contains 19 proposed vectors using millisecond offsets
from a vector-local start. Covered categories include normal steady/variation,
single-sample spike/drop, noisy normal, sustained spike/drop, second episodes,
gap break, out-of-order rejection, invalid BPM rejection, no baseline, exact and
one-bpm-inside boundaries, kind change, and baseline replacement.

Test results on this branch:

| Command | Result |
|---|---|
| `py -3.12 -m unittest backend.tests.test_anomaly -v` | PASS - 39 tests |
| `py -3.12 -m unittest backend.tests.test_anomaly_integration -v` | PASS - 18 tests |
| `py -3.12 -m unittest backend.tests.test_detector_dedupe -v` | PASS - 14 tests |
| `py -3.12 -m unittest backend.tests.test_last_moments_buffer -v` | PASS - 18 tests |
| `py -3.12 -m unittest backend.tests.test_reply_classifier -v` | PASS - 13 tests |
| `py -3.12 -m unittest backend.tests.test_detector_backend_contract -v` | PASS - 16 tests |
| Combined six-suite invocation | PASS - 118 tests |
| `py -3.12 -m compileall -q backend` | PASS |

`unittest discover` is blocked by the shared namespace-package layout because
`backend/tests` has no `__init__.py`; module invocation is used instead. Adding
package files requires owner approval.

These are unit tests only. The backend adapter exists on `origin/backend` at
`7de901b`, but no running backend/database is available on this branch, so no
live integration test is claimed. An ad hoc check loaded that adapter via
`git show` and confirmed the facade returns its result type and kind mapping.
`pytest`, Ruff, Flutter, and a runnable backend are not available in this
environment.

## 13. Implementation status

**Implemented and unit-tested:**

- `backend/app/services/anomaly.py`: core detector.
- `backend/tests/test_anomaly.py`: vectors and detector tests.
- `backend/app/services/anomaly_integration.py`: typed batch interface and
  immediate evidence capture.
- `backend/tests/test_anomaly_integration.py`: interface tests.
- `backend/app/services/detector_dedupe.py`: deterministic dedupe helper.
- `backend/tests/test_detector_dedupe.py`: canonicalization/hash tests.
- `backend/app/services/last_moments_buffer.py`: bounded recent-reading buffer.
- `backend/tests/test_last_moments_buffer.py`: buffer tests.
- `backend/app/services/reply_classifier.py`: conservative classifier.
- `backend/tests/test_reply_classifier.py`: classifier tests.
- `backend/app/services/detector_backend_contract.py`: backend single-result
  facade with bounded evidence and transactional contract handling.
- `backend/tests/test_detector_backend_contract.py`: backend-shape/contract tests.
- `docs/anomaly_vectors.json`, `docs/thresholds.md`,
  `docs/detector_integration_contract.md`, `docs/integration_gaps.md`,
  `handoff/prasiddh.md`.

**Not implemented / not changed:**

- No backend adapter file, reading route, Pydantic schema, ORM model, migration,
  dashboard, location, Flutter, or incident state machine was modified by Role 1.
- The backend adapter inspected on `origin/backend` remains owned by Shubhankar;
  Role 1's facade is the integration seam.
- No severity assignment, confidence generation, durable evidence, or live
  backend/dedupe integration.
- No registered provider; `get_detector()` still returns 503 on `origin/backend`.
- Commit/push status is recorded in `handoff/prasiddh.md`.

## 14. Unresolved decisions and owners

### Shubhankar (backend)

1. Register the Role 1 `BackendDetector` facade in `get_detector()` and retain
   one instance per active run/generation instead of creating it per request.
2. Supply the approved baseline and decide its lifecycle/persistence.
3. Decide how to handle a backend call that would produce multiple anomalies;
   the facade raises rather than dropping events.
4. Confirm the canonical incident status vocabulary and allowed transitions;
   distinguish reading `detection_status` from persisted incident status.
5. Confirm the reading response validation/error structure and live auth/run
   ownership for the route.

### Utkarsh (database/integration)

1. Confirm whether evidence or location persistence requires a migration and
   whether compact evidence is sufficient.
2. Confirm allowed detector-result/severity values and whether CHECK constraints
   will be added.
3. Confirm `IncidentAnomalyEvent.evidence_role` semantics and that it is not an
   anomaly-reading association.
4. Confirm that all IDs/run generations remain backend-assigned.

### Vaishnavi (dashboard/location)

1. Reconcile the stale handoff HEAD and confirm the tested revision.
2. Confirm status/display semantics for `MONITORING`, `RUNNING`, and `COMPLETED`
   versus incident lifecycle values.
3. Align location snapshot fields and incident-scoped location usage with the
   backend service.
4. Confirm evidence display: event summary versus bounded sample evidence.
5. Confirm severity display only when the backend supplies an approved value.

### Aditya (Flutter)

1. Provide the actual Flutter project, simulator lifecycle, and `SimMode`.
2. Confirm the timestamp/UTC boundary and baseline source.
3. Preserve the Python classifier behavior, especially the `I'm not okay`
   invariant.
4. Confirm whether the Dart detector is preview-only or authoritative; Role 1
   assumes Python backend authority per `SYSTEM_DESIGN.md`.

## 15. Non-goals and honesty constraints

- No trained ML model is proposed; this is a rule-based/statistical detector.
- No clinical accuracy, diagnosis, or emergency-dispatch claim is made.
- No smartwatch, Bluetooth, ESP32, MAX30102, or cloud ML integration is in scope.
- The detector does not create incidents, verification records, escalations,
  reading IDs, anomaly-event IDs, incident IDs, subject IDs, or run generations.
- The backend detector remains authoritative for incident-creating decisions.
- The detector and buffer are in-memory and single-threaded; not production-safe.
- Thresholds, vectors, severity policy, and dashboard mappings remain proposals
  unless explicitly marked **TEAM-CONFIRMED**.

**End of `docs/thresholds.md`.**
