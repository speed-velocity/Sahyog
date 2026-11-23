# SAHYOG — Instructions for AI Coding Agents

**Project:** SAHYOG — Detect. Verify. Respond.  
**Document:** AGENTS.md  
**Version:** 1.0  
**Applies to:** Codex, Antigravity and all AI coding agents

---

## 1. Your Role

You are an implementation assistant working inside the SAHYOG repository.

You are not the product owner.

You must follow the approved project requirements, system architecture, team ownership and handoff instructions.

Your job is to implement the assigned task accurately, test it and report the actual result.

You must not independently redesign SAHYOG.

## 2. Mandatory Reading Order

Before changing code, read:

1. `PRD.md`
2. `SYSTEM_DESIGN.md`
3. `TEAM.md`
4. `HANDOFF.md`
5. `AGENTS.md`
6. Your assigned `handoff/<your-name>.md`

Then inspect the actual repository.

Do not assume that the repository matches the documents. Verify it.

If the repository and documentation disagree, report the exact conflict to the responsible human teammate.

Do not silently overwrite existing implementation or documentation.

## 3. Project Scope

SAHYOG is currently a simulated health-monitoring and emergency-response prototype.

The first deliverable is an Android application with three approximately 60-second demo scenarios:

- `NORMAL`
- `TRUE_ANOMALY`
- `FALSE_ALARM`

The three scenarios must use the same pipeline.

The prototype does not implement actual smartwatch connectivity.

Do not introduce:

- Bluetooth connectivity.
- ESP32.
- MAX30102.
- Apple Watch SDK.
- Unapproved wearable integrations.
- Unapproved cloud services.
- Unnecessary ML infrastructure.
- Unrequested features.

A future integration-ready interface is acceptable where assigned, but simulated data must be clearly labelled.

## 4. Source-of-Truth Rules

Use this priority:

1. `PRD.md` — product behaviour and scope.
2. `SYSTEM_DESIGN.md` — architecture and technical contracts.
3. `TEAM.md` — file ownership and responsibilities.
4. `HANDOFF.md` — shared progress and integration decisions.
5. Individual handoff — current task and progress.
6. Existing code — actual implementation.

If two sources conflict, do not guess.

Report:

- The two conflicting statements.
- The files and sections involved.
- The implementation affected.
- The smallest decision needed to proceed.

Wait for approval when the conflict affects architecture, data contracts, API behaviour or ownership.

## 5. Task Discipline

You must only work on the task assigned to your role.

Before implementation, produce a short plan:

1. Task ID.
2. Required behaviour.
3. Files to inspect.
4. Files you may modify.
5. Interfaces you will consume.
6. Interfaces you will expose.
7. Dependencies.
8. Tests required.
9. Risks and blockers.

Do not start unrelated tasks.

Do not add "helpful" features that are outside the assigned scope.

Do not modify another teammate's owned files without permission.

## 6. Repository Inspection

Before editing:

- Inspect the current directory structure.
- Inspect relevant existing classes and functions.
- Inspect dependency versions.
- Inspect existing tests.
- Inspect configuration.
- Inspect current Git branch and working-tree status.

Never assume a file is empty because you have not read it.

Never replace a working file with a fresh implementation without checking its contents.

Never delete unrelated code.

Do not generate an entirely new project inside an existing project directory.

## 7. API and Interface Rules

- Use the exact approved API routes.
- Use the exact approved request and response fields.
- Use the exact approved status vocabulary.
- Use the agreed timestamp format.
- Use the agreed units.
- Use the agreed identifier relationships.
- Use the agreed error structure.

Do not invent endpoint paths.

Do not rename shared fields.

Do not create duplicate services.

Do not hardcode API URLs in multiple locations.

Do not make a mobile-only decision that contradicts backend incident state.

If an interface is missing, request approval before creating it.

## 8. Three Scenario Rules

The three scenarios must use the same application pipeline.

### NORMAL

- Simulated normal readings.
- No anomaly event.
- No incident.
- No verification.
- No escalation.

### TRUE_ANOMALY

- Sustained simulated abnormal readings.
- Anomaly detection.
- Incident creation.
- Verification.
- No-response timeout.
- Escalation.
- Dashboard update.

### FALSE_ALARM

- Simulated abnormal readings.
- Anomaly detection.
- Incident creation.
- Verification.
- Person confirms they are okay.
- Pending escalation cancelled.
- Incident resolved.
- Dashboard update.

Never hardcode the final result while bypassing the detector, backend or incident service.

Never confuse anomaly detection with confirmed emergency escalation.

## 9. Coding Standards

- Follow the existing language and framework conventions.
- Prefer simple and maintainable code.
- Reuse existing approved dependencies.
- Avoid unnecessary libraries.
- Use clear names.
- Keep functions focused.
- Validate external inputs.
- Handle exceptions.
- Avoid silent failures.
- Avoid duplicated business logic.
- Avoid large unrelated refactors.
- Avoid premature abstractions.
- Add comments where they explain important decisions, not obvious syntax.

Do not optimise code that has not been measured to be a problem.

Do not add complexity to make the implementation appear more advanced.

## 10. Server Stability Rules

The backend must support repeated demonstrations.

Never introduce:

- Infinite loops without controlled termination.
- Infinite retries.
- Unbounded queues.
- Unbounded in-memory reading buffers.
- Uncontrolled polling.
- Duplicate background jobs.
- A worker per reading.
- Unbounded database queries.
- Uncontrolled WebSocket reconnections.
- Unnecessary writes on every dashboard refresh.

Use:

- Request timeouts.
- Bounded concurrency.
- Bounded connection pools.
- Pagination or limits.
- Duplicate protection.
- Safe task cancellation.
- Resource cleanup.
- Clear error handling.

Do not perform destructive database operations.

Do not run load tests against a shared or public server without explicit approval.

## 11. Security Rules

- Never commit passwords.
- Never commit API keys.
- Never commit signing keys.
- Never put backend secrets inside Flutter or React code.
- Do not expose database credentials to the client.
- Do not log personal health information unnecessarily.
- Do not weaken authentication to make a demo work.
- Do not bypass authorisation checks.
- Do not expose location data to unauthorised users.

Use environment variables and the approved configuration strategy.

## 12. Testing Rules

A task is not complete just because code generation succeeded.

Run the appropriate tests.

Depending on the task, perform:

- Unit tests.
- Integration tests.
- Static analysis.
- Formatting.
- Build checks.
- API validation.
- Database migration checks.
- Android build checks.
- Dashboard build checks.

If a test cannot run:

- State why.
- Show the command attempted.
- Report the exact failure.
- Do not claim that the test passed.

Never delete a failing test just to make the test suite green.

## 13. Dependency Rules

Before adding a dependency:

1. Check whether an existing dependency already provides the functionality.
2. Check whether the dependency is necessary for the assigned task.
3. Check compatibility with the existing framework version.
4. Consider whether it works in the offline demonstration environment.
5. Explain the reason for adding it.

Do not add large AI frameworks, model-serving systems, cloud services or UI libraries without approval.

## 14. Git Rules

- Work only on your assigned branch.
- Check the working tree before editing.
- Do not discard another person's uncommitted changes.
- Do not force-push shared branches.
- Do not commit secrets.
- Commit small logical changes.
- Use meaningful commit messages.
- Do not merge directly into the integration branch unless authorised by Utkarsh.

Before committing, inspect the diff.

## 15. Handoff Rules

At the end of each task, update your individual handoff file.

Include:

- Task ID.
- Status.
- Summary.
- Files changed.
- Interfaces changed or created.
- Commands executed.
- Tests executed and results.
- Commit ID.
- Known issues.
- Next action.
- Dependencies on other teammates.

Do not update another person's handoff.

Only Utkarsh updates the shared `HANDOFF.md`.

## 16. Stop Conditions

Stop and ask the responsible teammate when:

- The task requires changing a shared API contract.
- The task requires changing a database model owned by another teammate.
- The task requires editing another person's owned files.
- The source documents conflict.
- An endpoint is missing.
- A required field is undefined.
- A dependency is unavailable.
- A test reveals a cross-component failure.
- A proposed implementation would expand the approved scope.
- The existing architecture cannot support the task without a decision.

Do not make up a solution and continue silently.

## 17. Required Final Report

At the end of your work, report:

1. Task completed.
2. Exact files changed.
3. Exact behaviour implemented.
4. Interfaces consumed.
5. Interfaces exposed.
6. Tests run.
7. Test results.
8. Build results.
9. Known limitations.
10. Remaining work.
11. Commit ID.
12. What the next teammate must do.

Use accurate status labels:

- `NOT_STARTED`
- `IN_PROGRESS`
- `BLOCKED`
- `IMPLEMENTED`
- `TESTED`
- `INTEGRATED`

Do not use `DONE` when the implementation has not been tested and integrated.

## 18. Final Rule

Your success is measured by whether your assigned component works correctly with the other four components.

A large amount of generated code is not success.

A clean, tested, integrated implementation is success.

**Do not hallucinate. Do not expand scope. Do not silently change contracts. Do not claim tests passed when they did not.**

**End of AGENTS.md**