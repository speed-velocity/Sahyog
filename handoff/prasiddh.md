# Individual Handoff - Prasiddh

**Owner:** Prasiddh
**Role:** Role 1 - AI/ML and Health Monitoring
**Last updated:** 2026-11-25
**Branch:** `Ai/ml-and-monitoring`
**Base commit:** `1cdf0ee821319b4ac814051535754282c201ea7b` (all work below is
uncommitted)
**Task ID:** No separate Phase 2/3 ID was supplied. This slice continues HandOff
A2.1-A2.12 and the Phase 1/1.5 detector work.
**Status:** `IMPLEMENTED` and `TESTED` at unit level; `NOT INTEGRATED`.

## 1. Summary

Phase 1 implemented the deterministic Python heart-rate anomaly detector,
expanded the shared vectors to 19 cases, and added a stdlib `unittest` suite.

Phase 1.5 fixed an overflow-validation defect, strengthened the vector harness,
and documented the detector, dashboard, schema, and integration boundaries.

Phase 2/3 added a typed stateful detector integration interface, a deterministic
logical deduplication helper, a bounded `LastMomentsBuffer`, a conservative
`ReplyClassifier`, unit tests for each, and two integration documents. It also
inspected the latest `Dashboard-and-location` branch read-only and recorded the
dashboard/backend/location gaps.

No backend adapter, route, Pydantic schema, ORM model, migration, dashboard file,
location file, Flutter file, or shared incident state machine was modified.

The detector is rule-based, not a trained model. Thresholds and vectors remain
Role 1 demo proposals, not clinical thresholds or approved production contracts.

## 2. Completed Work

### Phase 1 / 1.5

- `backend/app/services/anomaly.py`: `HrSample`, `DetectorConfig`, `Thresholds`,
  `AnomalyEvent`, `AnomalyEvidence`, `DetectorSnapshot`, `compute_thresholds`,
  and `AnomalyDetector`.
- `backend/tests/test_anomaly.py`: loads all 19 vectors, checks expected events,
  rejection counters, final state, evidence bounds/consistency, and thresholds.
- `docs/anomaly_vectors.json`: 19 deterministic vectors using millisecond offsets.
- Phase 1.5: `_require_finite` converts oversized numeric `OverflowError` to the
  documented `ValueError`; vector structure/evidence checks were strengthened;
  overflow regression test added; command documentation corrected.

### Phase 2 typed integration

`backend/app/services/anomaly_integration.py`:

- `DetectorReading(observed_at, heart_rate_bpm)`:
  - aware datetime required;
  - integer BPM required;
  - no backend IDs/context;
  - conversion to/from the existing `HrSample` interface.
- `DetectedAnomaly(event, evidence, detector_result, severity=None,
  detector_version=...)`:
  - maps internal `spike`/`drop` to `HR_SPIKE`/`HR_DROP`;
  - validates event/evidence consistency;
  - carries optional severity only; no confidence;
  - exposes proposed observation-window start/end from evidence.
- `DetectorResult(anomalies, accepted_readings, rejected_readings)`:
  - per-call counts;
  - zero/one/multiple anomalies;
  - no backend fields.
- `AnomalyDetectorSession(baseline_mean, baseline_std, config=None, *,
  detector_version=...)`:
  - holds one core detector;
  - requires an explicit baseline;
  - prevalidates the whole batch before feeding;
  - preserves state across calls;
  - captures evidence immediately after each event;
  - returns per-call accepted/rejected counts.

`backend/tests/test_anomaly_integration.py`: 18 tests covering conversion,
validation, empty batch, normal/spike/drop, multiple episodes with distinct
evidence, cross-call state, invalid/out-of-order readings, no confidence/database
fields, and mapping/count validation.

### Phase 2 deduplication

`backend/app/services/detector_dedupe.py`:

- `DeduplicationContext(subject_id, demo_run_id, generation, detector_version,
  window_start, window_end)`.
- Validates non-empty identifiers, positive integer generation, aware
  timestamps, and non-inverted windows.
- `canonical_dedupe_payload`: sorted keys, compact separators, UTF-8,
  UTC-normalized timestamps with fixed microsecond precision.
- `dedupe_sha256`: raw lowercase SHA-256 hex digest; no prefix.
- Exact canonical key names/prefix remain unresolved and are documented.

`backend/tests/test_detector_dedupe.py`: 14 tests covering exact canonical JSON,
fixed microseconds, offset equivalence, UTF-8, field sensitivity, raw digest
shape, and validation.

### Phase 2 monitoring buffer

`backend/app/services/last_moments_buffer.py`:

- Separate from the event-scoped core evidence buffer.
- Bounded by sample count and retention; defaults 60 samples / 30,000 ms.
- UTC-normalized, ordered timestamps; duplicate/out-of-order rejection counted.
- `recent`, inclusive `window`, compact `snapshot`, and `reset`.
- No IDs, no persistence, no unbounded storage.

`backend/tests/test_last_moments_buffer.py`: 18 tests covering count/time
bounds, ordering, UTC normalization, retrieval, snapshots, reset, and validation.

### Phase 2 reply classifier

`backend/app/services/reply_classifier.py`:

- `ReplyResult.ok`, `notOk`, `unrecognised`.
- `ReplyClassifier().classify(reply)` and convenience `classify_reply`.
- Handles case, whitespace, punctuation, curly apostrophes, Unicode NFKC.
- Checks negative safety phrases before positive phrases.
- Treats silence/empty input as `unrecognised`, not `ok` or `notOk`.
- Does not submit verification or change incident state.

`backend/tests/test_reply_classifier.py`: 13 tests including all required
phrases, `I'm not okay` regression, conflicts, unrelated text, word boundaries,
result values, and invalid types.

### Phase 3 inspection and documentation

- Safely fetched `origin/Dashboard-and-location`; updated from `ee5baed` to
  `c3afb24` (`feat: complete dashboard and location modules`).
- Read-only inspection of dashboard types/client/status/config, package metadata,
  location service/API, tests, and Vaishnavi's handoff. No dashboard README or
  lint script was found; dependencies are React 18, Vite 6, and Vitest 3.
- Confirmed no backend detector adapter, dashboard/incident backend APIs, or
  backend application exists on the inspected branches.
- Recorded stale dashboard handoff metadata, status-vocabulary findings, route
  gaps, type/field gaps, location/auth/durability gaps, and evidence-display
  gaps.
- Created `docs/detector_integration_contract.md` with approved/implemented/
  proposed/unresolved distinctions.
- Created `docs/integration_gaps.md` with exact paths and owners.
- Updated `docs/thresholds.md` to remove stale Phase 1.5 decisions and reflect
  the Phase 2/3 boundary without changing detector semantics.

## 3. Detector Behaviour Preserved

- `effective_delta = max(z_threshold * max(std, std_floor_bpm),
  min_abs_delta_bpm)`.
- Inclusive thresholds: `hr >= upper` is spike; `hr <= lower` is drop.
- Event requires both minimum consecutive abnormal samples and persistence time.
- One event per continuous same-kind episode.
- Normal confirmation closes an episode; a normal sample restarts persistence.
- Gap greater than `max_gap_ms` closes an episode.
- Kind change, baseline replacement, and reset close/reset active episodes as
  documented.
- Invalid, duplicate, out-of-order, and mixed naive/aware samples are rejected
  without changing classification state.
- Core events contain only `started_at`, `last_hr`, and `kind`.
- Evidence is bounded, diagnostic, transient, and contains no IDs or confidence.
- Backend context, persistence, and incident orchestration remain backend-owned.

## 4. Files Changed

All files below are uncommitted. No tracked file was modified.

| File | Reason | Status |
|---|---|---|
| `backend/app/services/anomaly.py` | Core detector and Phase 1.5 overflow fix | Untracked, TESTED |
| `backend/tests/test_anomaly.py` | 39 detector/vector tests | Untracked, TESTED |
| `docs/anomaly_vectors.json` | 19 shared vectors | Untracked, TESTED |
| `backend/app/services/anomaly_integration.py` | Typed stateful batch interface | Untracked, TESTED |
| `backend/tests/test_anomaly_integration.py` | 18 integration-interface tests | Untracked, TESTED |
| `backend/app/services/detector_dedupe.py` | Proposed deterministic dedupe helper | Untracked, TESTED |
| `backend/tests/test_detector_dedupe.py` | 14 dedupe tests | Untracked, TESTED |
| `backend/app/services/last_moments_buffer.py` | Bounded recent-reading buffer | Untracked, TESTED |
| `backend/tests/test_last_moments_buffer.py` | 18 buffer tests | Untracked, TESTED |
| `backend/app/services/reply_classifier.py` | Conservative reply classifier | Untracked, TESTED |
| `backend/tests/test_reply_classifier.py` | 13 classifier tests | Untracked, TESTED |
| `docs/thresholds.md` | Updated detector/decision record | Untracked, updated |
| `docs/detector_integration_contract.md` | Role 1 integration contract | Untracked, created |
| `docs/integration_gaps.md` | Read-only cross-component gap report | Untracked, created |
| `handoff/prasiddh.md` | This Phase 2/3 handoff | Untracked, updated |

No dashboard, location, ORM, migration, API route, Flutter, or teammate-owned file
was changed. No `__init__.py` was added.

## 5. Interfaces

### Consumed

- Team-confirmed backend/detector boundary and detection-response vocabulary.
- `backend.app.services.detector_adapter` as the future adapter location; no
  adapter was created.
- Existing Phase 1 detector interface and shared vectors.
- Read-only `origin/Software-integration-and-database` ORM models at `4df7d3b`.
- Read-only `origin/Dashboard-and-location` dashboard/location files and handoff.
- `SYSTEM_DESIGN.md` lifecycle and ownership context.

### Exposed

- Existing core detector types and `AnomalyDetector` interface.
- `DetectorReading`, `DetectedAnomaly`, `DetectorResult`,
  `AnomalyDetectorSession`, `map_detector_result`, `DETECTOR_VERSION`.
- `DeduplicationContext`, `canonical_dedupe_payload`, `dedupe_sha256`.
- `LastMomentsBuffer`, `BufferEvidence`.
- `ReplyClassifier`, `ReplyResult`, `classify_reply`.

### Changed

- No shared API, database, Flutter, dashboard, location, or backend service
  contract was changed.
- No adapter, route, ORM model, or migration was added.
- The new Python interfaces are Role 1 proposals/implementation, not approved
  transport schemas.

## 6. Commands Executed and Results

| Command | Result |
|---|---|
| `py -3.12 -m unittest backend.tests.test_anomaly -v` | PASS - 39 tests |
| `py -3.12 -m unittest backend.tests.test_anomaly_integration -v` | PASS - 18 tests |
| `py -3.12 -m unittest backend.tests.test_detector_dedupe -v` | PASS - 14 tests |
| `py -3.12 -m unittest backend.tests.test_last_moments_buffer -v` | PASS - 18 tests |
| `py -3.12 -m unittest backend.tests.test_reply_classifier -v` | PASS - 13 tests |
| Combined module invocation for all five suites | PASS - 102 tests, 0 failures |
| `py -3.12 -m compileall -q backend` | PASS |
| `py -3.12 -m unittest discover -s backend/tests -t . -v` | BLOCKED - `Start directory is not importable`; `backend/tests` has no `__init__.py` |
| `git fetch origin Dashboard-and-location` | UPDATED - `ee5baed..c3afb24` |
| `git show origin/Dashboard-and-location:<file>` | Read-only inspection |

Not run:

- Backend/integration tests: no adapter/backend application exists.
- Dashboard tests/typecheck/build: Role 2-owned; not rerun by Role 1, and the
  handoff HEAD is stale.
- Ruff/pytest: not installed on this branch; no dependencies installed.
- Flutter analyzer/tests: no Flutter project/SDK used.
- Database/migration checks: no schema changes made.
- Load tests or parallel-run tests.

`unittest discover` is blocked by the shared namespace-package layout. Adding
`__init__.py` files requires owner approval and was not done.

## 7. Test Coverage

Core detector/vectors (39):

- All 19 shared vectors and vector structure.
- Threshold formula, std floor, inclusive/one-bpm-inside boundaries.
- Configuration/baseline validation, atomic replacement, oversized numerics.
- Persistence by count and duration; gap boundaries; normal confirmation.
- Kind change; one event per episode; rejected samples; reset.
- Evidence bounds/window; event contract; no backend fields.

Typed integration (18):

- Input validation/conversion.
- Empty/normal/spike/drop/multi-episode batches.
- Cross-call state; distinct evidence; invalid/out-of-order counts.
- No confidence/database fields; mapping/count validation.

Dedupe (14):

- Canonical JSON exactness, sorted/compact/UTF-8.
- UTC/fixed-microsecond equivalence.
- Subject/run/generation/version/window sensitivity.
- Raw SHA-256 shape and validation.

Buffer (18):

- Count and time bounds; boundary retention; zero retention.
- Ordering/duplicate rejection; UTC normalization.
- Recent/window retrieval; snapshots; reset; invalid inputs.

Classifier (13):

- Approved positive/negative phrases and variants.
- Required `I'm not okay` regression.
- Conflicting safety intent prefers `notOk`.
- Empty/whitespace/unrelated text is `unrecognised`.
- Exact enum values; invalid types.

## 8. Commit

- None. Commit and push intentionally not performed.
- Commit ID: none.
- Working branch remains `Ai/ml-and-monitoring`.
- All Role 1 work is uncommitted.

## 9. Known Issues and Limitations

- No backend adapter exists; no integration test is possible or claimed.
- Exact `DetectorResult` transport schema, evidence delivery, and sync/async
  behavior remain unresolved.
- Exact dedupe-key field names/prefix and digest representation remain
  unresolved; helper returns a raw digest only.
- Severity vocabulary is approved, but assignment policy is not. Detector emits
  `severity=None`.
- No confidence score exists and none should be displayed.
- Baseline computation/persistence ownership is unresolved.
- Session storage/concurrency/lifecycle in the backend is unresolved; the
  session is single-threaded and not thread-safe.
- Evidence is transient and event-scoped; no persistence/migration is approved.
- No backend application or dashboard/incident APIs exist; the dashboard runs
  against mocks only.
- Dashboard handoff metadata is stale (`ee5baed` claimed vs `c3afb24` actual).
- Actual dashboard status map uses canonical lifecycle strings plus
  `MONITORING`/`RUNNING`/`COMPLETED`; incident-state semantics remain to be
  confirmed.
- Location service is in-memory, unauthenticated, and not mounted; seeded
  hospitals are demo data.
- Dashboard types omit some backend location fields and expect an
  `AnomalyEvent[]` evidence shape that needs backend mapping.
- Flutter classifier parity and timestamp conversion are unverified.
- `unittest discover` is blocked by the namespace-package layout.
- Python on PATH is 3.10.11; tests use `py -3.12` because the backend targets
  3.12.
- No clinical validity or production readiness is claimed.

## 10. Decision Register

### Confirmed by latest team decisions

1. Adapter path: `backend.app.services.detector_adapter`; expected entry:
   `detect(readings: Sequence[DetectorReading]) -> DetectorResult`.
2. Backend owns subject/run/generation, IDs, receipt time, persistence, and
   incident orchestration. The detector must not generate or accept those values.
3. Backend loads/locks the active demo run, validates generation, and persists
   the generation snapshot. Mobile/reading endpoint must not supply
   `run_generation`.
4. Detector result values: `HR_SPIKE` and `HR_DROP`.
5. Severity vocabulary: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`; optional, with no
   approved assignment policy.
6. No confidence score.
7. Verification action `I_AM_OK`; `notOk` is frontend-only; silence is a backend
   timeout.
8. Evidence is transient/bounded initially; no ORM/JSON/migration change by
   Role 1.
9. Dedupe method: canonical JSON, sorted keys, compact separators, UTF-8, UTC,
   fixed microseconds, SHA-256.
10. Detection status values: `NORMAL`, `ANOMALY_DETECTED`, distinct from incident
    lifecycle.
11. Backend normalizes UTC; frontend must preserve classifier behavior.
12. No `NOT_OK` backend status, no invented incident transitions, no
    `anomaly_readings`, no `last_moments` persistence.

### Unresolved / owner decisions

**Shubhankar (backend):**

1. Implement adapter, exact result serialization, evidence delivery, and
   sync/async behavior.
2. Confirm session scoping, locking, reset, and per-run/generation lifecycle.
3. Confirm canonical incident status values/transitions and whether dashboard
   labels are aliases/display-only.
4. Confirm exact dedupe-key prefix/format and reading-response validation/error
   structure.
5. Confirm baseline source/lifecycle and auth/ownership for dashboard/location
   APIs.

**Utkarsh (database/integration):**

1. Decide whether evidence, location, or last-moments persistence needs a
   migration; Role 1 must not modify ORM/migrations.
2. Confirm allowed values/CHECK constraints for `detector_result`/`severity`.
3. Confirm `IncidentAnomalyEvent.evidence_role` semantics and that it is not an
   anomaly-reading association.
4. Confirm all IDs/run generations remain backend-assigned.

**Vaishnavi (dashboard/location):**

1. Reconcile stale handoff HEAD with actual `c3afb24` and confirm tested revision.
2. Confirm `MONITORING`/`RUNNING`/`COMPLETED` semantics versus incident states.
3. Align lifecycle/location types with backend schemas.
4. Confirm evidence display: event summaries versus sample evidence.
5. Show severity only when backend supplies it; do not invent confidence.

**Aditya (Flutter):**

1. Provide Flutter project, `SimMode`, simulator lifecycle, and constructor
   signatures.
2. Confirm timestamp/UTC boundary and baseline source.
3. Preserve Python classifier behavior, especially `I'm not okay` -> `notOk`.
4. Confirm preview-only versus authoritative Dart detector; Role 1 assumes Python
   backend authority.

## 11. Next Actions

1. Share `docs/detector_integration_contract.md` and
   `docs/integration_gaps.md` with Shubhankar, Utkarsh, Vaishnavi, and Aditya.
2. Do not create the adapter or backend route in Role 1; Shubhankar owns it.
3. After owner approval of the result payload, dedupe representation, baseline
   lifecycle, and session lifecycle, run real backend integration tests.
4. Re-run the complete unit/compile checks after any approved interface change.
5. Only mark `INTEGRATED` after a real backend consumes the detector and the
   normal/true-anomaly/false-alarm flows pass.
6. Produce the required final report with exact test/build evidence.

**End of `handoff/prasiddh.md`.**
