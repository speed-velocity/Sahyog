# SAHYOG Dart Interface Contract — Proposed for Aditya's Review

**Purpose:** This document proposes exact Dart interfaces for the Flutter frontend (Role 4). It is not a direct implementation — Aditya will review and apply the design. No backend files are modified.

**Latest backend baseline:** `fea72cb`  
**Python detector/backend integration:** APPROVED and SIGNED OFF  
**Flutter/backend three-scenario E2E:** Still pending  

---

## 1. Overview and Ownership Boundary

| Component | Owner | Detection Authority |
|---|---|---|
| **Backend anomaly detection** | Shubhankar / Prasiddh | **Authoritative** — decides incident creation |
| **Flutter simulator** | Aditya | **No detection** — generates and submits readings |
| **Flutter verification** | Aditya | Consumes backend `detection_status`; submits `I_AM_OK` action |

**Critical:** Flutter must NOT implement a local threshold-based anomaly detector. The backend Python `AnomalyDetectorSession` is the sole decision-maker for anomaly events. Flutter submits readings and consumes backend `detection_status` responses.

---

## 2. Classes and Interfaces

### 2.1 `HrSample`

Heart rate sample model used by the simulator to represent a single reading.

**Constructor:** `HrSample({required DateTime ts, required int hr})`

**Fields:**
- `ts`: `DateTime` — UTC timestamp of the reading (timezone-aware, offset=0)
- `hr`: `int` — Heart rate in beats per minute

**Validates:** `hr` must be in range 20-250 (demo bounds per `thresholds.md`)

**Error:** Throws `ArgumentError` if `hr` is outside valid range

**Rationale:** This is the internal Dart representation of a heart-rate sample. It mirrors the backend `DetectorReading` shape but exists only in the Flutter simulator — the backend owns the Pydantic `DetectorReading` model.

**Example:**
```dart
final sample = HrSample(ts: DateTime.parse('2026-11-23T10:00:03Z'), hr: 78);
```

**Immutability:** All fields are `final`; no modifying methods exist after construction.

**`copyWith`:** `HrSample copyWith({required DateTime? ts, required int? hr})` — returns a copy with potentially different values. Null parameters retain the original value.

**Equality:** `operator ==` and `hashCode` based on `ts` and `hr`.

---

### 2.2 `HeartRateSource`

abstraction for the source of heart-rate readings.

**Public interface:**
- `Stream<HrSample> get samples` — Stream of readings from this source. Emits in chronological order with UTC timestamps. Broadcast or single-subscription depending on implementation.
- `Future<void> start()` — Start generating and emitting readings.
- `Future<void> stop()` — Stop further emissions and clean up resources.

**Rationale:** Per `PRD.md` §100 and `SYSTEM_DESIGN.md` D1, all generated readings must carry a source marker such as `SIMULATED`. The Flutter app must never imply that a real wearable is connected.

---

### 2.3 `SimScenario`

Enum identifying which demo scenario to run. These are the three exact scenario identifiers approved by the team.

**Values:**
- `normal` — NORMAL — no anomaly, no incident, no verification, no escalation
- `trueAnomaly` — TRUE_ANOMALY — sustained abnormal pattern; detection → verification → escalation
- `falseAlarm` — FALSE_ALARM — same abnormal pattern triggers detection, but user confirms `I_AM_OK` → `RESOLVED_FALSE_ALARM`

**String values:** `'NORMAL'`, `'TRUE_ANOMALY'`, `'FALSE_ALARM'` — these are the exact strings sent to the backend `POST /api/v1/demo/runs` endpoint.

**Rationale:** Per `SYSTEM_DESIGN.md` §4.1 and `PRD.md` §133, the three scenario identifiers are exactly `NORMAL`, `TRUE_ANOMALY`, `FALSE_ALARM`. The same pipeline is used for all three; they differ in input data and expected outcome, not in underlying implementation.

**Important:** `TRUE_ANOMALY` and `FALSE_ALARM` use the same abnormal reading pattern. The distinction is the demo scenario and subsequent verification outcome. The readings can be identical — what changes is the user's verification response.

---

### 2.4 `SimulatorHeartRateSource`

Simulated heart-rate source that generates deterministic reading sequences per scenario. This is the Flutter-side simulator — it does not perform anomaly detection.

**Constructor:** `SimulatorHeartRateSource({Duration sampleInterval = const Duration(seconds: 3)})`
- `sampleInterval`: approximate interval between successive readings (default 3 seconds)

**Public fields:**
- `SimScenario? scenario` — the selected scenario (`null` if not yet set via `setScenario()`)
- `bool isRunning` — whether the simulator is actively generating readings
- `List<HrSample> samplesList` — the generated sequence of samples (read-only after generation)

**Public methods:**
- `List<HrSample> generateSamples()` — generates the deterministic sample sequence for the selected scenario. Returns a fresh list each call (idempotent, no internal mutable state exposed).
- `Future<void> start()` — starts the simulator, generates the first reading immediately, and begins emitting stream events. Throws `StateError` if a scenario is already running.
- `Future<void> stop()` — stops the simulator, cancels pending emissions. Does NOT call any backend reset endpoint; the backend owns incident lifecycle.
- `void setScenario(SimScenario newScenario)` — sets the demo scenario. May only be called when the simulator is not running. Throws `StateError` if called while running. After calling this, call `start()` to generate the sample sequence for the new scenario.

**Lifecycle rules:**
- Scenario must be set via `setScenario()` before calling `start()`.
- `start()` emits the first sample immediately.
- No duplicate timer on repeated `start()` — throws `StateError` if a scenario is already running.
- `stop()` prevents additional readings — after calling `stop()`, no new samples will be emitted.
- Restarting the same simulator instance works — call `start()` again after `stop()`.
- Scenario change: `setScenario()` cannot be called while running — create a new `SimulatorHeartRateSource` instance for a different scenario.
- Timestamps are UTC and strictly increasing.
- Timestamps remain strictly increasing across stop/start cycles.
- No random sample values — all sequences are deterministic.
- No random timestamps — all timestamps are generated via `DateTime.now().utc`.

**Verification flow:**
1. Simulator generates deterministic `HrSample` sequences per scenario.
2. Flutter app submits each sample via `POST /api/v1/readings`.
3. Backend returns `detection_status` (`NORMAL` or `ANOMALY_DETECTED`).
4. If `ANOMALY_DETECTED`, Flutter shows verification prompt.
5. User selects `I_AM_OK` through Aditya's verification UI.
6. Aditya's API client submits the verification action to the backend.
7. Backend owns the resulting incident state.

---

### 2.5 `BackendDetectionResult`

Model for the actual backend `POST /api/v1/readings` response.

**Constructor:** `BackendDetectionResult({required bool accepted, required String detectionStatus, String? readingId, String? demoRunId, String? anomalyEventId, String? incidentId})`

**Fields:**
- `accepted`: `bool` — Whether the reading was accepted and processed by the backend.
- `detectionStatus`: `String` — The backend's detection status for this reading.
  - `NORMAL`: no anomaly pattern detected.
  - `ANOMALY_DETECTED`: an unusual pattern was detected by the backend detector. This triggers the verification workflow; it is NOT an incident lifecycle status.
- `readingId`: `String?` — Unique identifier assigned by the backend for this reading.
- `demoRunId`: `String?` — The backend-assigned demo run ID linking this reading to the active demo scenario.
- `anomalyEventId`: `String?` — Optional anomaly event ID, if an anomaly was detected and an event was created by the backend.
- `incidentId`: `String?` — Optional incident ID, if an incident was created as a result of the anomaly detection and subsequent verification/escalation flow.

**Static method:**
- `BackendDetectionResult.fromJson(Map<String, dynamic> json)` — Parses a `BackendDetectionResult` from the backend's JSON response body. Returns `null` if the JSON is malformed or missing required fields (`accepted`, `detectionStatus`).

**JSON field mapping (from `POST /api/v1/readings` response):**
| JSON field | Dart field | Type |
|---|---|---|
| `accepted` | `accepted` | `bool` |
| `detection_status` | `detectionStatus` | `String` |
| `reading_id` | `readingId` | `String?` |
| `demo_run_id` | `demoRunId` | `String?` |
| `anomaly_event_id` | `anomalyEventId` | `String?` |
| `incident_id` | `incidentId` | `String?` |

**`toJson()`:** Converts this model to a JSON map suitable for serialization or debugging.

**Example:**
```dart
final result = BackendDetectionResult.fromJson({
  'accepted': true,
  'detection_status': 'ANOMALY_DETECTED',
  'reading_id': 'reading_001',
  'demo_run_id': 'run_001',
  'anomaly_event_id': 'event_001',
  'incident_id': 'incident_001',
});
// result.accepted == true
// result.detectionStatus == 'ANOMALY_DETECTED'
// etc.
```

**Verification flow integration:**
1. Flutter submits a reading via `POST /api/v1/readings`.
2. The API response is parsed into a `BackendDetectionResult`.
3. If `result.detectionStatus == 'ANOMALY_DETECTED'`, proceed to verification.
4. If `result.detectionStatus == 'NORMAL'`, continue to the next reading.

---

### 2.6 `AnomalyEvent`

Event model representing a backend-confirmed anomaly information model.

**Note:** This model is constructed from backend data, not from local threshold detection. The `POST /api/v1/readings` response includes `anomaly_event_id` (a UUID), but the full anomaly event details (`detected_at`, `kind`, `last_hr`, `duration_ms`) are not included in the POST response. To obtain the full `AnomalyEvent`, the Flutter app must query the backend database using the `anomaly_event_id`.

**Fields (when constructed from backend data):**
- `detectedAt`: `DateTime` — UTC timestamp of detection.
- `kind`: `String` — Internal kind: `"spike"` or `"drop"`.
- `lastHr`: `int` — Heart rate of the sample that completed the anomaly event.
- `firstAbnormalAt`: `DateTime` — UTC timestamp of the first abnormal sample.
- `durationMs`: `int` — How long the abnormal pattern persisted, in milliseconds.

**Factory:**
- `AnomalyEvent.fromJson(Map<String, dynamic> json)` — Parses an `AnomalyEvent` from a JSON map. Returns `null` if any required field is missing or `kind` is not `'spike'` or `'drop'`. **Note:** This factory cannot populate an `AnomalyEvent` from the `POST /api/v1/readings` response alone, as the required fields are not included. The `anomaly_event_id` from the response should be used to look up the full event from the backend.

**Error behavior:** Asserts that `kind` is either `'spike'` or `'drop'`.

**Example (from backend database query, not from POST response):**
```dart
// This would require a separate backend query, not direct fromJson from POST response
final event = AnomalyEvent(
  detectedAt: DateTime.parse('2026-11-23T10:00:05Z'),
  kind: 'spike',
  lastHr: 88,
  firstAbnormalAt: DateTime.parse('2026-11-23T10:00:03Z'),
  durationMs: 30000,
);
```

---

### 2.7 `LastMomentsBuffer`

Bounded rolling buffer of recent heart-rate samples. The current demo's evidence remains transient in memory — no database table, migration, or persistence layer.

**Constructor:** `LastMomentsBuffer({int maxSamples = 60, int maxMs = 30000})`
- `maxSamples`: maximum number of samples retained (default 60).
- `maxMs`: maximum retention window in milliseconds (default 30,000 / 30 seconds).

**Public methods:**
- `add(HrSample sample)`: `void` — adds a sample to the buffer. Rejects duplicates and out-of-order timestamps; counts rejections internally.
- `recent([int limit])`: `List<HrSample>` — returns up to `limit` recent samples in chronological order (oldest first). Defaults to `maxSamples`.
- `snapshot()`: `HrBufferSnapshot` — returns `HrBufferSnapshot` with first/last time, min/max BPM, and rejection count.
- `window(DateTime start, DateTime end)`: `HrBufferSnapshot` — returns snapshot of samples whose timestamps fall within `[start, end]`, inclusive.
- `reset()`: `void` — clears all samples and the rejection count.

**Rules:**
- Duplicate and out-of-order timestamps are rejected; rejection count increments.
- Accepted samples are normalized to UTC and ordered chronologically.
- Buffer remains bounded by `maxSamples`; older samples are pruned when the limit is exceeded.
- `reset()` clears all samples and the rejection count to 0.
- No IDs, no persistence, no unbounded storage — purely in-memory.
- Snapshot collections cannot mutate the internal buffer (returned lists are new instances).
- Empty-buffer behavior is safe — `recent()` returns `[]`, `window()` returns an empty snapshot.

**Rationale:** Per `detector_integration_contract.md` §11.2, the `LastMomentsBuffer` is a separate, bounded, in-memory recent-reading buffer. It is distinct from the core detector's evidence (which is abnormal-only and event-scoped). The buffer cannot supply normal readings or a pre-incident monitoring window from the core detector's evidence alone.

**Why a Flutter-side buffer may not be needed:** The backend already owns its detector evidence (bounded to 32 samples). If the Flutter UI only needs to display the most recent readings for context, the buffer can be optional — the backend can supply recent readings on demand via the dashboard API. However, if a local buffer is desired for UI preview purposes, the above specification provides a bounded, resettable implementation.

**Unit tests and expected outputs:**
- `LastMomentsBuffer()` with defaults creates a buffer with `maxSamples=60`, `maxMs=30000`.
- `add(HrSample(ts: DateTime.parse('2026-11-23T10:00:03Z'), hr: 78))` adds a sample; `recent()` returns it.
- Adding a duplicate timestamp increments rejection count but does not add a duplicate sample.
- Adding a timestamp earlier than the latest rejected sample increments rejection count and is not added.
- `snapshot().firstHr` and `snapshot().lastHr` return the correct min/max.
- `reset()` clears all samples and resets rejection count to 0.
- Buffer remains bounded: adding more than `maxSamples` prunes oldest samples.
- `maxMs` retention: samples outside the window are rejected on `add()`.

---

### 3. Detection Boundary Resolution

#### 3.1 AnomalyDetector Ownership Question

**Conflict:** The TEAM ownership list mentions `AnomalyDetector`, but Aditya explicitly requires Flutter to consume backend detection results rather than independently decide whether an anomaly occurred.

**Proposed resolution:** Define `AnomalyDetector` strictly as a **backend-result adapter** with no local threshold logic. Two options:

**Option A (Recommended):** Omit local anomaly detection from Flutter entirely. Use `AnomalyEvent`/`backend response model` instead. Flutter reads `detection_status` from the `POST /api/v1/readings` response and acts accordingly. No local detector is created.

**Option B:** Define `AnomalyDetector` as a backend-result adapter abstraction, with no local threshold logic. It maps backend `detector_result`/`anomaly_kind` to local `AnomalyEvent` for display purposes only. It explicitly documents that the backend is authoritative and local use does not trigger incident creation.

**Do not silently choose a competing detector implementation.** The contract must reflect that the backend Python anomaly service is the sole decision-maker for incident-creating anomaly events.

---

### 4. Reading Submission Flow (Full)

The complete flow for all three scenarios:

```
1. Flutter start scenario
   → POST /api/v1/demo/runs({scenario: SimScenario})
   ← returns demo_run_id

2. For each reading in the scenario sequence:
   → HrSample generated by SimulatorHeartRateSource
   → POST /api/v1/readings({
       demo_run_id,
       source: "SIMULATED",
       timestamp: sample.ts.toIso8601String(),
       heart_rate_bpm: sample.hr,
       activity: "RESTING",
     })
   ← returns {reading_id, demo_run_id, accepted, detection_status}

   - If detection_status == "NORMAL": continue to next reading
   - If detection_status == "ANOMALY_DETECTED": proceed to verification

3. If ANOMALY_DETECTED:
   → Show verification prompt: "Are you okay?"
   → Read person's reply through Aditya's ReplyClassifier
   - If I_AM_OK: POST /api/v1/incidents/{incident_id}/verification({response: "I_AM_OK"})
   - Backend owns the resulting incident state

4. Scenario completion:
   - NORMAL: no incident created, scenario can be reset or a new one started
   - TRUE_ANOMALY: verification times out → escalation → incident appears as "ESCALATED"
   - FALSE_ALARM: user confirms "I'm okay" → pending escalation cancelled → incident resolved as "RESOLVED_FALSE_ALARM"
```

---

### 5. Summary Table

| Interface | Constructor | Key Fields/Methods | Status |
|---|---|---|---|
| `HrSample` | `HrSample({required DateTime ts, required int hr})` | `ts: DateTime`, `hr: int` | Proposed |
| `HeartRateSource` | internal | `Stream<HrSample> get samples`, `start()`, `stop()` | Proposed |
| `SimScenario` | `SimScenario.value(String)` | `String identifier` ('NORMAL', 'TRUE_ANOMALY', 'FALSE_ALARM') | Proposed |
| `SimulatorHeartRateSource` | `SimulatorHeartRateSource({Duration sampleInterval = const Duration(seconds: 3)})` | `generateSamples()`, `start()`, `stop()`, `setScenario()` | Proposed |
| `BackendDetectionResult` | `BackendDetectionResult({required bool accepted, required String detectionStatus, String? readingId, ...})` | `fromJson()`, `toJson()` | Proposed |
| `AnomalyEvent` | N/A (received from backend) | `detectedAt`, `kind`, `lastHr`, `firstAbnormalAt`, `durationMs` | Proposed (display-only, fromJson cannot parse POST response directly) |
| `LastMomentsBuffer` | `LastMomentsBuffer({int maxSamples = 60, int maxMs = 30000})` | `add()`, `recent()`, `snapshot()`, `window()`, `reset()` | Proposed |

**No files were directly modified.** This proposal is presented for Aditya's review. He will decide which interfaces to implement and which option to choose for `AnomalyDetector`.

---

### 6. Verification Flow Summary

1. Flutter submits readings through Aditya's API client.
2. Backend returns `detection_status`.
3. Flutter displays the verification prompt when appropriate.
4. User selects `I_AM_OK`.
5. Aditya's API client submits the approved verification action.
6. Backend owns the resulting incident state.