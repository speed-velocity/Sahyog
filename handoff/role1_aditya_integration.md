# SAHYOG Role 1 — Aditya Integration Handoff

**For:** Aditya (Role 4: Flutter Android Frontend)  
**Branch:** `Ai/ml-and-monitoring`  
**Commit:** `d21d457` — fix(role-1): enforce UTC timestamps and align with Python 3.12  

This document contains the exact interfaces and patterns Aditya can rely on for integrating the Role 1 implementation into the Flutter application.

---

## 1. Exact Dart Imports

```dart
// HrSample — immutable heart-rate reading model
import 'package:sahyog_monitoring/features/monitoring/domain/hr_sample.dart';

// HeartRateSource — abstraction for reading sources
import 'package:sahyog_monitoring/features/monitoring/domain/heart_rate_source.dart';

// SimScenario — the three approved demo scenario identifiers
import 'package:sahyog_monitoring/features/monitoring/domain/sim_scenario.dart';

// SimulatorHeartRateSource — deterministic generator for all three scenarios
import 'package:sahyog_monitoring/features/monitoring/domain/simulator_heart_rate_source.dart';

// BackendDetectionResult — parser for POST /api/v1/readings response
import 'package:sahyog_monitoring/core/ml/backend_detection_result.dart';

// AnomalyEvent — backend-confirmed anomaly information model
import 'package:sahyog_monitoring/core/ml/anomaly_event.dart';

// LastMomentsBuffer — bounded in-memory rolling buffer for UI
import 'package:sahyog_monitoring/core/buffer/last_moments_buffer.dart';
```

---

## 2. Exact Public Signatures

### `HrSample`
```dart
class HrSample {
  final DateTime ts; // UTC timestamp
  final int hr;      // Heart rate in BPM

  const HrSample({required this.ts, required this.hr});

  HrSample copyWith({DateTime? ts, int? hr});

  bool operator ==(Object other);
  int get hashCode;
  String toString();
}
```

### `HeartRateSource`
```dart
abstract class HeartRateSource {
  Stream<HrSample> get samples;
  Future<void> start();
  Future<void> stop();
}
```

### `SimScenario`
```dart
enum SimScenario {
  normal,
  trueAnomaly,
  falseAlarm,
  @override
  String toString(); // returns 'NORMAL', 'TRUE_ANOMALY', 'FALSE_ALARM'
}
```

### `SimulatorHeartRateSource`
```dart
class SimulatorHeartRateSource {
  SimulatorHeartRateSource({Duration sampleInterval = const Duration(seconds: 3)});

  Duration get sampleInterval;
  SimScenario? get scenario;
  bool get isRunning;

  List<HrSample> generateSamples(); // idempotent, fresh list each call

  Future<void> start(); // emits first sample immediately, throws StateError if already running
  Future<void> stop();  // prevents additional readings

  void setScenario(SimScenario newScenario); // throws StateError if called while running
}
```

### `BackendDetectionResult`
```dart
class BackendDetectionResult {
  BackendDetectionResult({
    required this.accepted,
    required this.detectionStatus,
    this.readingId,
    this.demoRunId,
    this.anomalyEventId,
    this.incidentId,
  });

  final bool accepted;
  final String detectionStatus; // 'NORMAL' or 'ANOMALY_DETECTED'
  final String? readingId;
  final String? demoRunId;
  final String? anomalyEventId;
  final String? incidentId;

  factory BackendDetectionResult.fromJson(Map<String, dynamic> json);
  Map<String, dynamic> toJson();
}
```

### `LastMomentsBuffer`
```dart
class LastMomentsBuffer {
  LastMomentsBuffer({int maxSamples = 60, int maxMs = 30000});

  int get sampleCount;
  int get rejectionCount;

  void add(HrSample sample);
  List<HrSample> recent([int limit]);
  HrBufferSnapshot snapshot();
  HrBufferSnapshot window(DateTime start, DateTime end);
  void reset();
}
```

---

## 3. Scenario Setup

```dart
// Select a scenario before starting the simulator
final simulator = SimulatorHeartRateSource();
simulator.setScenario(SimScenario.normal); // or trueAnomaly, falseAlarm
```

The three scenario identifiers are exactly `NORMAL`, `TRUE_ANOMALY`, `FALSE_ALARM` — sent as strings to `POST /api/v1/demo/runs`.

---

## 4. Stream Subscription Example

```dart
// Listen to simulator samples
final simulator = SimulatorHeartRateSource()..setScenario(SimScenario.normal);

simulator.samples.listen((HrSample sample) {
  // Process each reading sample
  // Submit to backend via POST /api/v1/readings
});
```

---

## 5. Start / Stop / Restart Example

```dart
// Start the simulator with a scenario
await simulator.start();

// Emit continues until stop() is called
// The first sample is emitted immediately after start()

// Stop the simulator
await simulator.stop();

// Restart the same instance (after stop)
await simulator.start();
await simulator.stop();

// Restart with a different scenario
simulator.setScenario(SimScenario.trueAnomaly);
await simulator.start();
await simulator.stop();
```

**Important:** `setScenario()` must be called before `start()`. Calling `setScenario()` while the simulator is running throws `StateError`.

---

## 6. BackendDetectionResult Parsing Example

```dart
// Parse the actual POST /api/v1/readings response
final jsonResponse = {
  'accepted': true,
  'detection_status': 'ANOMALY_DETECTED',
  'reading_id': 'reading_001',
  'demo_run_id': 'run_001',
  'anomaly_event_id': 'event_001',
  'incident_id': 'incident_001',
};

final result = BackendDetectionResult.fromJson(jsonResponse);

if (result == null) {
  // Malformed response — should not happen with well-formed backend
  return;
}

// Check detection status
if (result.detectionStatus == 'ANOMALY_DETECTED') {
  // Proceed to verification flow
  // Show verification prompt to the user
}

// If NORMAL, continue to next reading
```

**Note:** `accepted` is always `true` for valid readings. The key field is `detection_status`.

**Reading-level vs incident-level distinction:**
- `detection_status == 'ANOMALY_DETECTED'` → triggers verification workflow
- `detection_status == 'NORMAL'` → no anomaly, continue readings
- `anomalyEventId` and `incidentId` are optional — they are `null` when no anomaly detected
- Do not confuse `ANOMALY_DETECTED` (reading status) with incident lifecycle status (`ESCALATED`, `RESOLVED_FALSE_ALARM`, etc.)

---

## 7. LastMomentsBuffer Usage

```dart
// Create buffer with defaults (max 60 samples, 30s retention)
final buffer = LastMomentsBuffer();

// Add samples as they arrive from the simulator
buffer.add(HrSample(
  ts: sample.ts,
  hr: sample.hr,
));

// Get recent samples (chronological order, oldest first)
final recentSamples = buffer.recent(limit: 10);

// Get a snapshot with min/max BPM and timestamps
final snapshot = buffer.window(
  DateTime.now().subtract(const Duration(seconds: 30)),
  DateTime.now(),
);

// Reset buffer when scenario changes
buffer.reset();
```

**Key behaviors:**
- Duplicate timestamps are rejected (increment `rejectionCount`)
- Out-of-order timestamps are rejected (increment `rejectionCount`)
- Samples outside the `maxMs` window from the newest sample are rejected
- Buffer is bounded by `maxSamples` — oldest samples are pruned when exceeded
- `recent()` and `snapshot()` return fresh lists — modifications do not affect the buffer
- `reset()` clears all samples and resets `rejectionCount` to 0

---

## 8. Test File Locations and Execution

**Test files (under `mobile/test/`):**
- `hr_sample_test.dart` — HrSample unit tests
- `simulator_test.dart` — SimulatorHeartRateSource unit tests
- `backend_detection_result_test.dart` — BackendDetectionResult unit tests
- `last_moments_buffer_test.dart` — LastMomentsBuffer unit tests

**To run Dart tests (once Flutter project is scaffolded):**
```powershell
dart test mobile/test/
// or, within Flutter:
flutter test test/
```

**Test coverage:**
- HrSample: valid BPM, invalid BPM, UTC timestamp, immutability
- Simulator: deterministic sequences, first reading emitted immediately, timestamps UTC and increasing, restart continuity, no duplicate start, stop prevents emissions, restart works, scenario selection
- BackendDetectionResult: parse NORMAL response, parse ANOMALY_DETECTED response, handle missing fields, handle null values, malformed detection_status, toJson round-trip, equality
- LastMomentsBuffer: add sample, chronological retrieval, max sample count, time-based expiry, duplicate rejection, out-of-order rejection, snapshot immutability, reset behavior

---

## 9. Fields Aditya Can Rely On

The following are guaranteed by the Role 1 implementation:

| Field | Guarantee |
|---|---|
| `HrSample.ts` | Always UTC (`DateTime.utc()` or `.toUtc()`) |
| `HrSample.hr` | Always within 20-250 BPM range (validated on construction) |
| `SimScenario.values` | Exactly `normal`, `trueAnomaly`, `falseAlarm` |
| `SimScenario.toString()` | Returns `'NORMAL'`, `'TRUE_ANOMALY'`, `'FALSE_ALARM'` |
| `SimulatorHeartRateSource.sampleInterval` | Defaults to 3 seconds; configurable before `start()` |
| `BackendDetectionResult.fromJson()` | Returns `null` for malformed JSON; missing `accepted` or `detectionStatus` |
| `BackendDetectionResult.detectionStatus` | Always `'NORMAL'` or `'ANOMALY_DETECTED'` (never other values) |
| `LastMomentsBuffer.recent()` | Returns list in chronological order (oldest first); never mutates internal buffer |
| `LastMomentsBuffer.window()` | Returns snapshot based on sample timestamps, not wall-clock time |

---

## 10. Backend Response Fields That Remain Unavailable

The following backend response fields are **not** included in the `POST /api/v1/readings` response and must not be assumed:

| Field | Status |
|---|---|
| `detected_at` | Not in POST response — requires backend database query via `anomaly_event_id` |
| `kind` | Not in POST response — requires backend database query |
| `last_hr` | Not in POST response — requires backend database query |
| `first_abnormal_at` | Not in POST response — requires backend database query |
| `duration_ms` | Not in POST response — requires backend database query |
| `demoRunId` | Available in POST response as `demo_run_id` String? |
| `anomalyEventId` | Available in POST response as `anomaly_event_id` String? |
| `incidentId` | Available in POST response as `incident_id` String? |

**Important:** `AnomalyEvent.fromJson()` cannot populate from the `POST /api/v1/readings` response directly. The `anomaly_event_id` should be used to look up the full event from the backend database.

---

## 11. Integration Assumptions Requiring Aditya's Confirmation

The following assumptions are subject to Aditya's confirmation during Flutter project scaffolding:

- [ ] **Flutter project test configuration:** `pubspec.yaml` test dependency and `flutter test` setup
- [ ] **API client implementation:** `POST /api/v1/readings` and `POST /api/v1/demo/runs` HTTP client
- [ ] **Verification UI:** `I_AM_OK` action and reply classifier integration
- [ ] **Demo run lifecycle:** `demo_run_id` generation and management per scenario
- [ ] **Timestamp handling:** How `DateTime` timestamps are converted to ISO 8601 strings for API submission
- [ ] **Buffer integration:** Whether `LastMomentsBuffer` is used in the monitoring UI and to what extent

**Do not implement:** API client, UI components, ReplyClassifier, or backend database queries. These are Aditya's responsibilities.

**Do not reference:** `ReplyClassifier`, `ReplyResult`, or an unsupported `NOT_OK` action.

---

## 12. Backend Correction Record — UTC Timestamp Enforcement

**Task:** Role 1 correction follow-up  
**Status:** `TESTED`  
**Implementation commit:** `d21d4570e9237285186a8162f4ac9aba1d84ad09`

### Behaviour now enforced by `AnomalyDetector.feed()`

| Input | Behaviour |
|---|---|
| Naive `datetime` (`tzinfo is None`) | Rejected — `rejected_sample_count` increments, `feed()` returns `None` |
| Aware `datetime` whose `utcoffset()` is `None` | Rejected — same counter, `feed()` returns `None` |
| Aware `datetime` in any timezone | Normalized to UTC via `astimezone(UTC)` before ordering and persistence checks |
| Non-`datetime` `ts`, non-`int` or out-of-range `hr` | Rejected exactly as before — unchanged |

The detector never raises for malformed samples; rejection is silent apart from the counter. `DetectorSnapshot.last_accepted_ts` is always the normalized UTC value.

### What changed

- `backend/app/services/anomaly.py` — added the naive-timestamp rejection guard and UTC normalization in `feed()`; corrected the `HrSample` docstring, which previously stated that naive and aware timestamps must not be mixed.
- `backend/tests/test_anomaly.py` — replaced `test_naive_and_aware_timestamps_are_not_mixed` with `test_naive_timestamps_are_rejected`, asserting `accepted_sample_count == 0`, `rejected_sample_count == 1` and `last_accepted_ts is None` for a naive sample, then that aware samples are accepted and normalized.

No signature, dataclass field, `__all__` export or backend API field changed.

### Python version alignment

The correction uses `from datetime import UTC`, matching the declared target: `requires-python = ">=3.12,<3.13"` and Ruff `target-version = "py312"`. Python 3.10 compatibility is **not** claimed and must not be assumed.

### Verification

| Check | Command | Result |
|---|---|---|
| Lint | `uv run --locked ruff check .` | All checks passed |
| Format | `uv run --locked ruff format --check .` | 82 files already formatted |
| Role 1 suites | `uv run --locked pytest tests/test_anomaly.py tests/test_anomaly_integration.py tests/test_detector_dedupe.py tests/test_last_moments_buffer.py tests/test_detector_backend_contract.py tests/test_reply_classifier.py` | 118 passed (39/18/14/18/16/13), 0 failed, 0 skipped |
| Ordinary suite | `uv run --locked pytest -m "not integration"` | 164 passed, 1 skipped, 27 deselected |
| Compile | `py -m compileall -q backend` | exit 0 |

`tests/test_postgresql_schema.py` was not executed locally: it requires `SAHYOG_TEST_DATABASE_URL`, which CI supplies through its PostgreSQL service container.

### Unchanged

- `detector_version` was already part of the backend contract (`detector_backend_contract.py`) before this commit; no detector-version field was added or modified.
- Ownership boundaries are unchanged — see §11. Backend database queries, API clients and UI remain outside Role 1.

---

## Change Log

| Date | Change | Owner |
|---|---|---|
| 2026-11-27 | Initial version — aligned simulator constructor, verified backend response fields, updated documentation | Prasiddh |
| 2026-11-28 | Recorded UTC timestamp enforcement correction, Python 3.12 alignment, and verified results (commit `d21d457`) | Prasiddh |