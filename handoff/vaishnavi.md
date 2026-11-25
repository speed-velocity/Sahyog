# Individual Handoff — Vaishnavi

**Owner:** Vaishnavi  
**Role:** Role 2 — Caregiver Dashboard and Location  
**Last updated:** 2026-11-25  
**Branch:** `Dashboard-and-location`  
**HEAD:** `ee5baed` (changes below are uncommitted)

## 1. Task IDs
- D5.1–D5.12 (dashboard and location phase).
- Location service/API and mobile location contract work required by Role 2 ownership.

## 2. Status
- Dashboard: `IMPLEMENTED`, `TESTED` against mocked backend contracts (19 tests, typecheck, production build).
- Backend location service/API: `IMPLEMENTED`, `TESTED` (17 tests, ruff check/format clean).
- Mobile core location module: `IMPLEMENTED`, `TESTED` in an isolated Dart harness (12 tests) plus `dart analyze`; Flutter/Android runtime integration remains untested.
- Real backend/dashboard/mobile integration: `BLOCKED` on missing backend application code (`backend/app/main.py`, dashboard/incident APIs, auth) owned by Shubhankar.

## 3. Summary
Implemented the complete caregiver dashboard, a bounded backend location service with a clearly labelled seeded hospital fallback, and a framework-independent mobile location module. The dashboard never creates incidents or fabricates state; it renders backend-authoritative data and explicitly labels simulation. The location API validates inputs, computes staleness, bounds memory, and exposes dashboard-compatible location and nearby-hospital responses. The mobile module handles permission/service failures, stale locations, and bounded reporting through interfaces that Aditya can wire into the Flutter app. Its pure-Dart logic was analyzed and exercised in an isolated harness, including a real local HTTP round trip.

## 4. Required Behaviour Implemented
- Dashboard views: overview, monitoring, incidents, location.
- Monitored-person status, latest and recent readings, heart-rate chart, reading table.
- Anomaly evidence, verification state, escalation state, incident timeline.
- False-alarm resolution and escalated-incident display using exact backend status vocabulary.
- Unknown statuses displayed verbatim; no client-side incident state decisions.
- Controlled polling (10 s default), pause while hidden, abort in-flight requests, no overlap.
- Explicit loading, empty, stale, unavailable, permission-independent, and error states.
- Dedicated authentication-expired state for HTTP 401/403 that never fabricates data.
- Dashboard never discovers location independently.
- Location snapshot ingestion, retrieval by subject or incident, staleness computation.
- Bounded in-memory location storage (512 latest subject/incident entries).
- Seeded, fictional Pune hospital fallback with source label and no availability/acceptance claim.
- Mobile permission failure handling, stale rejection, coordinate validation, and bounded reporting.

## 5. Files Changed
Dashboard:
- `dashboard/package.json`
- `dashboard/package-lock.json`
- `dashboard/.env.example`
- `dashboard/.gitignore`
- `dashboard/index.html`
- `dashboard/tsconfig.json`
- `dashboard/vite.config.ts`
- `dashboard/src/App.tsx`
- `dashboard/src/main.tsx`
- `dashboard/src/vite-env.d.ts`
- `dashboard/src/api/client.ts`
- `dashboard/src/api/config.ts`
- `dashboard/src/api/dashboard.ts`
- `dashboard/src/api/types.ts`
- `dashboard/src/components/EmptyState.tsx`
- `dashboard/src/components/ErrorState.tsx`
- `dashboard/src/components/EscalationPanel.tsx`
- `dashboard/src/components/HeartRateChart.tsx`
- `dashboard/src/components/Icon.tsx`
- `dashboard/src/components/IncidentDetailPanel.tsx`
- `dashboard/src/components/IncidentList.tsx`
- `dashboard/src/components/LatestReadingCard.tsx`
- `dashboard/src/components/LoadingSkeleton.tsx`
- `dashboard/src/components/LocationCard.tsx`
- `dashboard/src/components/NearbyHospitals.tsx`
- `dashboard/src/components/PageHeader.tsx`
- `dashboard/src/components/PersonCard.tsx`
- `dashboard/src/components/ReadingTable.tsx`
- `dashboard/src/components/SectionCard.tsx`
- `dashboard/src/components/Sidebar.tsx`
- `dashboard/src/components/SimulatedNotice.tsx`
- `dashboard/src/components/StatCard.tsx`
- `dashboard/src/components/StatusBadge.tsx`
- `dashboard/src/components/Timeline.tsx`
- `dashboard/src/components/Topbar.tsx`
- `dashboard/src/components/VerificationPanel.tsx`
- `dashboard/src/hooks/useDashboardData.ts`
- `dashboard/src/hooks/usePollingResource.ts`
- `dashboard/src/lib/format.ts`
- `dashboard/src/lib/readings.ts`
- `dashboard/src/lib/status.ts`
- `dashboard/src/styles/global.css`
- `dashboard/src/views/IncidentsView.tsx`
- `dashboard/src/views/LocationView.tsx`
- `dashboard/src/views/MonitoringView.tsx`
- `dashboard/src/views/OverviewView.tsx`
- `dashboard/src/test/client.test.ts`
- `dashboard/src/test/dashboard.test.tsx`
- `dashboard/src/test/fixtures.ts`
- `dashboard/src/test/mockApi.ts`
- `dashboard/src/test/setup.ts`

Backend:
- `backend/app/services/location.py`
- `backend/app/api/location.py`
- `backend/tests/conftest.py`
- `backend/tests/test_location_service.py`
- `backend/tests/test_location_api.py`

Mobile:
- `mobile/lib/core/location/location.dart`
- `mobile/lib/core/location/location_models.dart`
- `mobile/lib/core/location/location_provider.dart`
- `mobile/lib/core/location/location_service.dart`
- `mobile/lib/core/location/location_reporter.dart`
- `mobile/lib/core/location/http_location_update_sender.dart`
- `mobile/lib/core/location/simulated_location_provider.dart`

This handoff:
- `handoff/vaishnavi.md`

## 6. Interfaces Consumed
- Proposed dashboard read contract: `GET /api/v1/dashboard/overview`, `GET /api/v1/incidents?limit=25`, `GET /api/v1/incidents/{incident_id}`.
- Location read contract: `GET /api/v1/location/latest?subject_user_id=...` or `?incident_id=...` (404 means no snapshot).
- Hospital read contract: `GET /api/v1/hospitals/nearby?latitude=...&longitude=...&limit=...`.
- Exact status vocabulary from `SYSTEM_DESIGN.md`.
- Database field naming conventions from `origin/Software-integration-and-database` models.
- No backend dashboard/incident API implementation exists on this branch, so those shapes remain proposals pending Shubhankar approval.

## 7. Interfaces Exposed
- `POST /api/v1/location/updates` — accepts an authorised location snapshot; returns the snapshot.
- `GET /api/v1/location/latest` — returns the latest snapshot by subject or incident; 404 when unavailable.
- `GET /api/v1/hospitals/nearby` — bounded seeded-directory results with provider, disclaimer, distance, and timestamp.
- Backend `LocationService`, `LocationUpdateRequest`, `LocationSnapshot`, `NearbyHospitalsResponse`, `HospitalDirectory`.
- Dashboard API types in `dashboard/src/api/types.ts` (proposal in absence of Shubhankar's schemas).
- Mobile `LocationProvider`, `SimulatedLocationProvider`, `LocationService`, `LocationReporter`, `LocationUpdateSender`, `HttpLocationUpdateSender`.
- Location and hospital errors use `{"error":{"code","message"}}` for 400/404/422/503 responses.

## 8. Commands Executed
```powershell
npm install --no-audit --no-fund
npm test
npm run typecheck
npm run build
python -m venv C:\Users\VAISHN~1\AppData\Local\Temp\opencode\sahyog-location-venv
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\sahyog-location-venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet "fastapi>=0.115,<1.0" "httpx>=0.27,<1.0" "pytest>=8,<10" "ruff>=0.8,<0.18"
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\sahyog-location-venv\Scripts\python.exe" -m pytest backend/tests -q
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\sahyog-location-venv\Scripts\python.exe" -m pytest tests -q   # from backend/, CI-equivalent
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\sahyog-location-venv\Scripts\python.exe" -m ruff check backend/app/services/location.py backend/app/api/location.py backend/tests
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\sahyog-location-venv\Scripts\python.exe" -m ruff format --check backend/app/services/location.py backend/app/api/location.py backend/tests
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\dart-sdk\dart-sdk\bin\dart.exe" format --output=none --set-exit-if-changed mobile/lib/core/location
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\dart-sdk\dart-sdk\bin\dart.exe" analyze mobile/lib/core/location
& "C:\Users\VAISHN~1\AppData\Local\Temp\opencode\dart-sdk\dart-sdk\bin\dart.exe" test --reporter=expanded   # from isolated temp harness
```

## 9. Tests Executed and Results
- `npm test`: **19 passed**, 2 files. Includes NORMAL, TRUE_ANOMALY, FALSE_ALARM, verification-pending, unknown status, empty readings, stale reading, 401 authentication-expired, API error/recovery, location/hospital present, location/hospital missing, hospital-directory error, and repeated-demo refresh.
- `npm run typecheck`: **passed**.
- `npm run build`: **passed**; Vite 6.4.6, 61 modules, dist assets generated.
- `pytest backend/tests -q` / `pytest tests -q` from `backend/`: **17 passed**, 1 dependency deprecation warning.
- `ruff check`: **passed** (import sorting fixed in `backend/app/api/location.py` and `backend/tests/`).
- `ruff format --check`: **passed**.
- Backend tests used an isolated temporary Python 3.13 virtual environment and FastAPI `TestClient`.
- `dart analyze mobile/lib/core/location`: **no issues**.
- `dart format`: 4 files formatted; subsequent format check passed.
- Isolated Dart harness: **12 tests passed** (permission outcomes, stale/invalid input rejection, source labelling, reporter payload, HTTP success, HTTP error envelope, parser validation).
- Flutter widget/Android tests were **not run**; only the pure-Dart module was verified.

## 10. Build Results
- Dashboard production build succeeded.
- No runnable backend application exists on this branch, so no backend build/start check was possible.
- Dart analysis succeeded for the mobile module; no Flutter/Android build was possible without Flutter.

## 11. Known Limitations
- No real dashboard/incident backend implementation or `backend/app/main.py` exists; dashboard contract types are provisional and end-to-end integration is not verified.
- Location data is in-memory only and resets on backend restart; it is bounded but not durable or multi-process safe.
- Authentication/authorisation is not implemented; the location route accepts identifiers and must be protected by Shubhankar's approved auth layer.
- The seeded hospital directory is a local fallback, not Utkarsh's approved shared hospital abstraction.
- FastAPI request-validation errors use the default 422 body; only explicit location/hospital errors use the SAHYOG error envelope.
- Dashboard tests use mocked API responses in jsdom, not the real backend or a browser.
- The dashboard consumes canonical `GET /api/v1/dashboard/overview` and `GET /api/v1/incidents` routes that are documented but not implemented anywhere in the repository yet; until Shubhankar provides them the UI can only run against mocks.
- The location router exists but is not mounted because `backend/app/main.py` does not exist on this branch.
- Mobile logic passed a temporary Dart test harness, but those tests are not committed because `mobile/test/` and `pubspec.yaml` are outside this role's owned paths.
- The mobile module has no Android permission-plugin integration and has not run on a device/emulator.
- No map URL generation was added; the design does not require external map tiles or geocoding.

## 12. Blockers / Decisions Required
- **Shubhankar:** implement/approve dashboard overview and incident APIs, authentication, router registration in `backend/app/main.py`, shared error handling, and the dashboard CORS origin.
- **Shubhankar:** approve the location routes and include `backend.app.api.location.router` without adding a second `/api/v1` prefix.
- **Utkarsh:** confirm the shared hospital abstraction integration point and whether location snapshots require persistence.
- **Aditya:** integrate the mobile location provider/reporter into the Flutter app and provide the actual permission implementation.
- **Utkarsh:** review and merge only after cross-component contracts are approved.

## 13. Next Actions
1. Review and commit the owned implementation on `Dashboard-and-location` when explicitly approved.
2. Align dashboard types with Shubhankar's final response schemas and integrate against a running backend.
3. Replace the seeded hospital provider boundary with Utkarsh's approved abstraction.
4. Wire Aditya's Flutter permission provider to `mobile/lib/core/location/`, move the verified harness cases into `mobile/test/core/location/`, and run Flutter analysis/widget tests.
5. Run the three end-to-end scenarios and repeated-run stability checks.

## 14. Dependencies on Teammates
- Shubhankar: backend APIs, auth, error envelope, main router.
- Utkarsh: hospital abstraction, integration, CI, merge.
- Aditya: Flutter integration and Android runtime verification.
- Prasiddh: anomaly/reading display contract for incident detail evidence.

## 15. Integration Checklist
- [ ] `backend/app/main.py` includes the location router once.
- [ ] Dashboard CORS origin is allowed by the backend.
- [ ] Dashboard points `VITE_API_BASE_URL` at a running backend.
- [ ] Location writes are authorised and incident/subject ownership is validated.
- [ ] Hospital results come through the approved shared abstraction.
- [ ] Mobile permission denial/disabled-service paths are exercised on Android.
- [ ] Dashboard normal, escalated, and false-alarm scenarios verified against real APIs.
- [ ] Shared error envelope finalised.
- [ ] Repeated-run stability verified.

## 16. Contract Notes
- Location request fields: `subject_user_id`, optional `incident_id`/`demo_run_id`, `latitude`, `longitude`, optional `accuracy_meters`, `captured_at` (timezone-aware), `source_kind`.
- Location response fields: snapshot ID, subject/incident/run IDs, coordinates, accuracy, capture/receipt times, source, `is_stale`, `stale_after_seconds`.
- Hospital response fields: `hospitals[]`, `provider`, `disclaimer`, `generated_at`; each hospital has ID, name, address, coordinates, `distance_meters`, `source_kind`.
- Simulated location source must be sent as `SIMULATED`; seeded hospital source as `SEEDED_DEMO`.
- No field was renamed in an existing backend schema; no database model was modified.

## 17. Security and Privacy Notes
- No secrets are embedded in dashboard or mobile code.
- Location data is not logged.
- Hospital data is explicitly fictional/demo and does not claim availability or acceptance.
- The backend must add authenticated ownership checks before production/integration use.

## 18. Environment Notes
- Node `v24.15.0`, npm `11.12.1`.
- Python `3.13.7`; integration branch declares Python `<3.13`, so backend tests used an isolated temporary venv.
- Dart SDK `3.13.7` was used from a temporary directory for analysis/tests; Flutter is not installed.
- `uv` is not installed.
- Generated `__pycache__`, `.pytest_cache`, and `.ruff_cache` directories were removed after testing.

## 19. Commit
- Commit ID: **not created** (no commit was requested in this session).
- Branch remains `Dashboard-and-location`.
- Uncommitted docs intentionally excluded from any future commit: `Agents.md`, `HandOff.md`, `PRD.md`, `SYSTEM_DESIGN.md`, `TEAM.md`.
- Ready for Utkarsh/Shubhankar review before commit or integration.
