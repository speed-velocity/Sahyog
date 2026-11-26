# Individual Handoff - Prasiddh (Proposed Updates for Review)

**Owner:** Prasiddh  
**Role:** Role 1 - AI/ML and Health Monitoring  
**Branch:** `Ai/ml-and-monitoring`  
**Last updated:** 2026-11-27 (proposed updates)  
**Task ID:** Role 1 — PostgreSQL test update, documentation preparation and Dart contract design  

## Proposed Status Updates

The following status changes are proposed for review by Utkarsh:

- **Flutter/backend three-scenario E2E:** Changed from `NOT INTEGRATED` to `PENDING` — awaiting Aditya's Flutter project and Dart contract approval before full E2E integration testing can commence.
- **Backend baseline:** Updated reference from previous commits to `fea72cb` (latest confirmed baseline).
- **Python detector/backend integration:** Status confirmed `APPROVED and SIGNED OFF` by Shubhankar — no further detector logic changes required.
- **PostgreSQL validation:** Updated to reflect that migration downgrade/re-upgrade round-trip and runtime privileges have been applied; integration tests pass.
- **Altered-payload idempotency:** Added documentation noting this is fixed by backend; reusing an ingestion key with a different payload returns HTTP 409; exact duplicate submissions replay the original result.
- **LastMomentsBuffer evidence:** Added clarification that evidence remains transient in memory; no database migration is required for this demo.
- **Incident status vocabulary:** Proposed updating to use exact canonical statuses: `PENDING_VERIFICATION`, `ESCALATION_IN_PROGRESS`, `ESCALATED`, `RESOLVED_FALSE_ALARM`, `RESOLVED`.
- **ANOMALY_DETECTED boundary:** Proposed explicit separation of `ANOMALY_DETECTED` as a reading-level detection status, not an incident lifecycle status.

## Proposed Documentation Changes

### Incident Lifecycle Statuses

The following incident lifecycle statuses are confirmed backend-owned and should be reflected across all components:

| Status | Description |
|---|---|
| `PENDING_VERIFICATION` | Person has been asked to confirm their condition; verification is pending. |
| `ESCALATION_IN_PROGRESS` | Verification timeout has expired and escalation is being processed. |
| `ESCALATED` | No response was received within the verification window; escalation initiated. |
| `RESOLVED_FALSE_ALARM` | Person confirmed they are okay (`I_AM_OK`), pending escalation was cancelled, incident resolved as false alarm. |
| `RESOLVED` | Incident reached its approved terminal state. |

**Important distinction:** `ANOMALY_DETECTED` is a reading-level detection status, not an incident lifecycle status. An anomaly event triggers the incident workflow, but the final incident state is determined by the verification and escalation flow, not by detection alone.

### Backend Authority Confirmation

- Backend owns authoritative anomaly detection, incident creation, escalation and persistence.
- Flutter submits readings and consumes backend results — must not independently decide whether an anomaly occurred.
- No `NOT_OK` backend status exists; `notOk` is frontend-only for classification purposes.
- Verification action `I_AM_OK` is the only approved positive backend action for confirming a person is safe.

### Latest Team Confirmations (as of 2026-11-27)

1. **Python detector/backend integration:** APPROVED and SIGNED OFF — Shubhankar.
2. **PostgreSQL validation:** Passed — migration downgrade/re-upgrade round-trip and runtime privileges applied — Utkarsh.
3. **Altered-payload idempotency:** Fixed by backend — different payload with reused key returns HTTP 409 — Shubhankar.
4. **Exact duplicate submissions:** Replay the original result — Shubhankar.
5. **LastMomentsBuffer evidence:** Transient in memory; no database migration required — Utkarsh.
6. **Full Flutter/backend three-scenario E2E:** Still pending — Aditya.

### Next Actions (Proposed)

1. Utkarsh reviews proposed updates for `docs/detector_integration_contract.md` and `handoff/prasiddh.md`.
2. Aditya reviews and approves Dart interface contract (Phase 4).
3. Once Flutter project is ready, run full three-scenario E2E tests.
4. Mark Flutter/backend E2E as `INTEGRATED` after all three scenarios pass with the same pipeline.
5. Commit and push all approved changes.

**No tracked files were modified.** All proposed updates are in separate files for review.