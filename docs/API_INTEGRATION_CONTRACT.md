# SAHYOG — API Integration Contract (Dashboard ↔ Backend ↔ Mobile)

**Status:** `CONFIRMED & FROZEN` (All core architectural decisions resolved; Phase 1–3 backend capabilities active)  
**Scope:** Reconciles the implemented FastAPI backend (`backend/app/`) with the React caregiver dashboard (`dashboard/src/`), mobile client location integration, and PostgreSQL database schema.  
**Rule:** Everything labeled **`IMPLEMENTED (MOUNTED)`** describes code verified as active and routed in the backend application. Everything labeled **`PLANNED / PENDING BACKEND IMPLEMENTATION`** describes an approved design that is not yet implemented in backend code and must not be called until implemented. Unmounted or non-existent endpoints are never presented as available.

---

> [!IMPORTANT]
> ### Confirmed Architectural Decisions & Integration Directives
> 1. **Dashboard Authentication:** Caregiver dashboard authentication is confirmed to use `POST /api/v1/auth/token` (OAuth2 form URL-encoded body `username` and `password`). The client must store the returned JWT and supply `Authorization: Bearer <access_token>` on all requests to protected backend routes.
> 2. **Backend Response Schemas Are Authoritative (Flat Models):** Dashboard integration must adapt to the existing flat backend response models. The backend will **not** implement nested query wrappers or fabricated collections.
>    - `GET /api/v1/dashboard/overview` returns the flat `DashboardOverview` model.
>    - `GET /api/v1/incidents` and `GET /api/v1/incidents/{incident_id}` return the flat 9-scalar `IncidentResponse` model.
> 3. **Caregiver Subject Discovery (`GET /api/v1/authorizations/me` & `GET /api/v1/authorizations`):** Fully **`IMPLEMENTED (MOUNTED)`** and tested. Caregivers discover assigned subjects via `GET /api/v1/authorizations/me` (returning `AuthorizedSubjectsResponse`) or `GET /api/v1/authorizations` (returning `list[AuthorizationResponse]`). Both caregivers and subjects can also query their active grants via `GET /api/v1/authorizations`.
> 4. **Dual Error Conventions Preserved by Design:**
>    - Location and hospital routes return: `{"error": {"code": "...", "message": "..."}}`.
>    - Core backend and FastAPI routes return: `{"detail": "..."}`.
>    Both conventions are intentionally preserved for their respective domains.
> 5. **Canonical Enums Confirmed:**
>    - Incident statuses: `PENDING_VERIFICATION`, `ESCALATION_IN_PROGRESS`, `ESCALATED`, `RESOLVED_FALSE_ALARM`, `RESOLVED`.
>    - Verification action: `I_AM_OK`.
>    - Notification result statuses: `ACCEPTED`, `DELIVERED`, `FAILED`, `UNKNOWN`.
> 6. **CORS Middleware Active:** `backend/app/main.py` has `CORSMiddleware` mounted with allowed origins `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, and `http://127.0.0.1:5173`.

---

## 1. Authentication and Authorization

### 1.1 Implemented & Mounted Endpoints (`backend/app/api/auth.py`)

- **Register (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/auth/register` (unauthenticated)
  - Request (`RegisterRequest`, `extra="forbid"`):
    ```json
    {
      "login_identifier": "caregiver-demo-1",
      "password": "at-least-12-characters",
      "role": "CAREGIVER"
    }
    ```
  - Allowed `UserRole` values: `"SUBJECT"` | `"CAREGIVER"`. Minimum login identifier length: 3. Minimum password length: 12.
  - Response (`201 Created`, `RegisterResponse`): `{ "user_id": "<uuid>", "role": "CAREGIVER" }`.
  - Error: `409 Conflict` when `login_identifier` already exists.
- **Login / Token (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/auth/token` (unauthenticated)
  - Request (`OAuth2PasswordRequestForm`, `application/x-www-form-urlencoded`): `username` (maps to `AuthIdentity.login_identifier`) and `password`.
  - Response (`200 OK`, `TokenResponse`):
    ```json
    {
      "access_token": "<jwt>",
      "token_type": "bearer"
    }
    ```
  - Error: `401 Unauthorized` (`WWW-Authenticate: Bearer`) when unknown identifier, wrong password, or `AuthIdentity.disabled == True`.

### 1.2 JWT Bearer-Token Specification (`backend/app/core/auth.py`)

- Algorithm: `HS256` signed with `SAHYOG_AUTH_SECRET_KEY` (minimum 32 characters).
- Required claims in payload:
  - `sub`: UUID string (`AuthIdentity.user_id`)
  - `role`: `"SUBJECT"` | `"CAREGIVER"`
  - `iss`: `SAHYOG_AUTH_ISSUER` (default `"sahyog-backend"`)
  - `iat`: UTC issued-at timestamp
  - `exp`: UTC expiration timestamp (`iat + SAHYOG_ACCESS_TOKEN_EXPIRE_MINUTES`, default 30 minutes)
  - `jti`: UUID4 string (stateless unique identifier)
- **Dashboard Client Authentication Flow (Confirmed Decision):**
  1. The user logs in via the dashboard UI.
  2. The dashboard calls `POST /api/v1/auth/token` with credentials via form URL-encoding.
  3. The returned `access_token` is stored in client memory.
  4. All subsequent HTTP calls in `dashboard/src/api/client.ts` include the header:
     ```http
     Authorization: Bearer <access_token>
     ```
  5. On receiving a `401 Unauthorized` response, the dashboard clears the token and redirects to the login screen.

### 1.3 Protected Route Scoping & Role Enforcement

- `require_active_principal` validates the JWT signature, expiry, and verifies `AuthIdentity.disabled == False`.
- `can_access_subject(session, principal, subject_user_id)` enforces:
  - If `principal.user_id == subject_user_id`: allowed immediately.
  - If `principal.role == UserRole.CAREGIVER`: allowed only if an active delegation exists in `caregiver_authorizations` (`subject_user_id == requested_subject`, `caregiver_user_id == principal.user_id`, `revoked_at IS NULL`).
  - Otherwise denied (`403 Forbidden`).
- Route-level role enforcement:
  - `POST /api/v1/demo/runs` requires `UserRole.SUBJECT`.
  - `POST /api/v1/demo/runs/{id}/reset` requires `UserRole.SUBJECT`.
  - `POST /api/v1/authorizations` requires `UserRole.SUBJECT`.
  - `DELETE /api/v1/authorizations/{id}` requires `UserRole.SUBJECT`.
  - `POST /api/v1/incidents/{id}/verification` requires `UserRole.SUBJECT` and `principal.user_id == incident.subject_user_id`.
  - `POST /api/v1/location/updates` requires `UserRole.SUBJECT` and subject ownership of update, demo run, and incident.
  - `GET /api/v1/location/latest` requires `can_access_subject`.
  - `GET /api/v1/hospitals/nearby` requires `require_active_principal`.
  - `POST /api/v1/readings` verifies `DemoRun.subject_user_id == principal.user_id`.

### 1.4 Caregiver Subject Discovery (`IMPLEMENTED (MOUNTED)`)

- **Current State:** Caregiver discovery is fully implemented, mounted in `backend/app/api/authorizations.py`, and verified by unit and contract test suites (`test_authorization.py`, `test_authorizations_api.py`).
- **Caregiver Self Discovery Endpoint:**
  - Method & Path: `GET /api/v1/authorizations/me`
  - Auth: `require_active_principal` + `UserRole.CAREGIVER` (`403 Only caregivers may list authorized subjects`)
  - Response (`200 OK`, `AuthorizedSubjectsResponse`):
    ```json
    {
      "authorized_subjects": [
        {
          "subject_user_id": "a1b2c3d4-1111-4111-8111-111111111111",
          "granted_at": "2026-11-26T12:00:00Z",
          "revoked_at": null
        }
      ]
    }
    ```
- **Active Authorizations Listing Endpoint:**
  - Method & Path: `GET /api/v1/authorizations`
  - Parameters: `limit: int = Query(default=100, ge=1, le=100)`
  - Auth: `require_active_principal`
  - Response (`200 OK`, `list[AuthorizationResponse]`):
    - For `CAREGIVER`: lists active records where `caregiver_user_id == principal.user_id` and `revoked_at IS NULL`.
    - For `SUBJECT`: lists active records where `subject_user_id == principal.user_id` and `revoked_at IS NULL`.
- **Client Integration Rule:** Caregivers should query `GET /api/v1/authorizations/me` upon login to discover authorized subjects, then populate subject selection or pass `?subject_user_id=<uuid>` to overview and incident endpoints.

---

## 2. Platform Health Check

### 2.1 Service Health (`IMPLEMENTED (MOUNTED)` in `backend/app/api/health.py`)

- **Endpoint:** `GET /health` (unauthenticated)
- **Response (`200 OK`, `HealthResponse`):**
  ```json
  {
    "status": "ok",
    "service": "sahyog-backend"
  }
  ```

---

## 3. Caregiver Authorizations API

### 3.1 Implemented & Mounted Endpoints (`backend/app/api/authorizations.py`)

- **List My Authorized Subjects (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/authorizations/me`
  - Auth: `require_active_principal` + `UserRole.CAREGIVER` (`403 Only caregivers may list authorized subjects`).
  - Response (`200 OK`, `AuthorizedSubjectsResponse`): returns list of subjects delegated to the caregiver.
- **List Active Authorizations (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/authorizations`
  - Auth: `require_active_principal` (available to both subjects and caregivers).
  - Query Parameters: `limit: int = 100` (`ge=1, le=100`).
  - Response (`200 OK`, `list[AuthorizationResponse]`):
    ```json
    [
      {
        "authorization_id": "c1d2e3f4-3333-4333-8333-333333333333",
        "subject_user_id": "a1b2c3d4-1111-4111-8111-111111111111",
        "caregiver_user_id": "b1c2d3e4-2222-4222-8222-222222222222",
        "granted_at": "2026-11-26T12:00:00Z",
        "revoked_at": null
      }
    ]
    ```
  - Errors: `422 Unprocessable Entity` if limit is invalid.
- **Grant Access (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/authorizations`
  - Auth: `require_active_principal` + `UserRole.SUBJECT` (`403 Only subjects may manage access`).
  - Request (`AuthorizationCreateRequest`, `extra="forbid"`):
    ```json
    {
      "caregiver_user_id": "b1c2d3e4-2222-4222-8222-222222222222"
    }
    ```
  - Response (`201 Created`, `AuthorizationResponse`):
    ```json
    {
      "authorization_id": "c1d2e3f4-3333-4333-8333-333333333333",
      "subject_user_id": "a1b2c3d4-1111-4111-8111-111111111111",
      "caregiver_user_id": "b1c2d3e4-2222-4222-8222-222222222222",
      "granted_at": "2026-11-26T12:00:00Z",
      "revoked_at": null
    }
    ```
  - Errors: `400 Bad Request` if caregiver user does not exist, has role other than `CAREGIVER`, or matches subject ID.
- **Revoke Access (`IMPLEMENTED (MOUNTED)`):** `DELETE /api/v1/authorizations/{authorization_id}`
  - Auth: `require_active_principal` + `UserRole.SUBJECT` (`403 Only subjects may manage access`).
  - Response (`200 OK`, `AuthorizationResponse`): returns updated record with `revoked_at` populated.
  - Errors: `404 Not Found` if authorization does not exist or does not belong to subject.

---

## 4. Demo Run Management APIs

### 4.1 Implemented & Mounted Endpoints (`backend/app/api/demo.py`)

- **Start Demo Run (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/demo/runs`
  - Auth: `require_active_principal` + `UserRole.SUBJECT` (`403 Only subjects may start demos`).
  - Request (`DemoRunCreateRequest`, `extra="forbid"`):
    ```json
    {
      "scenario": "TRUE_ANOMALY",
      "start_idempotency_key": "run-demo-key-001"
    }
    ```
    - Allowed `scenario` values: `"NORMAL"` | `"TRUE_ANOMALY"` | `"FALSE_ALARM"`.
  - Response (`201 Created`, `DemoRunResponse`):
    ```json
    {
      "demo_run_id": "c3d4e5f6-3333-4333-8333-333333333333",
      "subject_user_id": "a1b2c3d4-1111-4111-8111-111111111111",
      "scenario": "TRUE_ANOMALY",
      "status": "RUNNING",
      "outcome": null,
      "current_generation": 1,
      "started_at": "2026-11-26T12:00:00Z",
      "completed_at": null,
      "reset_at": null
    }
    ```
- **Get Demo Run (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/demo/runs/{demo_run_id}`
  - Auth: `require_active_principal` + `can_access_subject` (`403 Demo access denied`, `404 Demo run not found`).
  - Response (`200 OK`, `DemoRunResponse`).
- **Reset Demo Run (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/demo/runs/{demo_run_id}/reset`
  - Auth: `require_active_principal` + `UserRole.SUBJECT` (`403 Only subjects may reset demos`).
  - Increments `current_generation`, sets `reset_at = utc_now()`, and transitions status to `RESET`.
  - Response (`200 OK`, `DemoRunResponse`).
  - Errors: `404 Not Found` if demo run does not exist or does not belong to subject.

---

## 5. Health Reading Ingestion & Anomaly Triggering

### 5.1 Implemented & Mounted Endpoint (`backend/app/api/readings.py`)

- **Ingest Reading (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/readings`
  - Auth: `require_active_principal` (authenticates principal; verifies `DemoRun.subject_user_id == principal.user_id`).
  - Request (`ReadingRequest`, `extra="forbid"`):
    ```json
    {
      "demo_run_id": "c3d4e5f6-3333-4333-8333-333333333333",
      "source_kind": "SIMULATED",
      "heart_rate_bpm": 142,
      "observed_at": "2026-11-26T12:01:00Z",
      "activity_context": "RESTING",
      "source_record_id": "rec-001",
      "ingestion_idempotency_key": "idemp-reading-001"
    }
    ```
  - Validation rules:
    - `source_kind` must equal `"SIMULATED"` (`422 Only SIMULATED readings are supported`).
    - `observed_at` must include timezone info (`422 observed_at must include a timezone`).
    - **BPM Range Validation:** `heart_rate_bpm` must be between `20` and `250` inclusive (`422 heart_rate_bpm must be between 20 and 250`). Checked before detector execution.
    - `demo_run_id` must match an active run owned by `principal.user_id` (`404 demo run was not found`).
  - **Idempotency & Replay Semantics:**
    - The backend looks up any existing reading under `(subject_user_id, ingestion_idempotency_key)`.
    - **Exact Replay:** If an existing reading matches all payload fields (`demo_run_id`, `source_kind`, `heart_rate_bpm`, `observed_at`, `activity_context`, `source_record_id`), the stateful detector is **not** called again (`result = None`). The existing `HealthReading` and its associated `AnomalyEvent` are preserved and returned.
    - **Altered Payload Conflict:** If the same key is reused with differing fields, the request is rejected with **`409 Conflict`** (`"ingestion_idempotency_key was already used with a different reading"`).
  - **Monotonic Observation Timestamp Validation:**
    - For new readings in the same subject/demo run, `observed_at` must be strictly later than the latest recorded reading.
    - If `observed_at <= latest.observed_at`, returns **`422 Unprocessable Entity`** (`"observed_at must be later than the latest reading"`).
    - Exact duplicate replays bypass this monotonic check and succeed even if newer readings have arrived.
  - Behavior:
    - Invokes the detector for the subject's active run and generation.
    - Persists reading to `health_readings`.
    - If anomaly detected, creates an `anomaly_events` row and opens an `Incident` in `PENDING_VERIFICATION` with deadline `utc_now() + verification_timeout_seconds` (default 15s) and idempotency key `f"anomaly:{event.dedupe_key}"`.
  - Response (`202 Accepted`, `ReadingResponse`):
    ```json
    {
      "reading_id": "d1e2f3a4-4444-4444-8444-444444444444",
      "demo_run_id": "c3d4e5f6-3333-4333-8333-333333333333",
      "accepted": true,
      "detection_status": "ANOMALY_DETECTED",
      "anomaly_event_id": "e1f2a3b4-5555-4555-8555-555555555555",
      "incident_id": "f1a2b3c4-6666-4666-8666-666666666666"
    }
    ```
  - Errors:
    - `404 Not Found`: Demo run not found for principal.
    - `409 Conflict`: Altered idempotency key payload, stale generation, or reading prior to demo start/reset.
    - `422 Unprocessable Entity`: Validation failure (out-of-range BPM, non-monotonic timestamp, missing timezone, non-SIMULATED source).
    - `503 Service Unavailable`: Authoritative detector unavailable.

---

## 6. Dashboard Overview (`GET /api/v1/dashboard/overview`)

### 6.1 Canonical Endpoint & Query Parameters (`backend/app/api/dashboard.py`)

- **Endpoint (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/dashboard/overview`
- **Auth:** `require_active_principal` + `can_access_subject` (`403 Dashboard access denied`).
- **Query parameters:** `subject_user_id: UUID | None = None` (optional for subjects; required for caregivers).

### 6.2 Confirmed Authoritative Schema (`DashboardOverview`)

Per confirmed architectural decision, dashboard integration uses the existing flat backend model. No nested wrapper schema is provided by the backend.

**Authoritative Response (`IMPLEMENTED (MOUNTED)` in `backend/app/schemas/dashboard.py`):**
```json
{
  "subject_user_id": "a1b2c3d4-1111-4111-8111-111111111111",
  "monitoring_status": "NORMAL",
  "latest_reading": {
    "reading_id": "11111111-1111-4111-8111-111111111111",
    "heart_rate_bpm": 78,
    "observed_at": "2026-11-26T01:50:00Z",
    "source_kind": "SIMULATED"
  },
  "active_incident": null,
  "incident_status": null,
  "latest_update_at": "2026-11-26T01:50:01Z"
}
```

### 6.3 Dashboard Frontend Field Consumption Mapping

The React caregiver dashboard views must adapt directly to this flat structure:

| Backend Field | Type / Nullable | Description / Dashboard Usage |
|---|---|---|
| `subject_user_id` | `UUID` | ID of the monitored subject displayed in headers and subject badge. |
| `monitoring_status` | `str` | Overall subject state (`"NORMAL"`, `"IN_INCIDENT"`, `"NO_DATA"`). |
| `latest_reading` | `ReadingItem \| null` | Latest sample: contains `reading_id`, `heart_rate_bpm`, `observed_at`, and `source_kind`. Populates heart rate card. |
| `active_incident` | `UUID \| null` | UUID of the currently open incident, if any (`null` when no incident is active). |
| `incident_status` | `str \| null` | Canonical status string (e.g., `"PENDING_VERIFICATION"`, `"ESCALATED"`). |
| `latest_update_at` | `datetime` | Timestamp of the most recent reading or state transition. |

*Note for Dashboard Developers:* Historical reading charts and full incident logs are populated by polling `GET /api/v1/incidents?subject_user_id=<uuid>` and `GET /api/v1/location/latest?subject_user_id=<uuid>`. Do not expect nested collections inside `/dashboard/overview`.

---

## 7. Incident APIs

### 7.1 Implemented & Mounted Endpoints (`backend/app/api/incidents.py`)

- **List Incidents (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/incidents`
  - Query params: `subject_user_id: UUID | None = None`, `status_filter: str | None = None`, `limit: int = 50` (`1..100`).
  - Auth: `require_active_principal` + `can_access_subject`.
  - Returns `list[IncidentResponse]`.
- **Get Incident (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/incidents/{incident_id}`
  - Auth: `require_active_principal` + `can_access_subject`.
  - Returns `IncidentResponse`.
- **Submit Incident Verification (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/incidents/{incident_id}/verification`
  - Auth: `require_active_principal` + `UserRole.SUBJECT` + `principal.user_id == incident.subject_user_id` (`403 Only the monitored subject may verify`).
  - Request (`VerificationResponse`, `extra="forbid"`):
    ```json
    {
      "response": "I_AM_OK",
      "idempotency_key": "verif-idemp-001",
      "request_reference": "ref-001"
    }
    ```
  - Allowed `response` action: `"I_AM_OK"` (confirmed canonical verification action).
  - Behavior: Records response in `verification_responses`. Transitions incident to `RESOLVED_FALSE_ALARM`.
  - Errors: `409 Conflict` if verification deadline passed (`VerificationExpired`) or not awaiting verification (`IncidentNotAwaitingVerification`).
  - Returns `IncidentResponse`.

### 7.2 Authoritative `IncidentResponse` Schema (Confirmed Decision)

Per confirmed architectural decision, `IncidentResponse` consists of the 9 scalar fields below. The backend will **not** fabricate or return nested timeline, evidence, or notification attempt collections.

**Authoritative Response (`IMPLEMENTED (MOUNTED)` in `backend/app/schemas/api.py`):**
```json
{
  "incident_id": "f1a2b3c4-6666-4666-8666-666666666666",
  "subject_user_id": "a1b2c3d4-1111-4111-8111-111111111111",
  "demo_run_id": "c3d4e5f6-3333-4333-8333-333333333333",
  "run_generation": 1,
  "status": "PENDING_VERIFICATION",
  "created_at": "2026-11-26T12:01:05Z",
  "updated_at": "2026-11-26T12:01:05Z",
  "verification_deadline_at": "2026-11-26T12:01:35Z",
  "resolved_at": null
}
```

---

## 8. Location and Nearby Hospitals

### 8.1 Endpoints & Routing Status (`backend/app/api/location.py`)

> [!NOTE]
> All location and hospital routes are **`IMPLEMENTED (MOUNTED)`** in production. The router defines its own `prefix="/api/v1"` in `backend/app/api/location.py` and is mounted directly in `backend/app/main.py` via `app.include_router(location_router)`. It is deliberately kept outside `backend/app/api/v1.py` so the `/api/v1` prefix is not duplicated (avoiding `/api/v1/api/v1/...`). Do not mount it through `v1.py`.

- **Submit Location Update (`IMPLEMENTED (MOUNTED)`):** `POST /api/v1/location/updates`
  - Auth: `require_active_principal` + `_validate_update_scope`.
    - Only `UserRole.SUBJECT` may submit their own location (`principal.user_id == update.subject_user_id`); otherwise returns `403 LOCATION_ACCESS_DENIED`.
    - If `demo_run_id` is supplied, verifies it belongs to the authenticated subject (`403 LOCATION_ACCESS_DENIED`).
    - If `incident_id` is supplied, verifies it belongs to the authenticated subject (`403 LOCATION_ACCESS_DENIED`).
  - Request (`LocationUpdateRequest`, `extra="forbid"`):
    ```json
    {
      "subject_user_id": "a1b2c3d4-1111-4111-8111-111111111111",
      "incident_id": "f1a2b3c4-6666-4666-8666-666666666666",
      "demo_run_id": "c3d4e5f6-3333-4333-8333-333333333333",
      "latitude": 18.5204,
      "longitude": 73.8567,
      "accuracy_meters": 12.0,
      "captured_at": "2026-11-26T12:00:30Z",
      "source_kind": "SIMULATED"
    }
    ```
  - Validation: rejects timestamps skewed > 120s into the future with `422 INVALID_LOCATION_TIMESTAMP`.
  - Response (`201 Created`, `LocationSnapshot`).
- **Get Latest Location (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/location/latest`
  - Auth: `require_active_principal` + `can_access_subject`.
    - When querying by `subject_user_id`: verified via `can_access_subject` (`403 LOCATION_ACCESS_DENIED`).
    - When querying by `incident_id`: verifies incident exists and `can_access_subject(session, principal, incident.subject_user_id)` (`403 LOCATION_ACCESS_DENIED`).
  - Query parameters: exactly one of `subject_user_id: UUID` or `incident_id: UUID` (fails with `400 LOCATION_QUERY_INVALID` if neither or both provided).
  - Returns `404 LOCATION_NOT_AVAILABLE` if no snapshot exists.
  - Returns `200 OK` (`LocationSnapshot`) with `"is_stale": true` if age > 300 seconds (`stale_after_seconds: 300`).
- **Get Nearby Hospitals (`IMPLEMENTED (MOUNTED)`):** `GET /api/v1/hospitals/nearby`
  - Auth: `require_active_principal` (authenticated principal required).
  - Query parameters: `latitude: float (-90..90)`, `longitude: float (-180..180)`, `limit: int (1..10, default 5)`.
  - Response (`200 OK`, `NearbyHospitalsResponse`):
    ```json
    {
      "hospitals": [
        {
          "hospital_id": "88888888-8888-4888-8888-888888888888",
          "name": "Sahyog Demo Central Hospital",
          "address": "Demo directory entry, central Pune",
          "latitude": 18.5167,
          "longitude": 73.874,
          "distance_meters": 1872.4,
          "source_kind": "SEEDED_DEMO"
        }
      ],
      "provider": "SEEDED_DEMO_DIRECTORY",
      "disclaimer": "Seeded demonstration hospital data only. No hospital has been contacted, is confirmed available, or has accepted an incident.",
      "generated_at": "2026-11-26T12:00:00Z"
    }
    ```

### 8.2 Location Persistence & Hospital Package Architecture

- **Database Schema (`IMPLEMENTED`):**
  - Table **`location_snapshots`** is created by Alembic migration `25c1af2fe01c_add_location_snapshots.py`.
  - ORM model `LocationSnapshotRecord` is defined in `backend/app/models/location.py`.
  - Composite foreign keys reference `users`, `demo_runs`, and `incidents`.
  - Table permissions for `sahyog_app` are restricted to `SELECT, INSERT` (append-only; no update or delete).
- **Service Layer (`IMPLEMENTED IN-MEMORY ONLY`):**
  - `LocationService` in `backend/app/services/location.py` currently maintains bounded in-memory maps (`_by_subject` and `_by_incident`, capped at 512 entries).
  - Data is lost on server restart and not shared across processes.
  - End-to-end PostgreSQL location persistence is deferred to a follow-up task.
- **Hospital Package Extraction (`IMPLEMENTED`):**
  - `backend/app/services/hospital/` is fully extracted and active (`protocol.py`, `seeded.py`, `service.py`, `__init__.py`).
  - Pre-seeded Pune directory entries (`SeededHospitalDirectory`) include Sahyog Demo Central Hospital, Pune Cantonment General Hospital, Deccan Emergency Care, Shivajinagar Specialty Clinic, and Kothrud Community Hospital.
  - `LocationService` delegates hospital lookups directly to `HospitalServiceProtocol`. Distance calculation uses the Haversine formula.

---

## 9. Escalation Worker & Notification Mechanics

### 9.1 Escalation Worker Lifecycle & Configuration (`IMPLEMENTED (ACTIVE)`)

- **Lifespan Management (`backend/app/main.py`):**
  - `run_timeout_worker()` from `backend/app/workers/timeout.py` is managed inside FastAPI's `asynccontextmanager` application lifespan.
  - At most one background task is created per application instance.
  - Clean shutdown: signaled via `asyncio.Event` (`stop_event.set()`) and awaited before application termination.
  - If `settings.timeout_worker_enabled` is `False`, no background task is created and startup proceeds normally.
- **Worker Configuration (`backend/app/core/config.py` & `backend/.env.example`):**
  - `SAHYOG_TIMEOUT_WORKER_ENABLED`: boolean, default `true`.
  - `SAHYOG_TIMEOUT_WORKER_INTERVAL_SECONDS`: float, default `1.0` (enforced floor `max(0.1, interval_seconds)`).
  - `SAHYOG_TIMEOUT_WORKER_BATCH_SIZE`: integer, default `50` (bounded to `max(1, min(batch_limit, 100))`).
- **Database Escalation Flow:**
  - Timeout worker polls expired incidents where `verification_deadline_at <= now` and status is `PENDING_VERIFICATION`.
  - It creates an `EscalationAttempt` row (`status="IN_PROGRESS"`) committed to PostgreSQL *before* invoking the escalation notifier. External I/O is never executed while a database transaction is open.
  - Upon notifier completion, it calls `complete_escalation` to record final attempt status (`ACCEPTED` or `FAILED`) and transitions the incident to `ESCALATED`.

### 9.2 Notifier Package & Simulated-Delivery Semantics (`IMPLEMENTED`)

- **Package Structure (`backend/app/services/notifier/`):**
  - `protocol.py`: Defines `EscalationNotifier` Protocol and `NotificationResult` dataclass.
  - `mock.py`: Defines `MockEscalationNotifier`.
  - `__init__.py`: Exports `EscalationNotifier`, `MockEscalationNotifier`, `NotificationResult`, and `get_demo_notifier()`.
- **In-Memory Simulated Delivery:**
  - `MockEscalationNotifier` records simulated escalation notifications in a thread-safe, bounded in-memory `OrderedDict` (`max_records=256`).
  - Idempotent: Reusing the same `idempotency_key` returns the previously generated `NotificationResult` with status `ACCEPTED`.
  - **Notification attempts are NOT stored in the database.**
  - Performs no external SMS, telephony, or emergency services dispatch.

---

## 10. Database Schema, Migrations, and Runtime Privileges

### 10.1 Alembic Migration Sequence (`backend/migrations/versions/`)

1. `2f4d5b1a8c77_add_auth_identity_and_caregiver_authorization.py`: Foundation schema (users, auth, authorizations, demo runs, readings, anomalies, incidents, verification, escalations, timeline).
2. `25c1af2fe01c_add_location_snapshots.py`: Adds `location_snapshots` table with foreign keys, bounds checks, and index. Exactly one Alembic head exists.

### 10.2 Complete Database Table Inventory (12 Tables)

| Table Name | Purpose / Ownership | Access Mode (`sahyog_app`) |
|---|---|---|
| `users` | Subject and caregiver identity records | `SELECT, INSERT, UPDATE, DELETE` |
| `auth_identities` | Password hashes and login state | `SELECT, INSERT, UPDATE, DELETE` |
| `caregiver_authorizations` | Caregiver-to-subject access delegations | `SELECT, INSERT, UPDATE, DELETE` |
| `demo_runs` | Demonstration execution lifecycle | `SELECT, INSERT, UPDATE, DELETE` |
| `health_readings` | High-frequency simulated sensor samples | **`SELECT, INSERT` (Append-only)** |
| `anomaly_events` | Detector-identified sustained anomaly episodes | **`SELECT, INSERT` (Append-only)** |
| `incidents` | Core emergency response incident tracking | `SELECT, INSERT, UPDATE, DELETE` |
| `incident_anomaly_events` | Evidence linkage between incidents and anomalies | `SELECT, INSERT, UPDATE, DELETE` |
| `verification_responses` | Subject interactive verification responses | **`SELECT, INSERT` (Append-only)** |
| `escalation_attempts` | Worker escalation attempts per incident | `SELECT, INSERT, UPDATE, DELETE` |
| `incident_timeline_events` | Audit timeline of state changes | **`SELECT, INSERT` (Append-only)** |
| `location_snapshots` | GPS coordinate breadcrumbs | **`SELECT, INSERT` (Append-only)** |

### 10.3 Incident Constraint Clarification

- Composite unique constraint **`uq_incidents_id_subject`** on `(incident_id, subject_user_id)` exists in `incidents` to support composite foreign key references from `location_snapshots`. Exactly one instance of this constraint is defined.

---

## 11. CORS Configuration (`IMPLEMENTED (MOUNTED)`)

`CORSMiddleware` is configured in `backend/app/main.py`:
- **Allowed Origins:** Parsed from `settings.cors_allowed_origins` (comma-separated, whitespace trimmed, empty entries omitted).
  - Default: `http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173`.
  - Configurable via `SAHYOG_CORS_ALLOWED_ORIGINS` in `.env`.
- **Preflight & Header Behavior:**
  - `allow_credentials = True`
  - `allow_methods = ["*"]`
  - `allow_headers = ["*"]`
- If `cors_allowed_origins` parses to an empty list, the middleware is not added.

---

## 12. Error Response Conventions (Confirmed Decision)

Both error response shapes are intentionally preserved by design according to domain ownership:

### 12.1 Location Domain (`/api/v1/location/*`, `/api/v1/hospitals/*`)
Uses the location domain error envelope:
```json
{
  "error": {
    "code": "LOCATION_ACCESS_DENIED",
    "message": "Only subjects may submit location updates."
  }
}
```
Standard codes: `LOCATION_ACCESS_DENIED` (403), `LOCATION_QUERY_INVALID` (400), `LOCATION_NOT_AVAILABLE` (404), `INVALID_LOCATION_TIMESTAMP` (422), `DIRECTORY_UNAVAILABLE` (503).

### 12.2 General Core Backend Routes
All other endpoints (`/auth/*`, `/demo/*`, `/readings`, `/incidents/*`, `/dashboard/*`, `/health`) use standard FastAPI error envelopes:
```json
{
  "detail": "observed_at must be later than the latest reading"
}
```
Clients must inspect responses according to the target endpoint domain.

---

## 13. Canonical Enums & Vocabulary (Confirmed Decision)

### 13.1 Incident Status (`IncidentStatus` in `backend/app/schemas/incidents.py`)

| Canonical Backend Enum (`IMPLEMENTED`) | Dashboard Value (`dashboard/src/lib/status.ts`) | Confirmed Status |
|---|---|---|
| `PENDING_VERIFICATION` | `VERIFICATION_PENDING` | **Confirmed Canonical:** Dashboard must adopt `PENDING_VERIFICATION` as primary enum key; alias `VERIFICATION_PENDING` in display metadata only. |
| `ESCALATION_IN_PROGRESS` | *(absent)* | **Confirmed Canonical:** Dashboard adds `ESCALATION_IN_PROGRESS` to `STATUS_META`. |
| `ESCALATED` | `ESCALATED` | **Matches.** |
| `RESOLVED_FALSE_ALARM` | `FALSE_ALARM_RESOLVED` | **Confirmed Canonical:** Dashboard adopts `RESOLVED_FALSE_ALARM`. |
| `RESOLVED` | `RESOLVED` | **Matches.** |

### 13.2 Verification Action

- Canonical action: **`I_AM_OK`** (only allowed payload action for `POST /api/v1/incidents/{incident_id}/verification`).

### 13.3 Notification Result Status (`NotificationResultStatus` in `backend/app/schemas/incidents.py`)

| Canonical Backend Enum (`IMPLEMENTED`) | Dashboard Usage (`dashboard/src/lib/status.ts`) | Confirmed Status |
|---|---|---|
| `ACCEPTED` | `SENT` / `SIMULATED` | **Confirmed Canonical:** Backend emits `ACCEPTED` for mock deliveries. Dashboard maps `ACCEPTED` to display as "Accepted / Simulated". |
| `DELIVERED` | *(absent)* | **Confirmed Canonical:** Reserved for verified delivery; never emitted by simulated notifier. |
| `FAILED` | `FAILED` | **Matches.** |
| `UNKNOWN` | *(absent)* | **Confirmed Canonical:** Fallback status. |

---

## 14. Remaining Team Action Items

1. **Dashboard Client Authentication (`dashboard/src/api/client.ts` — Vaishnavi):**
   - **`COMPLETED`:** Connected login UI to `POST /api/v1/auth/token`.
   - **`COMPLETED`:** Form-urlencoded token request with client-side credential storage and `Authorization: Bearer <access_token>` attached to all protected API calls.
2. **Dashboard Adaptation to Flat Backend Schemas (Vaishnavi):**
   - **`COMPLETED`:** `dashboard/src/views/OverviewView.tsx` consumes flat `DashboardOverview` fields (`subject_user_id`, `monitoring_status`, `latest_reading`, `active_incident`, `incident_status`, `latest_update_at`).
   - **`COMPLETED`:** `IncidentDetailPanel.tsx` and timeline views consume scalar fields from `IncidentResponse`.
3. **Caregiver Subject Discovery (`GET /api/v1/authorizations/me` & `GET /api/v1/authorizations` — Shubhankar & Vaishnavi):**
   - **`COMPLETED`:** Implemented and mounted endpoints so caregivers can dynamically query authorized subject IDs and subjects can manage delegations.
4. **PostgreSQL-Backed Location Persistence & Read-Through (Vaishnavi & Utkarsh):**
   - **`COMPLETED`:** Implemented `backend/app/services/location_persistence.py` repository.
   - **`COMPLETED`:** Wired `LocationService.prepare_snapshot()` and `LocationService.publish_snapshot()` into `backend/app/api/location.py`.
   - **`COMPLETED`:** Enabled commit-before-cache-publication and database read-through fallback for `/api/v1/location/latest`.
5. **Explicit Role Check on Reading Ingestion (Shubhankar):**
   - **`COMPLETED`:** Reading ingestion restricted to `UserRole.SUBJECT` with demo run ownership checks.

---

## 15. Role Ownership & Implementation Progress

### Role Ownership (per `TEAM.md`)

- **Shubhankar (Backend):**
  - **`INTEGRATED`:** Reading ingestion validation (BPM 20–250, idempotency consistency, monotonic timestamps).
  - **`INTEGRATED`:** Lifespan worker orchestration and CORS middleware.
  - **`INTEGRATED`:** Authoritative flat schemas (`DashboardOverview`, `IncidentResponse`).
  - **`INTEGRATED`:** `GET /api/v1/authorizations` and `GET /api/v1/authorizations/me` caregiver discovery routes.
  - **`INTEGRATED`:** Explicit subject role check on `POST /api/v1/readings`.
- **Vaishnavi (Dashboard & Location):**
  - **`INTEGRATED`:** Location router mounted under `/api/v1` prefix.
  - **`INTEGRATED`:** Location updates, latest location query, and nearby hospital query endpoints.
  - **`INTEGRATED`:** Dashboard JWT authentication flow and bearer token attachment.
  - **`INTEGRATED`:** Complete React caregiver dashboard with 22 vitest tests and clean TypeScript build.
- **Prasiddh (AI/ML & Monitoring):**
  - **`INTEGRATED`:** Anomaly detector adapter, provider, and deduplication.
  - **`INTEGRATED`:** Last-moments buffer and heart rate simulation domain.
  - **`INTEGRATED`:** Python 3.12 UTC datetime alignment.
- **Aditya (Flutter Mobile Frontend):**
  - **`INTEGRATED`:** Flutter mobile project structured in `mobile/`.
  - **`INTEGRATED`:** HTTP location reporter and reading ingestion transport models matching backend response schemas.
  - **`INTEGRATED`:** Simulation heart rate sources and UI state panels.
- **Utkarsh (Role 5 — Integration & Database):**
  - **`INTEGRATED`:** Database foundation for table `location_snapshots` and incident composite unique constraint (`25c1af2fe01c`).
  - **`INTEGRATED`:** Linear Alembic migration chain and downgrade/upgrade round-trip validation.
  - **`INTEGRATED`:** Location persistence repository (`backend/app/services/location_persistence.py`) and API read-through wiring.
  - **`INTEGRATED`:** PostgreSQL integration schema tests, constraint tests, and RESTRICT delete validation.
  - **`INTEGRATED`:** CI resilience update for `setup-uv` network timeout fallback and `integration` pytest marker registration.
  - **`INTEGRATED`:** Complete end-to-end demo workflow verification suite (`test_demo_workflow_e2e.py`) validating all 3 demo scenarios.

---

## 16. Demo Execution and Run Instructions

### 1. Start the Backend API Server
```bash
cd backend
uv sync --locked --group dev --group migrations
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 2. Start the Caregiver Dashboard
```bash
cd dashboard
npm install # or npm ci
npm run dev -- --port 5173
```
Open `http://localhost:5173` in a browser. Log in with caregiver credentials to view authorized subjects, live readings, incident status, and location/hospital panels.

### 3. Run Backend Verification Suite
```bash
cd backend
uv run --locked pytest -m "not integration"
uv run --locked ruff check .
uv run --locked ruff format --check .
```

### 4. Run Dashboard Verification Suite
```bash
cd dashboard
npm test
npm run build
```
