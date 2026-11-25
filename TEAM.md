# SAHYOG — Team Responsibilities and Ownership

**Project:** SAHYOG — Detect. Verify. Respond.  
**Document:** TEAM.md  
**Version:** 1.0  
**Status:** Proposed team baseline

---

## 1. Team Structure

SAHYOG has five primary development roles.

| Role | Team member | Primary responsibility |
|---|---|---|
| Role 1 | Prasiddh | AI/ML and health monitoring |
| Role 2 | Vaishnavi | Caregiver dashboard and location |
| Role 3 | Shubhankar | Backend engineering |
| Role 4 | Aditya | Flutter Android frontend |
| Role 5 | Utkarsh | Software integration and database |

Utkarsh is the integration lead.

Every person owns their assigned implementation and must coordinate shared interfaces with the other owners.

## 2. General Ownership Rules

1. Every file has one primary owner.
2. Do not modify another person's owned files without approval.
3. Do not create a duplicate service because another teammate's service is difficult to consume.
4. Shared interfaces must be agreed before implementation.
5. API changes must be communicated to all affected teammates.
6. Every completed task must be tested.
7. Every task must have a handoff update.
8. All changes must be committed to the correct branch.
9. Utkarsh reviews and merges work into the integration branch.
10. The integration branch must remain runnable.

If ownership is unclear, ask Utkarsh before editing the file.

## 3. Role 1 — Prasiddh: AI/ML and Health Monitoring

### Primary responsibility

Build the simulated health-reading analysis pipeline and anomaly-detection logic.

### Owned paths

- `backend/app/services/anomaly.py`
- `backend/app/api/readings.py`
- `mobile/lib/core/ml/`
- `mobile/lib/core/buffer/`
- `mobile/lib/features/monitoring/domain/`
- `mobile/lib/features/check/domain/`
- `hardware/` only if explicitly required by an approved task.

### Responsibilities

- Define and implement the approved health-sample interface.
- Implement the simulated reading source.
- Validate readings.
- Handle stale and missing readings.
- Implement the anomaly detector.
- Generate structured anomaly results.
- Implement or coordinate the last-moments buffer.
- Implement the approved reply-classification interface.
- Provide deterministic test vectors.
- Ensure the backend detector is authoritative for incident-creating decisions.
- Coordinate reading and anomaly contracts with Shubhankar.
- Coordinate simulator interfaces with Aditya.

### Not responsible for

- Database models and migrations.
- General backend authentication.
- Flutter screen design.
- Caregiver dashboard.
- Hospital discovery.
- Notification provider implementation.
- Real smartwatch connectivity in the current prototype.

### Dependencies

- Shubhankar: reading API and detector integration.
- Aditya: simulator UI and reading-source integration.
- Utkarsh: shared data models and test fixtures.
- Vaishnavi: dashboard display of anomaly information.

## 4. Role 2 — Vaishnavi: Dashboard and Location

### Primary responsibility

Build the caregiver dashboard and location/hospital functionality.

### Owned paths

- `dashboard/`
- `backend/app/services/location.py`
- `backend/app/api/location.py`
- `mobile/lib/core/location/`

### Responsibilities

- Build the dashboard.
- Display monitored-person status.
- Display reading summaries.
- Display anomaly and incident status.
- Display verification and escalation state.
- Display incident timeline.
- Implement approved location handling.
- Handle location permission failures.
- Provide approved nearby-hospital data.
- Support seeded/cached hospital data.
- Integrate the dashboard with backend APIs.
- Ensure false-alarm resolution is reflected correctly.

### Not responsible for

- General backend authentication.
- Database model ownership.
- AI/ML detection.
- Flutter's general navigation and screen structure.
- Notification provider implementation.
- Independent incident-state decisions.

### Dependencies

- Shubhankar: dashboard and incident APIs.
- Utkarsh: database and hospital/notifier abstractions.
- Aditya: mobile location integration.
- Prasiddh: anomaly and health-reading display contract.

## 5. Role 3 — Shubhankar: Backend

### Primary responsibility

Build the backend APIs and application services that connect the mobile application, detector, database and dashboard.

### Owned paths

- `backend/app/main.py`
- `backend/app/api/`, excluding `readings.py` and `location.py`
- `backend/app/core/`
- `backend/app/schemas/`
- Approved backend services for:
  - Authentication.
  - Profiles.
  - Medical information.
  - Emergency contacts.
  - Reminders.
  - Incidents.
  - Verification.
  - Packages.
  - Escalation.
- `backend/app/workers/`

### Responsibilities

- Implement approved API routes.
- Implement request and response schemas.
- Implement authentication and authorization.
- Implement incident lifecycle.
- Implement verification workflow.
- Implement timeout handling.
- Integrate Prasiddh's anomaly service.
- Integrate Utkarsh's database models.
- Integrate notification and hospital abstractions.
- Provide API documentation.
- Handle errors and duplicate requests.
- Keep the server stable under repeated demo runs.

### Not responsible for

- Database model ownership.
- Flutter screens.
- AI/ML detector implementation.
- Dashboard UI.
- Independent location-service implementation.
- Duplicating notifier or hospital services.

### Dependencies

- Prasiddh: reading and anomaly contract.
- Utkarsh: database models, migrations and notifier/hospital abstractions.
- Aditya: mobile API requirements.
- Vaishnavi: dashboard and location integration.

## 6. Role 4 — Aditya: Flutter Android Frontend

### Primary responsibility

Build the Android application and connect the user interface to the shared backend and simulator.

### Owned paths

- `mobile/` except:
  - `mobile/lib/core/ml/`
  - `mobile/lib/core/buffer/`
  - `mobile/lib/features/monitoring/domain/`
  - `mobile/lib/features/check/domain/`
  - `mobile/lib/core/location/`

The excluded paths belong to Prasiddh or Vaishnavi.

### Responsibilities

- Flutter application structure.
- Navigation.
- Main screens.
- Monitoring UI.
- Three Play buttons.
- Scenario progress display.
- Verification UI.
- "I'm okay" action.
- Manual SOS UI if included in the approved design.
- API-client integration.
- Error and loading states.
- Android configuration.
- APK build.
- AAB build.
- Release preparation.

### Not responsible for

- Backend detector.
- Backend database.
- Caregiver dashboard.
- General backend routes.
- Hospital discovery.
- Actual smartwatch connectivity in this prototype.

### Dependencies

- Prasiddh: simulator and health-monitoring interfaces.
- Shubhankar: API contracts.
- Vaishnavi: location interface.
- Utkarsh: app configuration and release integration.

## 7. Role 5 — Utkarsh: Software Integration and Database

### Primary responsibility

Maintain a consistent repository, database, integration process and runnable final product.

### Owned paths

- Repository-level configuration.
- CI and development tooling.
- `backend/app/models/`
- `backend/alembic/`
- `backend/app/services/notifier/`
- `backend/app/services/hospital/`
- `backend/scripts/`
- `docs/`
- `deployment/`

### Responsibilities

- Own database models.
- Own database migrations.
- Coordinate shared contracts.
- Maintain repository configuration.
- Maintain integration branch.
- Review and merge pull requests.
- Build notifier abstraction.
- Build hospital abstraction.
- Maintain documentation.
- Maintain demo-seed and reset scripts.
- Maintain local and deployment configuration.
- Run end-to-end integration tests.
- Verify server stability.
- Coordinate final Android release readiness.

### Not responsible for

- Independently rewriting teammates' application logic.
- Owning the AI/ML detector.
- Owning general backend API implementation.
- Owning Flutter screens.
- Owning dashboard UI.
- Duplicating Vaishnavi's location discovery logic.

### Dependencies

All four teammates.

## 8. Shared File Ownership

| File/path | Primary owner | Contributors |
|---|---|---|
| `PRD.md` | Utkarsh | All |
| `SYSTEM_DESIGN.md` | Utkarsh | All |
| `TEAM.md` | Utkarsh | All |
| `AGENTS.md` | Utkarsh | All |
| `HANDOFF.md` | Utkarsh | All |
| `docs/` | Utkarsh | Approved contributors |
| `backend/app/models/` | Utkarsh | Shubhankar |
| `backend/app/api/readings.py` | Prasiddh | Shubhankar |
| `backend/app/api/location.py` | Vaishnavi | Shubhankar |
| `backend/app/api/` other routes | Shubhankar | Utkarsh |
| `backend/app/services/anomaly.py` | Prasiddh | Shubhankar |
| `backend/app/services/location.py` | Vaishnavi | Utkarsh |
| `backend/app/services/notifier/` | Utkarsh | Shubhankar |
| `backend/app/services/hospital/` | Utkarsh | Vaishnavi |
| `mobile/lib/core/ml/` | Prasiddh | Aditya |
| `mobile/lib/core/buffer/` | Prasiddh | Aditya |
| `mobile/lib/features/monitoring/domain/` | Prasiddh | Aditya |
| `mobile/lib/features/check/domain/` | Prasiddh | Aditya |
| `mobile/lib/core/location/` | Vaishnavi | Aditya |
| `mobile/` remaining paths | Aditya | All |
| `dashboard/` | Vaishnavi | Shubhankar |
| `deployment/` | Utkarsh | Shubhankar |

Changes to shared documentation must be reviewed by Utkarsh.

## 9. Shared Contracts

The following interfaces must be agreed before implementation:

### Health monitoring

Owned by Prasiddh:

- `HrSample`
- `HeartRateSource`
- `AnomalyEvent`
- `AnomalyDetector`
- `ReplyClassifier`
- `LastMomentsBuffer`
- `SimulatorHeartRateSource`

### Location

Owned by Vaishnavi:

- `LocationService`
- Location data contract.
- Nearest-hospital response contract.
- Map URL generation, if specified by the approved design.

### Backend

Owned by Shubhankar:

- API routes.
- Request schemas.
- Response schemas.
- Authentication contract.
- Incident lifecycle API.
- Verification API.

### Database and integrations

Owned by Utkarsh:

- SQLAlchemy models.
- Migrations.
- Notifier interface.
- Hospital gateway interface.
- Demo seed/reset process.

No teammate may silently rename a shared interface.

## 10. Git Workflow

Use one branch per teammate.

Suggested branch names:

- `feature/ai-ml-monitoring`
- `feature/dashboard-location`
- `feature/backend`
- `feature/flutter-android`
- `feature/integration-database`

Rules:

1. Start from the agreed integration branch.
2. Pull or rebase from the integration branch before starting a new task.
3. Commit small logical changes.
4. Do not commit secrets.
5. Run tests before opening a PR.
6. Include a task ID in the PR description.
7. List files changed.
8. List tests run.
9. List dependencies on other teammates.
10. Utkarsh reviews and merges.
11. Resolve conflicts with the file owner.
12. Do not force-push over another person's work.

## 11. Handoff Rules

Each teammate updates their individual handoff file.

Individual files:

- `handoff/prasiddh.md`
- `handoff/vaishnavi.md`
- `handoff/shubhankar.md`
- `handoff/aditya.md`
- `handoff/utkarsh.md`

Each update must include:

- Completed tasks.
- Current task.
- Files created or modified.
- Interfaces exposed.
- Interfaces consumed.
- Tests run.
- Known failures.
- Blockers.
- Next steps.

Only Utkarsh updates the shared `HANDOFF.md`, using information supplied by the owners.

## 12. Conflict Resolution

If two teammates need to modify the same file:

1. Stop editing the shared file.
2. Identify the exact conflict.
3. Ask Utkarsh to coordinate.
4. Agree on one owner.
5. Have the other teammate provide a patch or interface requirement.
6. Review and merge the change.
7. Update the handoff.

Do not resolve ownership conflicts by independently overwriting code.

## 13. Final Responsibility

The project is complete only when all five roles work together in one integrated application.

Individual component completion does not equal project completion.

Utkarsh is responsible for verifying the final end-to-end flow, but every teammate remains responsible for the correctness of their own component.

**End of TEAM.md**