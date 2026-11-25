# SAHYOG Cross-Component Integration Gaps

**Project:** SAHYOG - Detect. Verify. Respond.
**Document:** `docs/integration_gaps.md`
**Owner of this inspection:** Prasiddh (Role 1)
**Date:** 2026-11-25
**Status:** Read-only integration comparison; no dashboard, backend route, model,
migration, Flutter, or location file was modified.

> The dashboard branch is not merged into this working branch. The findings below
> come from safely fetching and reading `origin/Dashboard-and-location`; no
> checkout, merge, cherry-pick, or file copy was performed.

## 1. Inspection basis

- Working branch: `Ai/ml-and-monitoring`.
- Working HEAD at inspection: `1cdf0ee821319b4ac814051535754282c201ea7b`.
- Dashboard remote: `origin/Dashboard-and-location`.
- Fetch updated the remote-tracking ref from `ee5baed` to
  `c3afb2407eb3d0d6f8fab0a987200d923582c80f`
  (`feat: complete dashboard and location modules`).
- Dashboard files inspected read-only: `dashboard/src/api/types.ts`,
  `dashboard/src/api/dashboard.ts`, `dashboard/src/api/config.ts`,
  `dashboard/src/lib/status.ts`, `backend/app/api/location.py`,
  `backend/app/services/location.py`, `handoff/vaishnavi.md`, and the dashboard
  fixtures/components relevant to incident evidence.
- This working branch has no backend application, backend reading route,
  database layer, or merged dashboard. The Role 1 unit tests use namespace
  imports only.
- `origin/backend` at `7de901b` now contains a FastAPI application, auth,
  reading route, persistence service, and detector adapter. Its
  `get_detector()` still raises HTTP 503 because no provider is registered.
- The inspected backend adapter defines Pydantic `DetectorReading`,
  single-result `DetectorResult`, and backend-owned `canonical_dedupe_key()`.
  Role 1 added `backend/app/services/detector_backend_contract.py` as the
  matching facade; it does not modify backend-owned files.

## 2. High-priority gaps

| ID | Component and exact path | Actual state | Required state / missing contract | Impact | Owner |
|---|---|---|---|---|---|
| G1 | `handoff/vaishnavi.md` | Claims HEAD `ee5baed` and that dashboard/location changes are uncommitted. Actual remote HEAD is `c3afb24` and the listed files are in the remote commit. | Handoff must be reconciled with the actual branch and commit. | Reviewers may test the wrong revision or believe work is uncommitted. | Vaishnavi |
| G2 | Dashboard API client, `dashboard/src/api/dashboard.ts` | Calls `/dashboard/overview`, `/incidents?limit=25`, `/incidents/{incident_id}`, `/hospitals/nearby`, and `/location/latest`. | No dashboard or incident backend routes exist on the inspected dashboard branch; only location routes exist. `backend/app/main.py` is absent. | Dashboard can only run against mocks; end-to-end flow is blocked. | Shubhankar |
| G3 | Backend router, `backend/app/api/location.py` and `backend/app/main.py` | Location router exists with prefix `/api/v1`; it is not mounted anywhere on the branch. | Mount `backend.app.api.location.router` once, under the approved application router, with auth and CORS. | Location and hospital calls are unreachable; duplicate prefix risk if mounted incorrectly. | Shubhankar |
| G4 | Dashboard base URL, `dashboard/src/api/config.ts` | Default `http://localhost:8000/api/v1`; dashboard paths are relative. | Backend must serve the dashboard routes under `/api/v1`; CORS origin and environment configuration must be approved. | Local dashboard requests will fail until backend/CORS configuration matches. | Shubhankar + Vaishnavi |
| G5 | Dashboard location type, `dashboard/src/api/types.ts` vs `backend/app/services/location.py` | Backend response includes `location_snapshot_id` and `demo_run_id`; dashboard `LocationSnapshot` does not declare either field. | Confirm whether the dashboard needs the snapshot ID/run ID and align the response type or explicitly allow extra fields. | Extra response fields are untyped; incident/run traceability is lost in the UI. | Vaishnavi |
| G6 | Location lookup, `dashboard/src/api/dashboard.ts` | Dashboard fetches latest location only by `subject_user_id`. | Backend supports either `subject_user_id` or `incident_id`; decide whether incident-scoped location must be surfaced in incident detail. | Incident-specific location may be unavailable even when present. | Vaishnavi + Shubhankar |
| G7 | Location security, `backend/app/api/location.py` | Accepts subject/incident identifiers; no authentication or ownership check is implemented. | Authorise the caller and validate that the subject/incident is within the caller's scope. | Potential location-data exposure; must not be used as production-ready. | Shubhankar |
| G8 | Location durability, `backend/app/services/location.py` | In-memory, thread-safe, bounded store; resets on restart; no database model. | Confirm whether persistence is required for the prototype; Utkarsh owns any migration. | Location disappears on restart and is not multi-process safe. | Utkarsh + Vaishnavi |
| G9 | Hospital provider, `backend/app/services/location.py` | Seeded fictional Pune hospital directory with an explicit disclaimer. | Replace or confirm the boundary with Utkarsh's approved shared provider; do not present seed data as availability. | Integration may use a different provider shape; disclaimer must remain visible. | Utkarsh + Vaishnavi |
| G10 | Incident detail evidence, `dashboard/src/api/types.ts` | `IncidentDetail.evidence` is typed as `AnomalyEvent[]`; detector output is `DetectedAnomaly` with event and bounded sample evidence. | Backend must map/aggregate detector evidence into the dashboard shape; no backend schema exists. | Dashboard cannot render detector evidence consistently without a backend mapping. | Shubhankar + Prasiddh |
| G11 | `dashboard/package.json`, `dashboard/README.md` | Package metadata uses React 18.3, ReactDOM 18.3, Vite 6.1, Vitest 3.0, TypeScript 5.7, jsdom, and Testing Library. No dashboard README exists at the branch/dashboard root and there is no lint script or ESLint dependency. | Add/confirm dashboard setup documentation and decide whether linting is required in CI. | Onboarding and lint consistency; not a runtime blocker. | Vaishnavi |

## 3. Status-vocabulary comparison

The actual dashboard file `dashboard/src/lib/status.ts` uses these keyed labels:

```text
NORMAL
MONITORING
ANOMALY_DETECTED
VERIFICATION_PENDING
FALSE_ALARM_RESOLVED
ESCALATED
RESOLVED
RUNNING
COMPLETED
```

The file comments call the first group backend lifecycle values and explicitly
render unknown values verbatim rather than renaming them. The earlier proposed
dashboard aliases (`DETECTED`, `PENDING_VERIFICATION`, `ACKNOWLEDGED`,
`CONFIRMED_EMERGENCY`, `FALSE_ALARM`) are **not present** in the actual file.

| Question | Current evidence | Status |
|---|---|---|
| Does the dashboard use the documented backend lifecycle strings? | Core labels match `ANOMALY_DETECTED`, `VERIFICATION_PENDING`, `FALSE_ALARM_RESOLVED`, `ESCALATED`, and `RESOLVED`. | Likely aligned for these labels; still requires Shubhankar confirmation. |
| Is `MONITORING` a persisted incident status or a display-only monitoring summary? | Present as a dashboard status label; no backend model/API inspected confirms it. | **UNRESOLVED**; do not persist or transition on it. |
| Are `RUNNING` and `COMPLETED` incident states? | They describe demo-run progress, not the incident lifecycle. | Display-only unless backend owners approve otherwise. |
| Is `NORMAL` an incident status? | Present as no-anomaly dashboard label; the reading response also uses `NORMAL` as `detection_status`. | **UNRESOLVED** semantics; keep reading detection status distinct from incident lifecycle. |
| Does `FALSE_ALARM_RESOLVED` replace `FALSE_ALARM`? | Only `FALSE_ALARM_RESOLVED` is in the actual status map. | Do not create a `FALSE_ALARM` incident status. |
| Is `ACKNOWLEDGED` or `CONFIRMED_EMERGENCY` implemented? | No occurrence in the actual status map. | Do not implement unapproved transitions. |

The status map also maps severity keys `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
That display vocabulary matches the approved severity vocabulary, but it does not
approve a severity-assignment policy. The detector still emits `severity=None`.

## 4. Dashboard/API contract gaps

### 4.1 Routes expected by the dashboard

From `dashboard/src/api/dashboard.ts` and the `/api/v1` base:

| Route | Purpose | Backend status |
|---|---|---|
| `GET /api/v1/dashboard/overview` | Monitoring summary, latest/recent readings, active incidents | **MISSING** |
| `GET /api/v1/incidents?limit=25` | Incident list | **MISSING** |
| `GET /api/v1/incidents/{incident_id}` | Incident detail, verification, escalation, evidence, timeline | **MISSING** |
| `GET /api/v1/hospitals/nearby?latitude=...&longitude=...&limit=...` | Nearby hospitals | **IMPLEMENTED only in location branch** |
| `GET /api/v1/location/latest?subject_user_id=...` | Latest subject location | **IMPLEMENTED only in location branch** |
| `POST /api/v1/location/updates` | Location ingestion | **IMPLEMENTED only in location branch**; not called by dashboard client |

No backend `main.py` or router registration exists on the inspected branch, so
even the implemented location routes are not reachable under a running app.

### 4.2 Field-shape gaps

| Field/type | Dashboard expectation | Backend/current source | Gap |
|---|---|---|---|
| Subject identifier | `SubjectSummary.user_id` | ORM uses `subject_user_id` | Confirm API naming and mapping; do not rename either side independently. |
| Anomaly event | `AnomalyEvent` with `anomaly_event_id`, `detected_at`, `detector_result`, optional severity/explanation/version | ORM has additional subject/demo/run/dedupe fields; no API schema exists | Backend response shape must be defined; dashboard does not need every ORM field. |
| Evidence | `IncidentDetail.evidence: AnomalyEvent[]` | Detector evidence is per-event bounded sample data | Backend must decide whether to expose event summaries, sample evidence, or both. |
| Verification | Optional `status`, `pending`, `deadline_at`, `responses[]` | No verification API implemented | Dashboard cannot verify until Shubhankar's API exists. |
| Escalation | Attempts with notification records | No escalation API implemented | Same blocker. |
| Location snapshot | Coordinates, capture/receipt times, staleness, optional subject/incident | Backend returns snapshot ID, subject/incident/run IDs and the same location fields | Add missing fields to dashboard types or explicitly allow/ignore them. |
| Severity | Optional string; display map supports `LOW`/`MEDIUM`/`HIGH`/`CRITICAL` | Detector emits `None`; ORM column nullable | Display only when backend supplies an approved value; assignment policy unresolved. |
| Confidence | Not present in the actual dashboard types | Detector has no confidence | Earlier confidence requirement is superseded; do not fabricate a value. |
| Detection status | `MonitoringSummary.detection_status` | No overview API implemented; reading response uses `NORMAL`/`ANOMALY_DETECTED` | Backend must populate the overview consistently with the reading response. |

### 4.3 Location-specific gaps

- The dashboard type does not declare `location_snapshot_id` or `demo_run_id`
  even though the backend Pydantic response includes them.
- The dashboard fetches locations only by subject; incident-scoped lookup is not
  wired into the UI.
- Backend location errors use `{"error": {"code", "message"}}` for explicit
  location failures; FastAPI request-validation errors may still use the default
  422 body. The shared error envelope is not fully standardised.
- The location service is bounded in memory; it is not durable, multi-process
  safe, or authenticated.
- The seeded hospital directory is a demonstration fallback with a disclaimer; it
  is not the approved shared hospital abstraction.
- The route is not mounted, so dashboard calls cannot succeed even if the
  dashboard and backend are started together.

## 5. Detector-to-backend gaps

These are cross-component contract gaps, not defects in the core algorithm.

| Gap | Current state | Required decision |
|---|---|---|
| Adapter | No `backend.app.services.detector_adapter` exists | Shubhankar implements `detect(readings) -> DetectorResult` and supplies backend context. |
| Result transport | Role 1 has typed Python dataclasses; no JSON payload is approved | Agree on one result schema, including evidence and counts, before route integration. |
| Dedupe key | Serialization method approved; exact field names/prefix unresolved | Shubhankar/Utkarsh confirm key derivation and unique-scope usage; Role 1 helper returns a raw digest. |
| Severity | Vocabulary approved; policy unresolved | Omit severity until an owner-approved assignment rule exists. |
| Confidence | Not available | Do not add a field or display a fabricated score. |
| Baseline | Explicit at session construction; ownership unresolved | Backend/product must decide who computes and supplies it. |
| Session lifecycle | One stateful session per context proposed; no backend map exists | Backend must scope sessions by subject/run/generation and handle resets safely. |
| Evidence durability | Transient bounded evidence; no ORM field/table approved | Utkarsh decides whether any migration is needed; Role 1 must not add one. |
| Reading response | `NORMAL`/`ANOMALY_DETECTED` confirmed; exact response body/serialization not frozen | Shubhankar confirms initial and anomaly response payloads. |

See `docs/detector_integration_contract.md` for the Role 1 boundary and status.

## 6. Verification and escalation gaps

- The dashboard can display `verification.responses[].response_value`; it maps
  the exact value `I_AM_OK` to the label "I'm okay".
- No `NOT_OK` backend value or transition is approved. `notOk` is frontend-only;
  the dashboard must not invent a status for it.
- No verification endpoint, timeout worker, escalation attempt model, or
  notification record API is present on the inspected branches.
- The dashboard's `EscalationAttempt` and `NotificationAttempt` types are
  provisional until Shubhankar supplies the backend schema.
- Do not implement `ACKNOWLEDGED` or `CONFIRMED_EMERGENCY` transitions merely to
  fill the UI; the actual status map does not contain them.

## 7. Test and build evidence

| Item | Claimed/observed | Status |
|---|---|---|
| Dashboard tests | Handoff claims 19 mocked tests passed | Not rerun by Role 1; actual remote HEAD differs from handoff metadata |
| Dashboard typecheck/build | Handoff claims passed | Not rerun by Role 1 |
| Location backend tests | Handoff claims 17 tests plus Ruff clean | Not rerun by Role 1; no backend application environment here |
| Backend/dashboard end-to-end | No runnable backend app or dashboard/incident APIs | **BLOCKED** |
| Flutter/Android | No Flutter project or SDK used in this inspection | Not verified |

Role 1's own unit tests and compile checks are recorded in
`handoff/prasiddh.md`. They do not verify any dashboard or backend integration.

## 8. Required sequence to close gaps

1. Vaishnavi reconciles the stale handoff metadata with the committed dashboard
   branch and confirms the actual test revision.
2. Shubhankar adds the backend application/router, dashboard overview and
   incident APIs, auth/ownership checks, and the detector adapter.
3. Shubhankar and Vaishnavi align the dashboard read contract with the backend
   response schemas, including location snapshot fields, subject identifier
   naming, evidence shape, and incident status semantics.
4. Shubhankar and Utkarsh confirm dedupe-key representation, severity policy,
   baseline ownership, and whether evidence/location persistence is required.
5. Run the dashboard against the real backend for normal, true-anomaly,
   false-alarm, repeated-run, stale-data, unauthorised, and location tests.
6. Only then update status from `NOT INTEGRATED` to `INTEGRATED`. No integration
   test has passed yet.

**End of `docs/integration_gaps.md`.**
