# SAHYOG — Master Handoff and Integration Tracker

**Project:** SAHYOG — Detect. Verify. Respond.  
**Document:** HANDOFF.md  
**Version:** 1.0  
**Status:** Initial project baseline  
**Integration lead:** Utkarsh

---

## 1. Purpose

This document is the central progress tracker for all five SAHYOG development roles.

It records:

- Task ownership.
- Task status.
- Dependencies.
- Integration decisions.
- Shared blockers.
- Testing progress.
- Demo readiness.

Every teammate maintains their own individual handoff file.

Utkarsh maintains this shared document.

## 2. Project Scope Reminder

The current prototype consists of:

- Flutter Android application.
- FastAPI backend.
- PostgreSQL database.
- React caregiver dashboard.
- Simulated health readings.
- AI/ML or statistical anomaly detection.
- Three approximately 60-second demo scenarios.
- Verification workflow.
- False-alarm resolution.
- No-response escalation.
- Location and seeded/cached hospital information.
- Mock notification service.
- Android APK and AAB preparation.

No physical smartwatch integration is part of the prototype.

The three scenarios must use the same detection and incident-response pipeline.

## 3. Task Status Vocabulary

| Status | Meaning |
|---|---|
| `NOT_STARTED` | Work has not begun |
| `IN_PROGRESS` | Implementation is underway |
| `BLOCKED` | Work cannot continue without a decision or dependency |
| `IMPLEMENTED` | Code exists but may not have passed tests |
| `TESTED` | Relevant tests passed locally |
| `INTEGRATED` | Tested and successfully merged/integrated |

Do not mark a task `INTEGRATED` merely because a pull request was opened.

## 4. Team Ownership

| Role | Owner | Responsibility |
|---|---|---|
| R1 | Prasiddh | AI/ML and health monitoring |
| R2 | Vaishnavi | Dashboard and location |
| R3 | Shubhankar | Backend |
| R4 | Aditya | Flutter Android frontend |
| R5 | Utkarsh | Integration and database |

## 5. Shared Architecture Decisions

### D1 — Prototype data source

The first prototype uses simulated health readings.

No real smartwatch, Bluetooth, ESP32 or MAX30102 integration is required.

### D2 — Three scenarios

The application must provide:

- `NORMAL`
- `TRUE_ANOMALY`
- `FALSE_ALARM`

Each scenario targets approximately 60 seconds.

### D3 — Shared pipeline

All scenarios use the same simulator interface, reading ingestion, detector, incident lifecycle, verification workflow and dashboard integration.

Only the generated input and expected outcome differ.

### D4 — Backend authority

The backend owns authoritative incident state and incident-creating anomaly decisions.

The mobile app must not independently invent the final incident outcome.

### D5 — False-alarm handling

If the person confirms they are okay:

- Record the response.
- Cancel pending escalation.
- Resolve the incident.
- Update the dashboard.

### D6 — True-anomaly handling

If verification receives no response within the configured demo timeout:

- Process the timeout.
- Initiate the approved escalation workflow.
- Record the escalation state.
- Update the dashboard.

### D7 — External services

The core demo must work with local or seeded data and mock notification services.

External services are optional.

### D8 — Android distribution

The team must generate an installable APK and prepare an AAB and Play Console assets.

Public Play Store approval is not assumed.

## 6. Master Task Board

### Phase 0 — Foundation and shared contracts

| Task ID | Task | Owner | Status |
|---|---|---|---|
| F0.1 | Inspect repository and current branch structure | Utkarsh | NOT_STARTED |
| F0.2 | Reconcile PRD and SYSTEM_DESIGN with repository | Utkarsh + All | NOT_STARTED |
| F0.3 | Confirm file ownership and branch rules | Utkarsh | NOT_STARTED |
| F0.4 | Confirm health-reading data contract | Prasiddh + Shubhankar | NOT_STARTED |
| F0.5 | Confirm incident status vocabulary | Shubhankar + Utkarsh | NOT_STARTED |
| F0.6 | Confirm API contracts | Shubhankar + All | NOT_STARTED |
| F0.7 | Confirm database entities and relationships | Utkarsh + Shubhankar | NOT_STARTED |
| F0.8 | Confirm scenario identifiers and timing | Prasiddh + Aditya + Shubhankar | NOT_STARTED |
| F0.9 | Confirm dashboard response contract | Vaishnavi + Shubhankar | NOT_STARTED |
| F0.10 | Confirm local development configuration | Utkarsh + All | NOT_STARTED |

**Phase acceptance:**

- Repository structure understood.
- Shared interfaces documented.
- No unresolved ownership conflicts.
- No conflicting API or database definitions.

### Phase 1 — Database and backend foundation

| Task ID | Task | Owner | Status |
|---|---|---|---|
| B1.1 | Configure backend environment | Shubhankar | NOT_STARTED |
| B1.2 | Configure database connection | Utkarsh + Shubhankar | NOT_STARTED |
| B1.3 | Create approved database models | Utkarsh | NOT_STARTED |
| B1.4 | Create initial migrations | Utkarsh | NOT_STARTED |
| B1.5 | Verify clean database setup | Utkarsh | NOT_STARTED |
| B1.6 | Configure FastAPI application startup | Shubhankar | NOT_STARTED |
| B1.7 | Implement approved authentication foundation | Shubhankar | NOT_STARTED |
| B1.8 | Implement profile and contact APIs | Shubhankar | NOT_STARTED |
| B1.9 | Implement health-check endpoint | Shubhankar | NOT_STARTED |
| B1.10 | Implement standard API error handling | Shubhankar | NOT_STARTED |

**Phase acceptance:**

- Database starts.
- Migrations apply from a clean state.
- Backend starts.
- Authentication foundation works.
- API errors are handled consistently.

### Phase 2 — AI/ML and simulated health monitoring

| Task ID | Task | Owner | Status |
|---|---|---|---|
| A2.1 | Finalise health sample contract | Prasiddh | NOT_STARTED |
| A2.2 | Implement simulated health-reading source | Prasiddh | NOT_STARTED |
| A2.3 | Implement reading validation | Prasiddh | NOT_STARTED |
| A2.4 | Implement stale/missing-reading handling | Prasiddh | NOT_STARTED |
| A2.5 | Implement bounded reading buffer | Prasiddh | NOT_STARTED |
| A2.6 | Implement baseline/statistical detector | Prasiddh | NOT_STARTED |
| A2.7 | Implement persistence/duration checks | Prasiddh | NOT_STARTED |
| A2.8 | Implement structured anomaly event | Prasiddh | NOT_STARTED |
| A2.9 | Integrate detector with reading API | Prasiddh + Shubhankar | NOT_STARTED |
| A2.10 | Create deterministic test vectors | Prasiddh | NOT_STARTED |
| A2.11 | Test normal, spike, drop and sustained anomaly | Prasiddh | NOT_STARTED |
| A2.12 | Test missing, stale and noisy readings | Prasiddh | NOT_STARTED |

**Phase acceptance:**

- Detector produces explainable results.
- Normal data does not create incidents.
- Sustained abnormal data can produce an anomaly event.
- Missing/stale data does not crash the backend.
- Duplicate event behaviour is controlled.

### Phase 3 — Incident and verification workflow

| Task ID | Task | Owner | Status |
|---|---|---|---|
| I3.1 | Confirm incident data model | Utkarsh + Shubhankar | NOT_STARTED |
| I3.2 | Implement incident service | Shubhankar | NOT_STARTED |
| I3.3 | Connect anomaly events to incidents | Prasiddh + Shubhankar | NOT_STARTED |
| I3.4 | Implement verification workflow | Shubhankar | NOT_STARTED |
| I3.5 | Implement "I'm okay" response | Shubhankar + Aditya | NOT_STARTED |
| I3.6 | Implement verification timeout | Shubhankar | NOT_STARTED |
| I3.7 | Implement escalation trigger | Shubhankar + Utkarsh | NOT_STARTED |
| I3.8 | Implement escalation cancellation | Shubhankar + Utkarsh | NOT_STARTED |
| I3.9 | Implement false-alarm resolution | Shubhankar + Aditya | NOT_STARTED |
| I3.10 | Test invalid incident transitions | Shubhankar | NOT_STARTED |
| I3.11 | Test duplicate incident prevention | Shubhankar + Utkarsh | NOT_STARTED |

**Phase acceptance:**

- Anomaly can create an incident.
- Verification starts.
- Confirmation resolves the false alarm.
- Timeout triggers escalation.
- Duplicate events do not create duplicate incidents.

### Phase 4 — Android application and demo controls

| Task ID | Task | Owner | Status |
|---|---|---|---|
| M4.1 | Inspect existing Flutter application | Aditya | NOT_STARTED |
| M4.2 | Finalise app navigation | Aditya | NOT_STARTED |
| M4.3 | Implement monitoring home screen | Aditya | NOT_STARTED |
| M4.4 | Implement three scenario Play buttons | Aditya | NOT_STARTED |
| M4.5 | Connect scenario selection to simulator | Aditya + Prasiddh | NOT_STARTED |
| M4.6 | Connect simulator to reading API | Prasiddh + Aditya | NOT_STARTED |
| M4.7 | Display current simulated readings | Aditya | NOT_STARTED |
| M4.8 | Display anomaly status | Aditya | NOT_STARTED |
| M4.9 | Implement verification screen | Aditya | NOT_STARTED |
| M4.10 | Implement "I'm okay" action | Aditya | NOT_STARTED |
| M4.11 | Display escalation state | Aditya | NOT_STARTED |
| M4.12 | Implement scenario reset/replay | Aditya + Shubhankar | NOT_STARTED |
| M4.13 | Implement loading and error states | Aditya | NOT_STARTED |
| M4.14 | Test on physical Android device | Aditya | NOT_STARTED |

**Phase acceptance:**

- All three buttons work.
- Readings are clearly labelled as simulated.
- Backend state is displayed correctly.
- Repeated scenarios do not conflict.
- The app works on a physical Android phone.

### Phase 5 — Dashboard and location

| Task ID | Task | Owner | Status |
|---|---|---|---|
| D5.1 | Inspect existing dashboard | Vaishnavi | NOT_STARTED |
| D5.2 | Implement dashboard layout | Vaishnavi | NOT_STARTED |
| D5.3 | Connect dashboard overview API | Vaishnavi + Shubhankar | NOT_STARTED |
| D5.4 | Display monitoring status | Vaishnavi | NOT_STARTED |
| D5.5 | Display latest reading summary | Vaishnavi | NOT_STARTED |
| D5.6 | Display anomaly and verification status | Vaishnavi | NOT_STARTED |
| D5.7 | Display escalated incidents | Vaishnavi | NOT_STARTED |
| D5.8 | Display resolved false alarms | Vaishnavi | NOT_STARTED |
| D5.9 | Implement location handling | Vaishnavi | NOT_STARTED |
| D5.10 | Implement hospital data fallback | Vaishnavi + Utkarsh | NOT_STARTED |
| D5.11 | Implement dashboard error/empty states | Vaishnavi | NOT_STARTED |
| D5.12 | Verify all three scenarios on dashboard | Vaishnavi + Shubhankar | NOT_STARTED |

**Phase acceptance:**

- Dashboard consumes real backend responses.
- All three scenario outcomes are represented correctly.
- Location failures do not crash the dashboard.
- Hospital fallback works without public internet.

### Phase 6 — Notifications and integration

| Task ID | Task | Owner | Status |
|---|---|---|---|
| N6.1 | Define notifier interface | Utkarsh | NOT_STARTED |
| N6.2 | Implement mock notifier | Utkarsh | NOT_STARTED |
| N6.3 | Connect notifier to escalation service | Utkarsh + Shubhankar | NOT_STARTED |
| N6.4 | Define hospital gateway interface | Utkarsh | NOT_STARTED |
| N6.5 | Connect hospital gateway to location service | Utkarsh + Vaishnavi | NOT_STARTED |
| N6.6 | Implement demo seed script | Utkarsh | NOT_STARTED |
| N6.7 | Implement safe demo reset | Utkarsh + Shubhankar | NOT_STARTED |
| N6.8 | Integrate all branches | Utkarsh + All | NOT_STARTED |
| N6.9 | Run end-to-end scenario tests | Utkarsh + All | NOT_STARTED |
| N6.10 | Fix integration failures | Responsible owner | NOT_STARTED |

**Phase acceptance:**

- Mock notifications work.
- Hospital information works through the approved abstraction.
- All components use the same contracts.
- End-to-end scenarios pass.

### Phase 7 — Stability and Android release

| Task ID | Task | Owner | Status |
|---|---|---|---|
| R7.1 | Review database indexes and query limits | Utkarsh | NOT_STARTED |
| R7.2 | Review backend timeouts and connection limits | Shubhankar + Utkarsh | NOT_STARTED |
| R7.3 | Test repeated scenario runs | All | NOT_STARTED |
| R7.4 | Check duplicate incidents and jobs | Shubhankar + Utkarsh | NOT_STARTED |
| R7.5 | Test backend restart/recovery | Shubhankar + Utkarsh | NOT_STARTED |
| R7.6 | Test local network demonstration | All | NOT_STARTED |
| R7.7 | Generate release APK | Aditya | NOT_STARTED |
| R7.8 | Generate release AAB | Aditya | NOT_STARTED |
| R7.9 | Configure app version and package ID | Aditya + Utkarsh | NOT_STARTED |
| R7.10 | Prepare privacy policy and store assets | Aditya + Utkarsh | NOT_STARTED |
| R7.11 | Verify Play Console requirements | Utkarsh | NOT_STARTED |
| R7.12 | Final demo rehearsal | All | NOT_STARTED |

**Phase acceptance:**

- Server survives repeated demonstrations.
- Android release builds are generated.
- Store-preparation assets are available.
- Final demonstration can run reliably.

## 7. Critical End-to-End Test

The following test is mandatory before the project is declared integrated.

### Test A — Normal

1. Start database.
2. Start backend.
3. Start dashboard.
4. Launch Android app.
5. Press Normal.
6. Observe simulated readings.
7. Confirm detector returns normal.
8. Confirm no incident is created.
9. Confirm no escalation is generated.
10. Confirm dashboard remains normal.

Expected result: `NORMAL`.

### Test B — True Anomaly

1. Reset the previous demo run.
2. Press True Anomaly.
3. Observe the readings.
4. Confirm detector identifies the sustained unusual pattern.
5. Confirm incident creation.
6. Confirm verification starts.
7. Do not respond.
8. Wait for verification timeout.
9. Confirm escalation is recorded.
10. Confirm dashboard displays the escalated incident.

Expected result: `ESCALATED`.

### Test C — False Alarm

1. Reset the previous demo run.
2. Press False Alarm.
3. Observe the readings.
4. Confirm anomaly detection.
5. Confirm verification starts.
6. Press "I'm okay".
7. Confirm the backend records the response.
8. Confirm pending escalation is cancelled.
9. Confirm incident is resolved.
10. Confirm dashboard reflects the resolved state.

Expected result: `FALSE_ALARM_RESOLVED`.

### Test D — Repeated execution

1. Run Normal.
2. Run True Anomaly.
3. Run False Alarm.
4. Repeat the sequence.
5. Do not restart the backend.
6. Check database records.
7. Check server logs.
8. Check background jobs.
9. Check dashboard state.

Expected result:

- No server crash.
- No duplicate incident from replay.
- No leftover pending escalation from an old run.
- No runaway worker.
- No conflicting scenario state.

## 8. Integration Risks

| Risk | Owner | Mitigation |
|---|---|---|
| API mismatch | Shubhankar | Freeze and publish canonical API contracts |
| Database/model mismatch | Utkarsh | Agree schema before parallel implementation |
| Detector inconsistency | Prasiddh | Use deterministic test vectors |
| UI uses fake incident state | Aditya | Display backend-authoritative state |
| Dashboard uses hardcoded cards | Vaishnavi | Consume backend APIs |
| Duplicate incidents | Shubhankar + Utkarsh | Idempotency and run isolation |
| External API unavailable | Utkarsh + Vaishnavi | Seeded/cached fallback |
| Server overload | Shubhankar + Utkarsh | Bounded work, timeouts and controlled tests |
| Scenario replay conflict | Aditya + Shubhankar | Unique run ID and safe reset |
| Play Store review delay | Utkarsh + Aditya | APK fallback and early Play Console checks |

## 9. Individual Handoff Files

Each teammate maintains:

- `handoff/prasiddh.md`
- `handoff/vaishnavi.md`
- `handoff/shubhankar.md`
- `handoff/aditya.md`
- `handoff/utkarsh.md`

### Required individual handoff format

```markdown
# Individual Handoff

Owner:
Role:
Last updated:

## Completed
- Task IDs:
- Summary:

## In Progress
- Task IDs:
- Current state:

## Files Changed
- File:
- Reason:

## Interfaces
- Consumed:
- Exposed:
- Changed:

## Tests
- Command:
- Result:

## Commits
- Commit ID:
- Summary:

## Blockers
- Issue:
- Required decision/owner:

## Next Steps
- Task:
- Dependency:
```

## 10. Shared Integration Log

Utkarsh must record important architecture and integration decisions here.

| Date | Decision/Issue | Owner | Resolution |
|---|---|---|---|
| 2026-11-26 | Initial project contract review | Utkarsh | Completed. All 5 roles aligned on PRD/System Design. |
| 2026-11-27 | Health-reading schema confirmed | Prasiddh + Shubhankar | Completed. Canonical ReadingRequest schema in place. |
| 2026-11-27 | Incident lifecycle confirmed | Shubhankar + Utkarsh | Completed. Verification timeout and mock notifier wired. |
| 2026-11-27 | Database schema confirmed | Utkarsh | Completed. location_snapshots (25c1af2fe01c) implemented and tested. |
| 2026-11-27 | Mobile API integration confirmed | Aditya + Shubhankar | Completed. Models, reading transport, and location sender aligned. |
| 2026-11-28 | Dashboard API integration confirmed | Vaishnavi + Shubhankar | Completed. React dashboard passes 22 vitest tests and builds clean. |
| 2026-11-28 | End-to-end demo passed | All | Completed. All 3 scenarios (NORMAL, TRUE_ANOMALY, FALSE_ALARM) verified. |

## 11. Final Definition of Integrated

The project may be marked integrated only when:

- The Android app builds.
- The three scenarios run.
- The detector works on the scenario readings.
- The backend processes the same scenario pipeline.
- The database records the required state.
- Verification works.
- False-alarm cancellation works.
- No-response escalation works.
- The dashboard reflects the correct outcome.
- Location/hospital fallback works.
- Mock notifications are clearly labelled.
- Repeated runs do not crash the server.
- The APK works on a physical device.
- Release build instructions are documented.

## 12. Final Rule

Every teammate owns their component.

Utkarsh owns integration.

No one should wait until the last day to discover that their component does not work with another person's component.

**The objective is one stable, repeatable SAHYOG application — not five separate implementations.**

# SAHYOG — Master Handoff and Integration Tracker

**Project:** SAHYOG — Detect. Verify. Respond.  
**Document:** HANDOFF.md  
**Version:** 1.0  
**Status:** Initial project baseline  
**Integration lead:** Utkarsh

---

## 1. Purpose

This document is the central progress tracker for all five SAHYOG development roles.

It records:

- Task ownership.
- Task status.
- Dependencies.
- Integration decisions.
- Shared blockers.
- Testing progress.
- Demo readiness.

Every teammate maintains their own individual handoff file.

Utkarsh maintains this shared document.

## 2. Project Scope Reminder

The current prototype consists of:

- Flutter Android application.
- FastAPI backend.
- PostgreSQL database.
- React caregiver dashboard.
- Simulated health readings.
- AI/ML or statistical anomaly detection.
- Three approximately 60-second demo scenarios.
- Verification workflow.
- False-alarm resolution.
- No-response escalation.
- Location and seeded/cached hospital information.
- Mock notification service.
- Android APK and AAB preparation.

No physical smartwatch integration is part of the prototype.

The three scenarios must use the same detection and incident-response pipeline.

## 3. Task Status Vocabulary

| Status | Meaning |
|---|---|
| `NOT_STARTED` | Work has not begun |
| `IN_PROGRESS` | Implementation is underway |
| `BLOCKED` | Work cannot continue without a decision or dependency |
| `IMPLEMENTED` | Code exists but may not have passed tests |
| `TESTED` | Relevant tests passed locally |
| `INTEGRATED` | Tested and successfully merged/integrated |

Do not mark a task `INTEGRATED` merely because a pull request was opened.

## 4. Team Ownership

| Role | Owner | Responsibility |
|---|---|---|
| R1 | Prasiddh | AI/ML and health monitoring |
| R2 | Vaishnavi | Dashboard and location |
| R3 | Shubhankar | Backend |
| R4 | Aditya | Flutter Android frontend |
| R5 | Utkarsh | Integration and database |

## 5. Shared Architecture Decisions

### D1 — Prototype data source

The first prototype uses simulated health readings.

No real smartwatch, Bluetooth, ESP32 or MAX30102 integration is required.

### D2 — Three scenarios

The application must provide:

- `NORMAL`
- `TRUE_ANOMALY`
- `FALSE_ALARM`

Each scenario targets approximately 60 seconds.

### D3 — Shared pipeline

All scenarios use the same simulator interface, reading ingestion, detector, incident lifecycle, verification workflow and dashboard integration.

Only the generated input and expected outcome differ.

### D4 — Backend authority

The backend owns authoritative incident state and incident-creating anomaly decisions.

The mobile app must not independently invent the final incident outcome.

### D5 — False-alarm handling

If the person confirms they are okay:

- Record the response.
- Cancel pending escalation.
- Resolve the incident.
- Update the dashboard.

### D6 — True-anomaly handling

If verification receives no response within the configured demo timeout:

- Process the timeout.
- Initiate the approved escalation workflow.
- Record the escalation state.
- Update the dashboard.

### D7 — External services

The core demo must work with local or seeded data and mock notification services.

External services are optional.

### D8 — Android distribution

The team must generate an installable APK and prepare an AAB and Play Console assets.

Public Play Store approval is not assumed.

## 6. Master Task Board

### Phase 0 — Foundation and shared contracts

| Task ID | Task | Owner | Status |
|---|---|---|---|
| F0.1 | Inspect repository and current branch structure | Utkarsh | NOT_STARTED |
| F0.2 | Reconcile PRD and SYSTEM_DESIGN with repository | Utkarsh + All | NOT_STARTED |
| F0.3 | Confirm file ownership and branch rules | Utkarsh | NOT_STARTED |
| F0.4 | Confirm health-reading data contract | Prasiddh + Shubhankar | NOT_STARTED |
| F0.5 | Confirm incident status vocabulary | Shubhankar + Utkarsh | NOT_STARTED |
| F0.6 | Confirm API contracts | Shubhankar + All | NOT_STARTED |
| F0.7 | Confirm database entities and relationships | Utkarsh + Shubhankar | NOT_STARTED |
| F0.8 | Confirm scenario identifiers and timing | Prasiddh + Aditya + Shubhankar | NOT_STARTED |
| F0.9 | Confirm dashboard response contract | Vaishnavi + Shubhankar | NOT_STARTED |
| F0.10 | Confirm local development configuration | Utkarsh + All | NOT_STARTED |

**Phase acceptance:**

- Repository structure understood.
- Shared interfaces documented.
- No unresolved ownership conflicts.
- No conflicting API or database definitions.

### Phase 1 — Database and backend foundation

| Task ID | Task | Owner | Status |
|---|---|---|---|
| B1.1 | Configure backend environment | Shubhankar | NOT_STARTED |
| B1.2 | Configure database connection | Utkarsh + Shubhankar | NOT_STARTED |
| B1.3 | Create approved database models | Utkarsh | NOT_STARTED |
| B1.4 | Create initial migrations | Utkarsh | NOT_STARTED |
| B1.5 | Verify clean database setup | Utkarsh | NOT_STARTED |
| B1.6 | Configure FastAPI application startup | Shubhankar | NOT_STARTED |
| B1.7 | Implement approved authentication foundation | Shubhankar | NOT_STARTED |
| B1.8 | Implement profile and contact APIs | Shubhankar | NOT_STARTED |
| B1.9 | Implement health-check endpoint | Shubhankar | NOT_STARTED |
| B1.10 | Implement standard API error handling | Shubhankar | NOT_STARTED |

**Phase acceptance:**

- Database starts.
- Migrations apply from a clean state.
- Backend starts.
- Authentication foundation works.
- API errors are handled consistently.

### Phase 2 — AI/ML and simulated health monitoring

| Task ID | Task | Owner | Status |
|---|---|---|---|
| A2.1 | Finalise health sample contract | Prasiddh | NOT_STARTED |
| A2.2 | Implement simulated health-reading source | Prasiddh | NOT_STARTED |
| A2.3 | Implement reading validation | Prasiddh | NOT_STARTED |
| A2.4 | Implement stale/missing-reading handling | Prasiddh | NOT_STARTED |
| A2.5 | Implement bounded reading buffer | Prasiddh | NOT_STARTED |
| A2.6 | Implement baseline/statistical detector | Prasiddh | NOT_STARTED |
| A2.7 | Implement persistence/duration checks | Prasiddh | NOT_STARTED |
| A2.8 | Implement structured anomaly event | Prasiddh | NOT_STARTED |
| A2.9 | Integrate detector with reading API | Prasiddh + Shubhankar | NOT_STARTED |
| A2.10 | Create deterministic test vectors | Prasiddh | NOT_STARTED |
| A2.11 | Test normal, spike, drop and sustained anomaly | Prasiddh | NOT_STARTED |
| A2.12 | Test missing, stale and noisy readings | Prasiddh | NOT_STARTED |

**Phase acceptance:**

- Detector produces explainable results.
- Normal data does not create incidents.
- Sustained abnormal data can produce an anomaly event.
- Missing/stale data does not crash the backend.
- Duplicate event behaviour is controlled.

### Phase 3 — Incident and verification workflow

| Task ID | Task | Owner | Status |
|---|---|---|---|
| I3.1 | Confirm incident data model | Utkarsh + Shubhankar | NOT_STARTED |
| I3.2 | Implement incident service | Shubhankar | NOT_STARTED |
| I3.3 | Connect anomaly events to incidents | Prasiddh + Shubhankar | NOT_STARTED |
| I3.4 | Implement verification workflow | Shubhankar | NOT_STARTED |
| I3.5 | Implement "I'm okay" response | Shubhankar + Aditya | NOT_STARTED |
| I3.6 | Implement verification timeout | Shubhankar | NOT_STARTED |
| I3.7 | Implement escalation trigger | Shubhankar + Utkarsh | NOT_STARTED |
| I3.8 | Implement escalation cancellation | Shubhankar + Utkarsh | NOT_STARTED |
| I3.9 | Implement false-alarm resolution | Shubhankar + Aditya | NOT_STARTED |
| I3.10 | Test invalid incident transitions | Shubhankar | NOT_STARTED |
| I3.11 | Test duplicate incident prevention | Shubhankar + Utkarsh | NOT_STARTED |

**Phase acceptance:**

- Anomaly can create an incident.
- Verification starts.
- Confirmation resolves the false alarm.
- Timeout triggers escalation.
- Duplicate events do not create duplicate incidents.

### Phase 4 — Android application and demo controls

| Task ID | Task | Owner | Status |
|---|---|---|---|
| M4.1 | Inspect existing Flutter application | Aditya | NOT_STARTED |
| M4.2 | Finalise app navigation | Aditya | NOT_STARTED |
| M4.3 | Implement monitoring home screen | Aditya | NOT_STARTED |
| M4.4 | Implement three scenario Play buttons | Aditya | NOT_STARTED |
| M4.5 | Connect scenario selection to simulator | Aditya + Prasiddh | NOT_STARTED |
| M4.6 | Connect simulator to reading API | Prasiddh + Aditya | NOT_STARTED |
| M4.7 | Display current simulated readings | Aditya | NOT_STARTED |
| M4.8 | Display anomaly status | Aditya | NOT_STARTED |
| M4.9 | Implement verification screen | Aditya | NOT_STARTED |
| M4.10 | Implement "I'm okay" action | Aditya | NOT_STARTED |
| M4.11 | Display escalation state | Aditya | NOT_STARTED |
| M4.12 | Implement scenario reset/replay | Aditya + Shubhankar | NOT_STARTED |
| M4.13 | Implement loading and error states | Aditya | NOT_STARTED |
| M4.14 | Test on physical Android device | Aditya | NOT_STARTED |

**Phase acceptance:**

- All three buttons work.
- Readings are clearly labelled as simulated.
- Backend state is displayed correctly.
- Repeated scenarios do not conflict.
- The app works on a physical Android phone.

### Phase 5 — Dashboard and location

| Task ID | Task | Owner | Status |
|---|---|---|---|
| D5.1 | Inspect existing dashboard | Vaishnavi | NOT_STARTED |
| D5.2 | Implement dashboard layout | Vaishnavi | NOT_STARTED |
| D5.3 | Connect dashboard overview API | Vaishnavi + Shubhankar | NOT_STARTED |
| D5.4 | Display monitoring status | Vaishnavi | NOT_STARTED |
| D5.5 | Display latest reading summary | Vaishnavi | NOT_STARTED |
| D5.6 | Display anomaly and verification status | Vaishnavi | NOT_STARTED |
| D5.7 | Display escalated incidents | Vaishnavi | NOT_STARTED |
| D5.8 | Display resolved false alarms | Vaishnavi | NOT_STARTED |
| D5.9 | Implement location handling | Vaishnavi | NOT_STARTED |
| D5.10 | Implement hospital data fallback | Vaishnavi + Utkarsh | NOT_STARTED |
| D5.11 | Implement dashboard error/empty states | Vaishnavi | NOT_STARTED |
| D5.12 | Verify all three scenarios on dashboard | Vaishnavi + Shubhankar | NOT_STARTED |

**Phase acceptance:**

- Dashboard consumes real backend responses.
- All three scenario outcomes are represented correctly.
- Location failures do not crash the dashboard.
- Hospital fallback works without public internet.

### Phase 6 — Notifications and integration

| Task ID | Task | Owner | Status |
|---|---|---|---|
| N6.1 | Define notifier interface | Utkarsh | NOT_STARTED |
| N6.2 | Implement mock notifier | Utkarsh | NOT_STARTED |
| N6.3 | Connect notifier to escalation service | Utkarsh + Shubhankar | NOT_STARTED |
| N6.4 | Define hospital gateway interface | Utkarsh | NOT_STARTED |
| N6.5 | Connect hospital gateway to location service | Utkarsh + Vaishnavi | NOT_STARTED |
| N6.6 | Implement demo seed script | Utkarsh | NOT_STARTED |
| N6.7 | Implement safe demo reset | Utkarsh + Shubhankar | NOT_STARTED |
| N6.8 | Integrate all branches | Utkarsh + All | NOT_STARTED |
| N6.9 | Run end-to-end scenario tests | Utkarsh + All | NOT_STARTED |
| N6.10 | Fix integration failures | Responsible owner | NOT_STARTED |

**Phase acceptance:**

- Mock notifications work.
- Hospital information works through the approved abstraction.
- All components use the same contracts.
- End-to-end scenarios pass.

### Phase 7 — Stability and Android release

| Task ID | Task | Owner | Status |
|---|---|---|---|
| R7.1 | Review database indexes and query limits | Utkarsh | NOT_STARTED |
| R7.2 | Review backend timeouts and connection limits | Shubhankar + Utkarsh | NOT_STARTED |
| R7.3 | Test repeated scenario runs | All | NOT_STARTED |
| R7.4 | Check duplicate incidents and jobs | Shubhankar + Utkarsh | NOT_STARTED |
| R7.5 | Test backend restart/recovery | Shubhankar + Utkarsh | NOT_STARTED |
| R7.6 | Test local network demonstration | All | NOT_STARTED |
| R7.7 | Generate release APK | Aditya | NOT_STARTED |
| R7.8 | Generate release AAB | Aditya | NOT_STARTED |
| R7.9 | Configure app version and package ID | Aditya + Utkarsh | NOT_STARTED |
| R7.10 | Prepare privacy policy and store assets | Aditya + Utkarsh | NOT_STARTED |
| R7.11 | Verify Play Console requirements | Utkarsh | NOT_STARTED |
| R7.12 | Final demo rehearsal | All | NOT_STARTED |

**Phase acceptance:**

- Server survives repeated demonstrations.
- Android release builds are generated.
- Store-preparation assets are available.
- Final demonstration can run reliably.

## 7. Critical End-to-End Test

The following test is mandatory before the project is declared integrated.

### Test A — Normal

1. Start database.
2. Start backend.
3. Start dashboard.
4. Launch Android app.
5. Press Normal.
6. Observe simulated readings.
7. Confirm detector returns normal.
8. Confirm no incident is created.
9. Confirm no escalation is generated.
10. Confirm dashboard remains normal.

Expected result: `NORMAL`.

### Test B — True Anomaly

1. Reset the previous demo run.
2. Press True Anomaly.
3. Observe the readings.
4. Confirm detector identifies the sustained unusual pattern.
5. Confirm incident creation.
6. Confirm verification starts.
7. Do not respond.
8. Wait for verification timeout.
9. Confirm escalation is recorded.
10. Confirm dashboard displays the escalated incident.

Expected result: `ESCALATED`.

### Test C — False Alarm

1. Reset the previous demo run.
2. Press False Alarm.
3. Observe the readings.
4. Confirm anomaly detection.
5. Confirm verification starts.
6. Press "I'm okay".
7. Confirm the backend records the response.
8. Confirm pending escalation is cancelled.
9. Confirm incident is resolved.
10. Confirm dashboard reflects the resolved state.

Expected result: `FALSE_ALARM_RESOLVED`.

### Test D — Repeated execution

1. Run Normal.
2. Run True Anomaly.
3. Run False Alarm.
4. Repeat the sequence.
5. Do not restart the backend.
6. Check database records.
7. Check server logs.
8. Check background jobs.
9. Check dashboard state.

Expected result:

- No server crash.
- No duplicate incident from replay.
- No leftover pending escalation from an old run.
- No runaway worker.
- No conflicting scenario state.

## 8. Integration Risks

| Risk | Owner | Mitigation |
|---|---|---|
| API mismatch | Shubhankar | Freeze and publish canonical API contracts |
| Database/model mismatch | Utkarsh | Agree schema before parallel implementation |
| Detector inconsistency | Prasiddh | Use deterministic test vectors |
| UI uses fake incident state | Aditya | Display backend-authoritative state |
| Dashboard uses hardcoded cards | Vaishnavi | Consume backend APIs |
| Duplicate incidents | Shubhankar + Utkarsh | Idempotency and run isolation |
| External API unavailable | Utkarsh + Vaishnavi | Seeded/cached fallback |
| Server overload | Shubhankar + Utkarsh | Bounded work, timeouts and controlled tests |
| Scenario replay conflict | Aditya + Shubhankar | Unique run ID and safe reset |
| Play Store review delay | Utkarsh + Aditya | APK fallback and early Play Console checks |

## 9. Individual Handoff Files

Each teammate maintains:

- `handoff/prasiddh.md`
- `handoff/vaishnavi.md`
- `handoff/shubhankar.md`
- `handoff/aditya.md`
- `handoff/utkarsh.md`

### Required individual handoff format

```markdown
# Individual Handoff

Owner:
Role:
Last updated:

## Completed
- Task IDs:
- Summary:

## In Progress
- Task IDs:
- Current state:

## Files Changed
- File:
- Reason:

## Interfaces
- Consumed:
- Exposed:
- Changed:

## Tests
- Command:
- Result:

## Commits
- Commit ID:
- Summary:

## Blockers
- Issue:
- Required decision/owner:

## Next Steps
- Task:
- Dependency:
```

## 10. Shared Integration Log

Utkarsh must record important architecture and integration decisions here.

| Date | Decision/Issue | Owner | Resolution |
|---|---|---|---|
| 2026-11-26 | Initial project contract review | Utkarsh | Completed. All 5 roles aligned on PRD/System Design. |
| 2026-11-27 | Health-reading schema confirmed | Prasiddh + Shubhankar | Completed. Canonical ReadingRequest schema in place. |
| 2026-11-27 | Incident lifecycle confirmed | Shubhankar + Utkarsh | Completed. Verification timeout and mock notifier wired. |
| 2026-11-27 | Database schema confirmed | Utkarsh | Completed. location_snapshots (25c1af2fe01c) implemented and tested. |
| 2026-11-27 | Mobile API integration confirmed | Aditya + Shubhankar | Completed. Models, reading transport, and location sender aligned. |
| 2026-11-28 | Dashboard API integration confirmed | Vaishnavi + Shubhankar | Completed. React dashboard passes 22 vitest tests and builds clean. |
| 2026-11-28 | End-to-end demo passed | All | Completed. All 3 scenarios (NORMAL, TRUE_ANOMALY, FALSE_ALARM) verified. |

## 11. Final Definition of Integrated

The project may be marked integrated only when:

- The Android app builds.
- The three scenarios run.
- The detector works on the scenario readings.
- The backend processes the same scenario pipeline.
- The database records the required state.
- Verification works.
- False-alarm cancellation works.
- No-response escalation works.
- The dashboard reflects the correct outcome.
- Location/hospital fallback works.
- Mock notifications are clearly labelled.
- Repeated runs do not crash the server.
- The APK works on a physical device.
- Release build instructions are documented.

## 12. Final Rule

Every teammate owns their component.

Utkarsh owns integration.

No one should wait until the last day to discover that their component does not work with another person's component.

**The objective is one stable, repeatable SAHYOG application — not five separate implementations.**

**End of HANDOFF.md**