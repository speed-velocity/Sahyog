# SAHYOG — Product Requirements Document (PRD)

**Project:** SAHYOG — Detect. Verify. Respond.  
**Document:** PRD.md  
**Version:** 1.0  
**Status:** Proposed project baseline  
**Target platform:** Android  
**Primary demo:** Three deterministic, approximately 60-second scenarios

---

## 1. Product Overview

SAHYOG is a health-monitoring and emergency-response prototype designed to demonstrate how unusual health patterns can be detected, verified and escalated when a person may need assistance.

The system is intended to support people living independently, including elderly people who may not be able to request help immediately during an emergency.

The prototype demonstrates the following workflow:

1. Receive simulated health readings.
2. Analyse readings using the health-monitoring and anomaly-detection pipeline.
3. Identify unusual patterns.
4. Ask the person to confirm whether they are okay.
5. Resolve a false alarm if the person confirms they are safe.
6. Demonstrate escalation if the person does not respond.
7. Display the incident and its status to an authorised caregiver through a dashboard.

**Core principle:** Detect. Verify. Respond.

SAHYOG is a prototype, not a clinically validated medical device or emergency-dispatch service.

## 2. Problem Statement

A person living alone may experience a sudden health-related event without being able to contact a family member or caregiver.

A system that only collects readings is insufficient. It must also distinguish ordinary readings from unusual patterns, verify the person's condition where possible, and communicate the appropriate status to an authorised caregiver.

The prototype focuses on demonstrating this complete workflow rather than claiming to diagnose a medical condition.

## 3. Product Goals

The project must:

- Provide a functional Android application.
- Demonstrate health monitoring using simulated data.
- Demonstrate anomaly detection.
- Distinguish an anomaly from a confirmed emergency.
- Provide a person-verification mechanism.
- Demonstrate escalation when verification receives no response.
- Handle a false alarm when the person confirms they are okay.
- Provide a caregiver dashboard that reflects the actual backend state.
- Provide location and nearby-hospital information using available or seeded data.
- Run repeatedly without requiring the server to restart.
- Be testable on physical Android devices.
- Prepare an Android release build and Play Store submission assets.

## 4. Explicit Prototype Scope

### 4.1 Included

- Android application built with Flutter.
- Backend built with FastAPI.
- PostgreSQL database.
- Caregiver dashboard built with React, subject to the existing repository structure.
- Simulated health-reading generator.
- AI/ML or statistical anomaly-detection pipeline.
- Personalized or configurable demo baseline, where supported by the approved implementation.
- Normal, true-anomaly and false-alarm scenarios.
- Verification workflow.
- Incident lifecycle management.
- Simulated notification/escalation.
- Location handling.
- Seeded or cached hospital information.
- Dashboard incident visibility.
- Demo reset and replay.
- Local development and demonstration configuration.
- Android APK and AAB generation.

### 4.2 Explicitly Excluded from this Prototype

The following are not part of the current implementation target:

- Physical smartwatch connectivity.
- Bluetooth Low Energy implementation.
- ESP32 integration.
- MAX30102 sensor integration.
- Apple Watch integration.
- Universal support for all smartwatch brands.
- Clinical diagnosis.
- Clinical validation of anomaly thresholds.
- Guaranteed emergency-service dispatch.
- Guaranteed hospital acceptance.
- Guaranteed SMS delivery.
- Production-grade integration with hospitals.
- Advanced ML training requiring a real labelled medical dataset.
- Public production availability being guaranteed within one or two days.

The architecture may allow future smartwatch integration, but the prototype must use simulated readings.

The application must clearly label simulated data. It must never present simulated readings as actual live wearable measurements.

## 5. Target Users

### Primary user

A person living independently who may benefit from health monitoring and a way to request or trigger assistance.

### Secondary user

A family member, caregiver or authorised responder who needs to see the monitored person's status and incident information.

### Demonstration user

A hackathon evaluator who uses the three Play buttons to observe the system's behaviour.

## 6. Core Application Features

### 6.1 Monitoring

The app must show:

- Monitoring status.
- Whether readings are simulated.
- Latest available reading.
- Reading timestamp.
- Current detection status.
- Current scenario, if a demo is running.

The app must not imply that a real wearable is connected.

### 6.2 Scenario selection

The main demonstration interface must provide three clearly labelled Play buttons:

1. Normal — No emergency.
2. True Anomaly — Escalation.
3. False Alarm — Person is okay.

Each scenario must run for approximately 60 seconds.

The scenarios must use the same application pipeline. They must differ in their input data and expected outcome, not in their underlying implementation.

The app must prevent conflicting scenarios from running simultaneously.

### 6.3 Scenario A — Normal

Purpose: Demonstrate that the system does not create an emergency when readings are ordinary.

Expected behaviour:

- Generate simulated normal readings.
- Validate and process readings.
- Run the anomaly detector.
- Produce no anomaly event.
- Create no emergency incident.
- Trigger no verification countdown.
- Trigger no escalation.
- Display a normal/safe status.
- Update the dashboard to reflect normal operation.

Acceptance criteria:

- No incident is created for the run.
- No emergency notification is generated.
- The UI does not display an active emergency.
- Replaying the scenario does not create duplicate incidents.

### 6.4 Scenario B — True Anomaly

Purpose: Demonstrate sustained abnormal readings, verification and escalation.

Expected behaviour:

- Generate simulated readings containing a sustained abnormal pattern.
- Pass readings through the same validation and detection pipeline used in normal monitoring.
- Detect an anomaly.
- Create or update an incident according to the backend incident lifecycle.
- Start the verification workflow.
- Display a prompt asking the person whether they are okay.
- For this scenario, simulate no response.
- Allow the configured verification window to expire.
- Trigger the approved escalation workflow.
- Show the escalated incident in the mobile app and caregiver dashboard.

Acceptance criteria:

- The detector processes the readings rather than returning a hardcoded success.
- An anomaly event is created.
- Verification starts.
- No-response causes escalation.
- The incident appears on the dashboard.
- Notification delivery is labelled as simulated if a mock notifier is used.

### 6.5 Scenario C — False Alarm

Purpose: Demonstrate that anomaly detection does not automatically mean emergency escalation.

Expected behaviour:

- Generate simulated readings containing an unusual pattern.
- Detect the anomaly.
- Create or update the incident.
- Start verification.
- Present an "I'm okay" confirmation action.
- The user confirms that they are safe.
- The backend records the confirmation.
- Pending escalation is cancelled.
- The incident is resolved as a false alarm or equivalent approved terminal state.
- The dashboard reflects the resolved state.

Acceptance criteria:

- The anomaly is genuinely detected by the configured detector.
- Verification is initiated.
- User confirmation is accepted.
- Pending escalation is cancelled.
- No emergency escalation is sent after confirmation.
- The incident is recorded as resolved.
- The dashboard does not continue displaying an active emergency.

### 6.6 Scenario timing

Each scenario should last approximately 60 seconds.

The timing must be configurable rather than scattered as hardcoded delays across the codebase.

The true-anomaly scenario must include enough time for:

- Reading generation.
- Detection.
- Verification.
- No-response timeout.
- Escalation display.

The false-alarm scenario must allow the user to confirm they are okay during the verification window.

A scenario may finish slightly earlier or later when necessary, but the target demonstration duration is approximately one minute.

The backend must use a consistent time source and scenario-run identifier. The mobile app must not independently invent a different incident outcome.

## 7. Incident and Detection Terminology

The following concepts must remain distinct throughout the system:

**Normal:** No anomaly has been detected.

**Anomaly detected:** The reading pattern appears unusual according to the configured detector.

**Verification pending:** The person has been asked to confirm their condition.

**False alarm resolved:** The person confirmed they are okay, and pending escalation was cancelled.

**Escalated:** The configured verification workflow received no response and escalation was initiated.

**Closed/resolved:** The incident reached its approved terminal state.

An anomaly must never automatically be described as a confirmed medical emergency.

## 8. AI/ML Requirements

The health-monitoring component must:

- Validate incoming readings.
- Handle missing and stale readings.
- Consider the approved baseline and context.
- Identify unusual patterns.
- Support persistence/duration checks.
- Produce an explainable result.
- Avoid repeated duplicate anomaly events.
- Support deterministic test data.
- Provide consistent output for the backend.

The team must accurately describe the implementation.

If the detector is statistical or rule-based, do not claim that it is a trained ML model.

If an ML model is used, document the algorithm, features, training or fitting approach, limitations and evaluation.

No clinical accuracy claim is permitted.

## 9. Location and Hospital Requirements

The application should support location information according to the approved permission and data model.

It must handle:

- Permission granted.
- Permission denied.
- Location unavailable.
- Missing coordinates.
- Stale location.
- Hospital data unavailable.

The hackathon demonstration must use seeded or cached hospital information if external services are unavailable.

The application must not claim that a hospital has accepted or acknowledged an incident unless an actual integration confirms it.

## 10. Caregiver Dashboard Requirements

The dashboard must show backend-authoritative information.

It should provide:

- Monitored-person status.
- Latest available readings.
- Reading timestamps.
- Anomaly status.
- Verification status.
- Incident status.
- Incident timeline.
- Location when available.
- Nearby-hospital information when available.
- Whether a notification is real or simulated.

The dashboard must accurately reflect all three scenarios.

## 11. Reliability Requirements

The application must:

- Handle backend unavailability gracefully.
- Avoid duplicate scenario execution.
- Avoid duplicate incident creation.
- Avoid uncontrolled polling.
- Avoid infinite retries.
- Avoid unbounded in-memory buffers.
- Use timeouts for network requests.
- Handle invalid input safely.
- Support repeated scenario runs.
- Support demo reset without deleting unrelated user data.
- Provide logs sufficient for debugging without logging sensitive health information.

The core demo must not require public internet access or external paid services.

## 12. Android and Distribution Requirements

The Android app must:

- Build successfully.
- Install on a physical Android device.
- Have a stable application ID.
- Have appropriate versioning.
- Have an app icon and launch screen.
- Have correct permissions.
- Support a release build.
- Generate a signed APK for direct testing.
- Generate an Android App Bundle for Play Console preparation.

Prepare:
- Store title and description.
- Screenshots.
- Privacy policy URL.
- App icon and feature graphic.
- Data safety disclosures.
- Health-related declarations, if applicable.
- Permission declarations.
- Release signing configuration.

Do not claim public Play Store approval until the account's eligibility, testing requirements and review status are confirmed.

## 13. Non-Functional Requirements

### Performance
- The app should remain responsive during scenario execution.
- Detection must not block the UI.
- API calls must use appropriate timeouts.
- Database queries must be bounded.

### Security
- Protect user and caregiver information.
- Enforce authentication and authorization where required.
- Do not expose secrets in mobile or dashboard code.
- Do not commit credentials.

### Maintainability
- Follow role-based file ownership.
- Use shared API and data contracts.
- Avoid duplicated business logic.
- Document configuration and setup.

### Demonstrability
- The three scenarios must be repeatable.
- The demo must work with seeded data.
- The team must be able to explain which parts are real and which are simulated.

## 14. Definition of Done

The prototype is ready when:

1. The Android app builds and installs.
2. All three Play buttons work.
3. Normal produces no incident.
4. True anomaly produces detection, verification and escalation.
5. False alarm produces detection, confirmation and resolution.
6. All scenarios use the same pipeline.
7. Dashboard states match backend states.
8. Location/hospital fallback works.
9. Repeated tests do not crash the server.
10. No duplicate incidents are created by replay.
11. Simulated data and notifications are clearly labelled.
12. A release APK and AAB can be generated.
13. The team has reproducible setup and demo instructions.

# SAHYOG — Product Requirements Document (PRD)

**Project:** SAHYOG — Detect. Verify. Respond.  
**Document:** PRD.md  
**Version:** 1.0  
**Status:** Proposed project baseline  
**Target platform:** Android  
**Primary demo:** Three deterministic, approximately 60-second scenarios

---

## 1. Product Overview

SAHYOG is a health-monitoring and emergency-response prototype designed to demonstrate how unusual health patterns can be detected, verified and escalated when a person may need assistance.

The system is intended to support people living independently, including elderly people who may not be able to request help immediately during an emergency.

The prototype demonstrates the following workflow:

1. Receive simulated health readings.
2. Analyse readings using the health-monitoring and anomaly-detection pipeline.
3. Identify unusual patterns.
4. Ask the person to confirm whether they are okay.
5. Resolve a false alarm if the person confirms they are safe.
6. Demonstrate escalation if the person does not respond.
7. Display the incident and its status to an authorised caregiver through a dashboard.

**Core principle:** Detect. Verify. Respond.

SAHYOG is a prototype, not a clinically validated medical device or emergency-dispatch service.

## 2. Problem Statement

A person living alone may experience a sudden health-related event without being able to contact a family member or caregiver.

A system that only collects readings is insufficient. It must also distinguish ordinary readings from unusual patterns, verify the person's condition where possible, and communicate the appropriate status to an authorised caregiver.

The prototype focuses on demonstrating this complete workflow rather than claiming to diagnose a medical condition.

## 3. Product Goals

The project must:

- Provide a functional Android application.
- Demonstrate health monitoring using simulated data.
- Demonstrate anomaly detection.
- Distinguish an anomaly from a confirmed emergency.
- Provide a person-verification mechanism.
- Demonstrate escalation when verification receives no response.
- Handle a false alarm when the person confirms they are okay.
- Provide a caregiver dashboard that reflects the actual backend state.
- Provide location and nearby-hospital information using available or seeded data.
- Run repeatedly without requiring the server to restart.
- Be testable on physical Android devices.
- Prepare an Android release build and Play Store submission assets.

## 4. Explicit Prototype Scope

### 4.1 Included

- Android application built with Flutter.
- Backend built with FastAPI.
- PostgreSQL database.
- Caregiver dashboard built with React, subject to the existing repository structure.
- Simulated health-reading generator.
- AI/ML or statistical anomaly-detection pipeline.
- Personalized or configurable demo baseline, where supported by the approved implementation.
- Normal, true-anomaly and false-alarm scenarios.
- Verification workflow.
- Incident lifecycle management.
- Simulated notification/escalation.
- Location handling.
- Seeded or cached hospital information.
- Dashboard incident visibility.
- Demo reset and replay.
- Local development and demonstration configuration.
- Android APK and AAB generation.

### 4.2 Explicitly Excluded from this Prototype

The following are not part of the current implementation target:

- Physical smartwatch connectivity.
- Bluetooth Low Energy implementation.
- ESP32 integration.
- MAX30102 sensor integration.
- Apple Watch integration.
- Universal support for all smartwatch brands.
- Clinical diagnosis.
- Clinical validation of anomaly thresholds.
- Guaranteed emergency-service dispatch.
- Guaranteed hospital acceptance.
- Guaranteed SMS delivery.
- Production-grade integration with hospitals.
- Advanced ML training requiring a real labelled medical dataset.
- Public production availability being guaranteed within one or two days.

The architecture may allow future smartwatch integration, but the prototype must use simulated readings.

The application must clearly label simulated data. It must never present simulated readings as actual live wearable measurements.

## 5. Target Users

### Primary user

A person living independently who may benefit from health monitoring and a way to request or trigger assistance.

### Secondary user

A family member, caregiver or authorised responder who needs to see the monitored person's status and incident information.

### Demonstration user

A hackathon evaluator who uses the three Play buttons to observe the system's behaviour.

## 6. Core Application Features

### 6.1 Monitoring

The app must show:

- Monitoring status.
- Whether readings are simulated.
- Latest available reading.
- Reading timestamp.
- Current detection status.
- Current scenario, if a demo is running.

The app must not imply that a real wearable is connected.

### 6.2 Scenario selection

The main demonstration interface must provide three clearly labelled Play buttons:

1. Normal — No emergency.
2. True Anomaly — Escalation.
3. False Alarm — Person is okay.

Each scenario must run for approximately 60 seconds.

The scenarios must use the same application pipeline. They must differ in their input data and expected outcome, not in their underlying implementation.

The app must prevent conflicting scenarios from running simultaneously.

### 6.3 Scenario A — Normal

Purpose: Demonstrate that the system does not create an emergency when readings are ordinary.

Expected behaviour:

- Generate simulated normal readings.
- Validate and process readings.
- Run the anomaly detector.
- Produce no anomaly event.
- Create no emergency incident.
- Trigger no verification countdown.
- Trigger no escalation.
- Display a normal/safe status.
- Update the dashboard to reflect normal operation.

Acceptance criteria:

- No incident is created for the run.
- No emergency notification is generated.
- The UI does not display an active emergency.
- Replaying the scenario does not create duplicate incidents.

### 6.4 Scenario B — True Anomaly

Purpose: Demonstrate sustained abnormal readings, verification and escalation.

Expected behaviour:

- Generate simulated readings containing a sustained abnormal pattern.
- Pass readings through the same validation and detection pipeline used in normal monitoring.
- Detect an anomaly.
- Create or update an incident according to the backend incident lifecycle.
- Start the verification workflow.
- Display a prompt asking the person whether they are okay.
- For this scenario, simulate no response.
- Allow the configured verification window to expire.
- Trigger the approved escalation workflow.
- Show the escalated incident in the mobile app and caregiver dashboard.

Acceptance criteria:

- The detector processes the readings rather than returning a hardcoded success.
- An anomaly event is created.
- Verification starts.
- No-response causes escalation.
- The incident appears on the dashboard.
- Notification delivery is labelled as simulated if a mock notifier is used.

### 6.5 Scenario C — False Alarm

Purpose: Demonstrate that anomaly detection does not automatically mean emergency escalation.

Expected behaviour:

- Generate simulated readings containing an unusual pattern.
- Detect the anomaly.
- Create or update the incident.
- Start verification.
- Present an "I'm okay" confirmation action.
- The user confirms that they are safe.
- The backend records the confirmation.
- Pending escalation is cancelled.
- The incident is resolved as a false alarm or equivalent approved terminal state.
- The dashboard reflects the resolved state.

Acceptance criteria:

- The anomaly is genuinely detected by the configured detector.
- Verification is initiated.
- User confirmation is accepted.
- Pending escalation is cancelled.
- No emergency escalation is sent after confirmation.
- The incident is recorded as resolved.
- The dashboard does not continue displaying an active emergency.

### 6.6 Scenario timing

Each scenario should last approximately 60 seconds.

The timing must be configurable rather than scattered as hardcoded delays across the codebase.

The true-anomaly scenario must include enough time for:

- Reading generation.
- Detection.
- Verification.
- No-response timeout.
- Escalation display.

The false-alarm scenario must allow the user to confirm they are okay during the verification window.

A scenario may finish slightly earlier or later when necessary, but the target demonstration duration is approximately one minute.

The backend must use a consistent time source and scenario-run identifier. The mobile app must not independently invent a different incident outcome.

## 7. Incident and Detection Terminology

The following concepts must remain distinct throughout the system:

**Normal:** No anomaly has been detected.

**Anomaly detected:** The reading pattern appears unusual according to the configured detector.

**Verification pending:** The person has been asked to confirm their condition.

**False alarm resolved:** The person confirmed they are okay, and pending escalation was cancelled.

**Escalated:** The configured verification workflow received no response and escalation was initiated.

**Closed/resolved:** The incident reached its approved terminal state.

An anomaly must never automatically be described as a confirmed medical emergency.

## 8. AI/ML Requirements

The health-monitoring component must:

- Validate incoming readings.
- Handle missing and stale readings.
- Consider the approved baseline and context.
- Identify unusual patterns.
- Support persistence/duration checks.
- Produce an explainable result.
- Avoid repeated duplicate anomaly events.
- Support deterministic test data.
- Provide consistent output for the backend.

The team must accurately describe the implementation.

If the detector is statistical or rule-based, do not claim that it is a trained ML model.

If an ML model is used, document the algorithm, features, training or fitting approach, limitations and evaluation.

No clinical accuracy claim is permitted.

## 9. Location and Hospital Requirements

The application should support location information according to the approved permission and data model.

It must handle:

- Permission granted.
- Permission denied.
- Location unavailable.
- Missing coordinates.
- Stale location.
- Hospital data unavailable.

The hackathon demonstration must use seeded or cached hospital information if external services are unavailable.

The application must not claim that a hospital has accepted or acknowledged an incident unless an actual integration confirms it.

## 10. Caregiver Dashboard Requirements

The dashboard must show backend-authoritative information.

It should provide:

- Monitored-person status.
- Latest available readings.
- Reading timestamps.
- Anomaly status.
- Verification status.
- Incident status.
- Incident timeline.
- Location when available.
- Nearby-hospital information when available.
- Whether a notification is real or simulated.

The dashboard must accurately reflect all three scenarios.

## 11. Reliability Requirements

The application must:

- Handle backend unavailability gracefully.
- Avoid duplicate scenario execution.
- Avoid duplicate incident creation.
- Avoid uncontrolled polling.
- Avoid infinite retries.
- Avoid unbounded in-memory buffers.
- Use timeouts for network requests.
- Handle invalid input safely.
- Support repeated scenario runs.
- Support demo reset without deleting unrelated user data.
- Provide logs sufficient for debugging without logging sensitive health information.

The core demo must not require public internet access or external paid services.

## 12. Android and Distribution Requirements

The Android app must:

- Build successfully.
- Install on a physical Android device.
- Have a stable application ID.
- Have appropriate versioning.
- Have an app icon and launch screen.
- Have correct permissions.
- Support a release build.
- Generate a signed APK for direct testing.
- Generate an Android App Bundle for Play Console preparation.

Prepare:
- Store title and description.
- Screenshots.
- Privacy policy URL.
- App icon and feature graphic.
- Data safety disclosures.
- Health-related declarations, if applicable.
- Permission declarations.
- Release signing configuration.

Do not claim public Play Store approval until the account's eligibility, testing requirements and review status are confirmed.

## 13. Non-Functional Requirements

### Performance
- The app should remain responsive during scenario execution.
- Detection must not block the UI.
- API calls must use appropriate timeouts.
- Database queries must be bounded.

### Security
- Protect user and caregiver information.
- Enforce authentication and authorization where required.
- Do not expose secrets in mobile or dashboard code.
- Do not commit credentials.

### Maintainability
- Follow role-based file ownership.
- Use shared API and data contracts.
- Avoid duplicated business logic.
- Document configuration and setup.

### Demonstrability
- The three scenarios must be repeatable.
- The demo must work with seeded data.
- The team must be able to explain which parts are real and which are simulated.

## 14. Definition of Done

The prototype is ready when:

1. The Android app builds and installs.
2. All three Play buttons work.
3. Normal produces no incident.
4. True anomaly produces detection, verification and escalation.
5. False alarm produces detection, confirmation and resolution.
6. All scenarios use the same pipeline.
7. Dashboard states match backend states.
8. Location/hospital fallback works.
9. Repeated tests do not crash the server.
10. No duplicate incidents are created by replay.
11. Simulated data and notifications are clearly labelled.
12. A release APK and AAB can be generated.
13. The team has reproducible setup and demo instructions.

**End of PRD.md**