# SAHYOG Detector Integration Contract — Proposed Updates for Utkarsh Review

**Purpose:** This document proposes updates to the detector integration contract based on latest team confirmations. It is not a direct edit of `docs/detector_integration_contract.md`. Utkarsh will review and apply changes.

---

## Latest Backend Baseline and Integration Status

- **Latest backend baseline:** `fea72cb`.
- **Python detector/backend integration:** APPROVED and SIGNED OFF by Shubhankar.
- **Detector logic:** No changes required — the rule-based detector is finalized and tested (118 unit tests passing).
- **PostgreSQL validation:** Passed according to latest team confirmation (migration downgrade/re-upgrade round-trip and runtime privileges applied).
- **Altered-payload idempotency:** Fixed by backend; reusing an ingestion key with a different payload now returns HTTP 409; exact duplicate submissions replay the original result.
- **LastMomentsBuffer evidence:** Remains transient in memory; no database migration is required. The bounded rolling buffer (60 samples / 30,000 ms default) is in-memory only with `reset()` clearing samples and rejection count.
- **Backend `POST /api/v1/readings` response schema:** Confirmed fields are `reading_id`, `demo_run_id`, `accepted`, `detection_status`, `anomaly_event_id`, `incident_id`. No local anomaly decisions are made from the response.

## Incident Status Vocabulary

The following incident lifecycle statuses are correct and backend-owned:

| Status | Meaning |
|---|---|
| `PENDING_VERIFICATION` | Person has been asked to confirm their condition; verification is in progress. |
| `ESCALATION_IN_PROGRESS` | Verification timeout has expired and escalation is being processed. |
| `ESCALATED` | No response was received within the verification window; escalation initiated. |
| `RESOLVED_FALSE_ALARM` | Person confirmed they are okay (`I_AM_OK`), pending escalation was cancelled, incident resolved as false alarm. |
| `RESOLVED` | Incident reached its approved terminal state. |

**Important:** `ANOMALY_DETECTED` is a reading-level detection status, **not** an incident lifecycle status. An anomaly detected by the backend does not automatically mean a confirmed emergency escalation has occurred.

## Ownership and Authority

- **Backend owns authoritative anomaly detection, incident creation, escalation and persistence.** The Python backend detector is the authoritative decision-maker for incident-creating anomaly events.
- **Flutter submits readings and consumes backend results.** Flutter must not independently decide whether an anomaly occurred or what the incident outcome should be.
- **No `NOT_OK` backend status exists.** The frontend may classify `notOk` locally for its own purposes, but it has no approved backend status equivalent.
- **Verification action `I_AM_OK`** is the only approved positive backend action for confirming a person is safe. Silence is a backend verification timeout, not a classifier result.
- **Reading-level status vs incident lifecycle:** `ANOMALY_DETECTED` in the reading response triggers the verification workflow, but the final incident state is determined by the verification and escalation flow, not by detection alone.

## Evidence and Buffer

- **LastMomentsBuffer evidence remains transient in memory.** No persistence layer, ORM model, or migration should be created for it.
- The bounded rolling buffer (60 samples / 30,000 ms default) rejects duplicates and out-of-order timestamps, normalizes to UTC, and provides `recent(limit)`, `window(start, end)`, and `snapshot()` retrieval.
- **One buffer belongs to one backend lifecycle context.** The backend must create a new buffer or call `reset()` when the subject/demo-run/generation changes.
- Detector evidence (abnormal-episode samples) is event-scoped and bounded (32 samples max for backend shape). It is not a durable telemetry table and must not be persisted via ORM or migration.

## Detection Status vs Incident Lifecycle

| Surface | Values | Owner/status |
|---|---|---|
| Reading response `detection_status` | `NORMAL`, `ANOMALY_DETECTED` | TEAM-CONFIRMED; backend response contract |
| Detector `detector_result` | `HR_SPIKE`, `HR_DROP` | TEAM-CONFIRMED; detector-result vocabulary |
| Incident lifecycle | `PENDING_VERIFICATION`, `ESCALATION_IN_PROGRESS`, `ESCALATED`, `RESOLVED_FALSE_ALARM`, `RESOLVED` | Backend-owned; exact persistence/API mapping with Shubhankar |
| Dashboard statuses | `NORMAL`, `MONITORING`, `ANOMALY_DETECTED`, `VERIFICATION_PENDING`, `FALSE_ALARM_RESOLVED`, `ESCALATED`, `RESOLVED`, plus run labels `RUNNING`/`COMPLETED` | Actual implementation; backend/API confirmation still required |

`ANOMALY_DETECTED` in the reading response is not by itself proof of a persisted incident status. `NORMAL` means no anomaly indicated; it is not an incident resolution. Do not collapse detection, verification, and escalation into one field.

## Backend-Python Detector Boundary

- The backend Python anomaly service is authoritative for incident-creating anomaly decisions.
- The detector must not generate or accept authoritative values for backend-owned fields: `subject_user_id`, `demo_run_id`, `run_generation`, `reading_id`, `anomaly_event_id`, `incident_id`, `received_at`.
- The backend loads/locks the active demo run, validates generation, and persists the generation snapshot. Mobile/reading endpoint must not supply `run_generation`.
- Detection status values: `NORMAL`, `ANOMALY_DETECTED`, distinct from incident lifecycle.
- Backend normalizes UTC; frontend must preserve classifier behavior.

## Proposed Changes Summary for Utkarsh

1. Update incident status vocabulary to include `PENDING_VERIFICATION`, `ESCALATION_IN_PROGRESS`, `ESCALATED`, `RESOLVED_FALSE_ALARM`, `RESOLVED`.
2. Explicitly separate `ANOMALY_DETECTED` (reading-level) from incident lifecycle statuses.
3. Document that altered-payload idempotency is fixed by backend (HTTP 409 for different payload with reused key).
4. Document that LastMomentsBuffer evidence remains transient in memory; no database migration required.
5. Confirm Flutter submits readings and consumes backend results — no independent anomaly decision.
6. Note that full Flutter/backend three-scenario E2E is still pending.
7. Backend baseline: `fea72cb`; Python detector integration: APPROVED and SIGNED OFF.

**Confirmed:** `POST /api/v1/readings` response fields: `reading_id`, `demo_run_id`, `accepted`, `detection_status`, `anomaly_event_id`, `incident_id`. No local anomaly decisions.

**No files were directly modified.** This proposal is presented for Utkarsh's review. He will decide which changes to apply to `docs/detector_integration_contract.md` and `handoff/prasiddh.md`.