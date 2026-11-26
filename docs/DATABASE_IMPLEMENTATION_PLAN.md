# SAHYOG — Database Implementation Plan

**Status:** Implementation plan updated for Phase 0A closeout; remaining work and unresolved contracts are identified below
**Design baseline:** `docs/DATABASE_SCHEMA_DESIGN.md` and approved `docs/PHYSICAL_DATABASE_SCHEMA.md`
**Owner:** Role 5 — Software Integration Lead + Database Engineer

This document preserves the original implementation plan and records progress against it. The physical document is the approved schema baseline. Recommendations remain recommendations and do not silently settle owner decisions or claim that proposed runtime contracts already exist.

## 1. Current repository readiness

### Confirmed repository facts

- The current branch is `Software-integration-and-database`, tracking `origin/Software-integration-and-database`.
- The original repository baseline contained `backend/pyproject.toml`, `backend/uv.lock`, and a project-metadata test. Since that historical baseline, nine SQLAlchemy ORM models and shared `Base.metadata` have been implemented in `backend/app/db/base.py` and `backend/app/models/`.
- `backend/pyproject.toml` targets Python `>=3.12,<3.13` and declares FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy `>=2.0,<2.1`, and `psycopg[binary]>=3.3,<3.4`; Alembic `>=1.20,<1.21` is in the `migrations` group; pytest and Ruff are in the `dev` group. The lockfile is present and contains the resolved baseline dependencies.
- The current tests include project metadata checks and a static check of the Alembic transaction boundary. They do not connect to PostgreSQL or test runtime application behavior.
- `.github/workflows/ci.yml` runs on pushes and pull requests using Ubuntu, Python 3.12, uv locked installation (including migrations/dev groups), Ruff lint, Ruff format check, and pytest. It has no PostgreSQL service and therefore does not exercise database migrations or constraints.
- The logical and physical schema documents are present at `docs/DATABASE_SCHEMA_DESIGN.md` and `docs/PHYSICAL_DATABASE_SCHEMA.md`; they record the approved schema design and current implementation status.

### Local database availability check

At the original readiness inspection, `psql`, a local PostgreSQL service/listener, and Docker were not detected. That finding was limited to that environment inspection. For this closeout, it is reported that the initial migration has since been applied to both `sahyog_dev` and `sahyog_test`; no database was accessed during this documentation update.

### Readiness summary

| Area | Status | Evidence / next requirement |
|---|---|---|
| Dependency baseline | Present | Manifest and lockfile declare the approved stack. No new package is needed for the proposed schema foundation. |
| PostgreSQL 16 | Migration access used (reported); current local service not rechecked | The initial revision is reported applied to `sahyog_dev` and `sahyog_test`. Confirm an isolated PostgreSQL 16 target for automated integration tests; this task did not inspect either database. |
| Alembic | Implemented | `backend/alembic.ini`, `backend/migrations/env.py`, template, README, and one initial revision exist. The online migration transaction-boundary fix is present and covered by a static ordering test. |
| SQLAlchemy engine/session | Not implemented | No bootstrap module or agreed import/settings path exists. Shubhankar owns this integration. |
| Models and schema | Implemented | Nine SQLAlchemy ORM models share `Base.metadata` and follow the approved physical schema. Runtime persistence operations remain pending. |
| Initial migration | Generated and applied (reported) | The sole initial revision creates the nine application tables; it is reported applied to `sahyog_dev` and `sahyog_test`. Each database has ten tables including `alembic_version`, owned by `sahyog_migrator`. |
| Database roles | Partially provisioned (reported) | `sahyog_app` has schema `USAGE` and no schema `CREATE`; application DML permissions remain pending. |
| Tests | Schema/constraint integration tests implemented; runtime validation environment-dependent | 27 PostgreSQL integration cases cover schema readiness, CHECK/FK constraints, idempotency uniqueness, partial uniqueness, and restrictive deletes. PostgreSQL execution is distinct from implementation; concurrency and runtime behavior tests remain future work. |
| CI database coverage | Not present | The workflow does not start PostgreSQL or run the implemented integration cases. Add an isolated PostgreSQL service and test-only settings when the CI service contract is agreed. |

## 2. MVP database scope

These classifications preserve the original recommendation for the database-backed first prototype and its three scenarios. The approved nine-table core is now implemented; implementation status is in Section 1. “Required” describes the workflow need and does not claim that runtime application behavior exists.

| Logical table/candidate | Recommended classification | Reason and scenario/workflow impact |
|---|---|---|
| `users` | Required foundation, subject to Shubhankar identity contract | Stable subject FK target for demo runs, readings, incidents, and authorization. Minimal identity fields remain unresolved; do not invent auth columns. |
| `demo_runs` | Required | Identifies scenario, subject, start/replay identity, and generation. Supports run isolation and reset for `NORMAL`, `TRUE_ANOMALY`, and `FALSE_ALARM`. |
| `health_readings` | Required | Persists simulated BPM samples through the common pipeline. `NORMAL` stores readings without an anomaly; anomaly scenarios store the same canonical reading form. |
| `anomaly_events` | Required for anomaly scenarios | Detector output is distinct from readings/incidents and is needed to create and explain anomaly-driven incidents. `NORMAL` must not produce an event. |
| `incidents` | Required for `TRUE_ANOMALY` and `FALSE_ALARM` | Backend-authoritative lifecycle record. The false-alarm path resolves after an accepted safe response; the no-response path escalates after timeout. |
| `incident_anomaly_events` | Required evidence link for anomaly-created incidents in the initial schema | Preserves one triggering association plus supporting evidence and enforces one trigger-role row per incident. The direct incident trigger pointer remains. Shubhankar must confirm runtime association validation and any future changes. |
| `verification_responses` | Required for the complete verification flow | Records person responses and supports idempotent safe confirmation. The no-response timeout and accepted response must be transactionally coordinated with incident state. |
| `escalation_attempts` | Required for the complete no-response escalation flow | Separates the timeout-triggered escalation workflow from notification provider attempts. Must not be created for a safe response that cancels pending escalation. |
| `incident_timeline_events` | Required for the initial schema's durable lifecycle history | The logical design specifies an append-only event table. Confirm runtime event vocabulary and retention with Shubhankar before writing lifecycle events or changing the schema. |
| `profiles` | Required only if profile workflow is delivered | The profile capability exists in project design, but shape and one-to-one storage choice are unresolved. Does not block scenario/incident persistence. |
| `emergency_contacts` | Required only if contact registration/recipient selection is implemented | Needed to persist contact destinations for a notification workflow; registration is not caregiver authorization. Avoid retaining full destination data unless approved. |
| `caregiver_authorizations` | Required only if caregiver access authorization is implemented | Needed to persist grants/revocations if the dashboard enforces caregiver-to-subject access. Keep grant and revocation history distinct from contact records. |
| `anomaly_readings` | Required only if detector events reference multiple reading rows | Add only if Prasiddh's event contract needs sample-level references; otherwise use a reviewed minimized summary on the anomaly event. |
| `notification_attempts` | Optional for initial persistence; required if durable attempt history is an accepted workflow requirement | The notifier can be deterministic/mock without this table. Add it when recipient/type/attempt history and retry audit are required; `SENT` means provider acceptance, not delivery. |
| `incident_location_snapshots` | Optional / workflow-dependent | Persist only if Vaishnavi confirms incident-time location snapshot needs and consent/freshness semantics. Location may remain a separately fetched service result. |
| `hospital_catalog_entries` | Optional / local fallback decision | No live provider is implied. A bundled deterministic seed/mock can avoid delaying the DB; use a table only if Vaishnavi requires persistent catalog queries. |
| Source-compatible input object | Excluded from initial persistence | Keep at the adapter boundary; raw source payload remains transient by default. Persist only after an approved concrete source/replay/privacy need. |
| Detector baseline/configuration | Excluded from initial persistence | No durable configuration contract exists. Add only on Prasiddh's explicit detector requirement. |

### Scenario coverage expected from this scope

- **`NORMAL`:** subject-owned run and simulated canonical readings; no anomaly event, incident, verification, or escalation.
- **`TRUE_ANOMALY`:** run readings → detector event → incident with triggering evidence → verification pending → timeout processing → escalation attempt and, if adopted, notification attempt; timeline records approved lifecycle events.
- **`FALSE_ALARM`:** same readings/detector/incident/verification path → accepted safe response → pending escalation cancelled → incident resolved; retries do not duplicate the response transition or timeline event.

Optional tables above do not remove their logical concepts. Their workflows must remain out of initial persistence or use an owner-approved non-database contract. Document the impact before any future migration adds them.

## 3. Unresolved decisions and recommended defaults

Recommendations below are not approvals. This table preserves the pre-implementation review: its “blocks” column describes the impact identified at that time. The physical baseline has since been approved and applied; unresolved decisions now govern runtime behavior and future schema changes unless a new approved design requires a migration.

| # | Unresolved question and implementation impact | Recommended current-prototype default (not approved) | If chosen differently | Blocks |
|---:|---|---|---|---|
| 1 | Exact persisted incident status vocabulary and allowed transitions. Affects validation, transition guards, queries, and any status CHECK/index predicate. | Store as `TEXT`; do not create PostgreSQL enum or status CHECK initially. Shubhankar approves the application vocabulary and transitions before lifecycle code. | A closed enum/check constrains future evolution; a different transition graph changes response, timeout, and dashboard behavior. | Models can use text; blocks lifecycle implementation and any status constraint/index migration until confirmed. |
| 2 | Incident reopening policy and whether one trigger may produce a later incident. Controls `uq_incidents_trigger_event`. | Treat each anomaly event as one incident episode; do not reopen/reuse an incident, and apply the proposed one-incident-per-trigger partial unique index only after Shubhankar confirms. | Reopening requires a new episode identity or changed uniqueness; premature uniqueness could reject a legitimate later incident. | Blocks trigger uniqueness migration and incident lifecycle implementation; basic entity models can be drafted. |
| 3 | Whether notification attempts require persistence and final idempotency scope. | Keep `notification_attempts` optional/out of the first core schema; use the deterministic notifier result through the approved integration boundary. Persist attempts if retry/audit needs are confirmed. | Omitting history limits replay/audit visibility; including it adds PII/retention and retry identity decisions. | Future table decision; blocks notification persistence migration only. Does not block escalation attempts. |
| 4 | Whether hospital catalog entries belong in PostgreSQL or a bundled/local seed resource. | Prefer deterministic local mock/bundled data for the prototype; no provider calls and no catalog table initially. Vaishnavi confirms. | A DB catalog requires seed ownership, update semantics, indexes, and location query contracts. | Future table decision; does not block core models/migration. |
| 5 | Exact retention/deletion/anonymization periods for health, incidents/timeline, contacts, location, notifications, and reset data. | Do not retain health data indefinitely; minimize data and keep reset separate from retention. Approve bounded periods and purge authority before storing contact/location PII or operating beyond demo review. | Longer/shorter periods change audit needs, data operations, and legal/privacy review. | Blocks operational launch/PII storage policy; does not block the core schema shape, but blocks migrations for optional sensitive fields if policy dictates a different persistence boundary. |
| 6 | Source-record ID uniqueness scope and whether a stable source ID exists. | Do not add a uniqueness constraint on `source_record_id`; use approved ingestion idempotency identity. Keep the nullable column only if Prasiddh confirms it is useful. | A source-scoped unique key needs source identity and stable semantics; incorrect uniqueness can drop distinct samples. | Does not block core models; blocks a source-ID unique index and future source-specific ingestion. |
| 7 | Exact idempotency key formats and request replay behavior for start, reading, detector, incident, verification, escalation, notification, timeline. | Use opaque identities defined by each owning contract; preserve physical scopes from the approved design and do not derive keys from timestamps/values. Keep notification attempts optional. | Changed scope/format can alter unique indexes, replay responses, client retries, and detector dedupe. | Scope decision blocks relevant unique-index migration and integrated behavior; key byte/string format itself can remain opaque to DB models. |
| 8 | Whether ordinary non-demo incidents are included in the first schema. Physical incident `demo_run_id` remains nullable for an approved runless incident without a trigger. | Recommended first prototype is demo-run-scoped, matching the three required scenarios; do not silently add a new non-null CHECK beyond the approved physical spec. Obtain explicit approval whether to retain nullable columns for future ordinary incidents or enforce demo-only at app boundary. | Supporting ordinary incidents requires reviewed runless anomaly/evidence rules and robust handling of nullable composite FKs. | Blocks final incident models and migration constraints; ordinary flow is a future extension if explicitly deferred. |
| 9 | User identity/auth fields and profile relationship. `users` is the root FK target; no auth fields are defined. | Role 5 models only the agreed stable user ID reference. Shubhankar defines whether it maps to an existing auth identity and whether `profiles` is separate (0..1) or embedded. | New auth fields/identity tables change FK targets and integrations across every subject-owned record. | Blocks user/subject model and all FK migrations until the identity anchor is agreed. |
| 10 | Canonical reading field names, time semantics, unit conversion, source vocabulary, BPM range, activity and ordinary-reading policy. | Current demo row uses simulated `heart_rate_bpm` integer, timezone-aware `observed_at` and `received_at`; accept BPM only, reject unsupported units (no silent conversion); avoid clinical thresholds. Prasiddh/Shubhankar approve exact contract. | Field/unit/name changes affect detector, ingestion, dashboard, constraints, and stored history. | Blocks reading model/migration contract and integration tests; arbitrary clinical ranges are not introduced. |
| 11 | Detector result/severity/evidence vocabulary, `anomaly_readings` need, detector version, and non-demo event support. | Persist only the minimum event fields in the physical design as text; do not add severity/result enums. Exclude `anomaly_readings` unless Prasiddh requires sample-level references. | Evidence and dedupe changes affect composite FKs/indexes and replay correctness. | Core event model needs field-name confirmation; association table is conditional; ordinary events remain future scope unless approved. |
| 12 | Demo-run status/outcome, active-run uniqueness scope, generation lifecycle, reset state, client exposure and stale-work result. | Start generation at positive value `1`; reset locks the run, increments generation and makes old work stale; replay uses a new `demo_run_id`. Status/outcome remain `TEXT` without enum/check until approved. Generation is internal unless Aditya needs it for work correlation. | Different reset/replay semantics affect run uniqueness, queued work, client retry, and timeline behavior. | `demo_runs` model/migration needs generation fields/checks; app reset/worker integration blocks on Shubhankar and Aditya confirmation. |
| 13 | Verification response vocabulary, late/duplicate response behavior, escalation lifecycle/retries, timeout identity, and notification result semantics. | Persist each accepted verification submission with incident-scoped idempotency; guard response and incident transition in one transaction. Only create escalation after processed timeout; safe response cancels pending escalation. Keep all vocabularies as text pending owner confirmation. | Different accepted/late response or retry rules change history, key scopes, and incident transitions. | Blocks lifecycle integration and related uniqueness details; base tables can be modeled with the physical fields after contract review. |
| 14 | Location capture fields/precision/access/consent/retention and hospital fallback contract. | Keep location service-owned and non-persistent unless Vaishnavi confirms a point-in-time snapshot is necessary; derive subject through incident. Use deterministic local hospital mock/catalog data. | Snapshot storage adds sensitive data; persistent catalog needs seed/query lifecycle. | Optional table decision; no core schema blocker. |
| 15 | Timeline approval, event vocabulary, minimal fields, key semantics, append-only exceptions, and retention. | Include the proposed append-only table for the first full incident history; keep `event_type` text, per-incident idempotency key, minimal details, and no update/delete during normal lifecycle. Shubhankar confirms event list and key. | Omitting or changing it alters timeline guarantees; detailed payloads increase privacy and migration cost. | Blocks timeline table migration/event writers; core incident state can be drafted. |
| 16 | UUID generation owner, timestamp clock policy, and exact Shubhankar engine/session integration point. | Recommend application-generated UUIDs (no DB extension/default) and timezone-aware UTC instants; Shubhankar owns database URL/settings/engine/session and defines the import/module point that Role 5 consumes. | DB-generated IDs or another clock change mapping/defaults and integration tests; bootstrap path changes Alembic wiring. | ID/time decisions block model/migration conventions; actual session/bootstrap agreement blocks running Alembic and integration tests. |

Historical environment blocker: earlier local checks did not detect PostgreSQL or Docker. The later migration application to development and test databases is reported in Section 1. Automated tests still require a verified isolated PostgreSQL 16 target; do not point tests at a shared, production, or unknown database.

## 4. Recommended initial schema scope and dependencies

The following table records the original recommended first-migration scope. Its nine core tables are now implemented and applied as reported in Section 1. Optional tables remain outside that initial migration; their absence does not remove their logical concepts from the design.

| Order | Table | Why/workflow | References | Essential physical guarantees | Must be confirmed before implementation |
|---:|---|---|---|---|---|
| 1 | `users` | Subject identity root for all demo and lifecycle records. | None. | UUID PK; agreed identity mapping. | Shubhankar's identity/auth anchor and UUID owner. |
| 2 | `demo_runs` | Scenario start, ownership, replay identity, reset/generation. | `users`. | Required subject; unique `(demo_run_id, subject_user_id)` FK target; positive `current_generation`; scenario check; approved start-key uniqueness. | Status/outcome labels, idempotency scope, active-run policy. |
| 3 | `health_readings` | Canonical simulated BPM path shared by all scenarios. | `users`, optionally `demo_runs`. | Subject/run composite FK; `ck_health_readings_run_generation_pair`; positive generation `ck_health_readings_generation_positive`; positive BPM; ingestion uniqueness by approved scope. | Exact reading field/time/source contract; ordinary reading/source ID policy. |
| 4 | `anomaly_events` | Detector decision for abnormal scenarios. | `users`, `demo_runs`. | Same subject/run FK; positive generation `ck_anomaly_events_generation_positive`; unique `(demo_run_id, run_generation, dedupe_key)`. | Prasiddh's result/evidence/dedupe contract; current demo-only run requirement. |
| 5 | `incidents` | Backend-authoritative incident state for true anomaly and false alarm. | `users`, optional `demo_runs`, optional trigger `anomaly_events`. | `ck_incidents_run_generation_pair`; positive generation `ck_incidents_generation_positive`; `ck_incidents_trigger_requires_run`; composite trigger FK matching event, subject, run; incident creation key uniqueness. | Demo-only vs ordinary scope, status transitions, trigger/reopen policy. |
| 6 | `incident_anomaly_events` | Trigger/supporting evidence association for anomaly-created incident. | `incidents`, `anomaly_events`. | Non-null subject/run tuple FKs; PK pair; partial unique index `uq_incident_anomaly_events_one_trigger_per_incident`; app transaction checks association equals direct trigger pointer. | Shubhankar's trigger/support role contract and transaction behavior. |
| 7 | `verification_responses` | Persist response for safe resolution/timeout workflow. | `incidents`, `users`. | Unique `(incident_id, idempotency_key)`; state guard remains application-owned. | Responder identity/authorization, accepted/late response semantics and key scope. |
| 8 | `escalation_attempts` | Record escalation only after timeout processing. | `incidents`. | Unique incident/key; unique `(escalation_attempt_id, incident_id)` target for same-incident optional notification FK. | Timeout generation identity, status/retry vocabulary. |
| 9 | `incident_timeline_events` | Durable incident history across verification/resolution/escalation. | `incidents`, optional actor `users`. | Unique `(incident_id, event_idempotency_key)`; append-only normal operation. | Shubhankar's lifecycle event list, minimal detail and retention. |

Orders 5–6 require base anomaly and incident tables before association FKs. Association may be created after both parent tables and unique target keys. Notification, contact, authorization, profile, location, anomaly-reading, and hospital tables should not delay the core schema unless the related workflow is included in the first demonstrator. `NORMAL` needs no anomaly/incident row but uses the same run/readings pipeline.

## 5. Implementation architecture

### Existing versus proposed structure

**Historical baseline:** the backend originally had only a project manifest/lock and metadata test. The current repository includes the shared database base, nine ORM models, and Alembic environment/revision. Application engine/session integration and runtime persistence are still absent.

**Current core paths and proposed extensions:**

```text
backend/
  app/
    models/                 # ORM entities and model package registration
    db/
      base.py               # shared DeclarativeBase / MetaData only
  migrations/
    env.py                  # imports model metadata and consumes agreed connection config
    versions/               # reviewed Alembic revisions
  alembic.ini               # script location/logging; no committed secret URL
  tests/
    integration/            # proposed PostgreSQL schema, migration, and constraint tests
```

An initial organization may split `models/` by bounded domain (identity, readings, incidents, operations) after model count warrants it; avoid one table per gratuitous module or parallel declarative Bases. A single `DeclarativeBase` and `MetaData` must carry all tables and naming convention. Import/registration must be explicit so Alembic autogenerate sees every approved model.

**Shubhankar-owned integration (not yet implemented):** application settings/configuration and the synchronous engine/session factory. Shubhankar selects the actual module path, application connection-setting names, pool options, and transaction dependency. Role 5's Alembic environment uses the separate `SAHYOG_MIGRATION_DATABASE_URL` contract and must not create a competing application engine/session factory.

**Shared coordination:** `backend/pyproject.toml` and `backend/uv.lock` remain shared dependency files; no dependency change is needed for this plan. If runtime/test groups or CI need changes, coordinate with Shubhankar before modifying them. Role 5 owns model/migration/schema-test files; Shubhankar owns app settings and bootstrap; tests/CI wiring must agree on connection setup.

### Configuration and database session handoff

- Use a SQLAlchemy URL with the approved Psycopg 3 synchronous dialect (`postgresql+psycopg`). Do not place credentials in source, the lockfile, workflow YAML, or Flutter/dashboard configuration.
- **Recommended environment-variable convention, not yet agreed:** `DATABASE_URL` for the local/application database and a separate disposable-test URL such as `TEST_DATABASE_URL`. Shubhankar must approve names, parsing/secret loading, and whether tests override settings. No such names or variables are implemented or present in the inspected environment.
- Application connection settings and their `.env.example` entries remain pending Shubhankar's contract. Alembic online commands separately require `SAHYOG_MIGRATION_DATABASE_URL`, supplied by the developer/deployment environment and not stored in `.env.example`.
- The application session owns each request/work unit transaction. Generation validation and run-scoped writes must use one transaction and one `demo_runs` row lock; reset and workers serialize on that row. Database helpers may expose transaction/session integration but do not own incident lifecycle decisions.
- Shubhankar owns application URL resolution through the future settings/bootstrap path. Alembic's migration-only URL remains separate; PostgreSQL tests must use an isolated test connection approved for that purpose.

## 6. Implementation sequence

The following sequence is retained from the original plan. Phases 4–8 (shared metadata, models, Alembic setup, initial revision review, and application to development/test databases) are reported complete. Remaining phases and unresolved contracts are marked by their current descriptions below.

| Phase | Deliverable and acceptance criteria | Dependencies | Expected files | Owner |
|---:|---|---|---|---|
| 1. Contract freeze | Record owner decisions from Section 3; approve table inclusion, same-subject/run FK graph, incident trigger rule, idempotency scopes, statuses, and optional workflows. No field or constraint remains ambiguously owned for chosen tables. | This plan and both design docs. | Proposed update to `docs/DATABASE_IMPLEMENTATION_PLAN.md` only if decisions require it; approved shared contract/handoff location to be agreed. | Role 5 coordinates; Shubhankar, Prasiddh, Vaishnavi, Aditya approve their contracts. |
| 2. PostgreSQL 16 availability | Confirm disposable development DB version/access and ability to create/drop an isolated test DB; no shared/production target. | Local install/approved service availability; credentials provisioned securely. | No repo file initially; later local-only settings as approved. | Role 5 with environment owner. |
| 3. Engine/session agreement | Shubhankar supplies actual settings, URL, synchronous engine/session module and transaction lifecycle; confirm the import path for Alembic/tests. | Phase 1 identity/settings decisions and phase 2 DB access. | Shubhankar-owned application config/bootstrap files; exact paths selected by Shubhankar. | Shubhankar; Role 5 integrates. |
| 4. Base/metadata — **IMPLEMENTED** | Shared `Base` and naming convention exist; all nine models register with its metadata without initializing a database connection. | Completed. | `backend/app/db/base.py`, `backend/app/models/__init__.py`. | Role 5. |
| 5. Approved models/constraints — **IMPLEMENTED** | Nine core models and approved constraints/indexes exist; no optional models were added. | Completed against the physical baseline. | `backend/app/models/*.py`. | Role 5. |
| 6. Alembic initialization — **IMPLEMENTED** | Environment imports shared metadata, uses a migration-only URL, verifies `sahyog_migrator`, and ends the verification transaction before Alembic's migration transaction. | Completed; application engine/session integration remains separate and pending. | `backend/alembic.ini`, `backend/migrations/`. | Role 5; Shubhankar owns runtime bootstrap. |
| 7. Initial migration review — **IMPLEMENTED** | The single initial revision was reviewed against the physical specification and Ruff style corrections preserve its operations. | Completed. | `backend/migrations/versions/99e748e414e3_initial_database_schema.py`. | Role 5. |
| 8. Development/test migration application — **APPLIED (reported)** | Initial migration is reported applied to `sahyog_dev` and `sahyog_test`; ten tables in each are owned by `sahyog_migrator`. No downgrade has been performed as part of this closeout. | Reported complete; not reverified by database access in this task. | No new files. | Role 5. |
| 9. PostgreSQL schema/constraint integration tests — **IMPLEMENTED** | 27 tests cover revision/table presence, scenario and generation checks, BPM validation, same-subject/run composite FKs, incident trigger/evidence integrity, idempotency uniqueness, the one-triggering-evidence partial unique index, and restrictive deletes. They use the isolated test fixtures. | Test execution requires an available, migrated `sahyog_test`; implementation does not mean the full suite has passed. Timestamp behavior and migration lifecycle remain future work. | `backend/tests/conftest.py`, `backend/tests/test_postgresql_schema.py`, `backend/tests/test_database_url_validation.py`, root `pytest.ini`. | Role 5; Shubhankar owns app-level transaction test seams. |
| 10. Reset concurrency/idempotency verification — **FUTURE** | Add two-session races for worker-first and reset-first lock order; verify stale generations cannot write after reset and retries do not duplicate persisted operations. The current 27 tests do not exercise concurrency. | Application locking implementation and idempotency contracts. | Future PostgreSQL tests under `backend/tests/`; app changes belong to Shubhankar, not Role 5. | Shubhankar implements transaction behavior; Role 5 verifies DB guarantees. |
| 11. CI and handoff | Add an isolated PostgreSQL 16 service and safe test settings so CI can run the implemented integration cases; record owner handoffs/readiness. | Agreed CI service configuration and verified database test execution. | `.github/workflows/ci.yml` (Role 5, coordinated); individual handoff files owned by each teammate; shared `HandOff.md` remains Utkarsh-owned. | Role 5 coordinates; Shubhankar reviews integration. |

## 7. PostgreSQL development and testing strategy

### Local development

- Use PostgreSQL 16 via an approved local Windows installation or an explicitly approved isolated development service. Current inspection found no conventional local installation/service/listener or Docker command; availability must be confirmed before work requiring a connection.
- Create a dedicated developer database and a separate disposable test database; never run schema reset/downgrade tests against a shared or production database. Development data should be synthetic and clearly simulated.
- Connection variables and `.env` loading are Shubhankar-owned. Recommended but unapproved names are in Section 5. Use local-only secrets, restrict file permissions, exclude `.env` and dumps from Git, and never print full URLs in logs or reports.
- Psycopg 3 binary is already in the runtime manifest; no second driver or additional dependency is recommended.

### Disposable tests and migrations

- Provision an isolated PostgreSQL 16 database/schema per test run with a dedicated test credential. Explicitly verify the target database name/environment before destructive cleanup. A test may use transaction rollback for ordinary cases, but migration and multi-session lock tests need independent connections and a disposable database lifecycle.
- Run Alembic upgrade on a clean database, inspect FK/unique/check/index definitions (including partial-index predicates), run positive and negative constraint cases, downgrade to base, and re-upgrade a fresh database. Do not use SQLite as evidence for PostgreSQL composite FK, partial unique, locking, or timezone behavior.
- Integration tests must not use actual notification providers or credentials. Mock notifier and location/hospital gateways; use no external personal data.

### CI implications

- Existing CI does not start PostgreSQL. The current pytest suite includes metadata checks and a static transaction-boundary check, but no PostgreSQL integration coverage. Once database-backed tests are added, use an isolated PostgreSQL 16 service with health checks and job-local test credentials; do not use developer, shared, production, or provider credentials.
- Keep `uv sync --locked --group migrations --group dev`, Ruff checks, and pytest; add migration/integration commands only when real tests exist. Do not claim CI database readiness before the GitHub workflow runs successfully with the service.
- If GitHub-hosted service containers are unavailable in the project environment, identify an approved isolated alternative rather than falling back to a shared DB.

## 8. Integration contracts and handoffs

These are proposed handoff specifications for review, not contracts already approved or implemented.

### Shubhankar — backend/session/lifecycle

- Select and implement the single synchronous engine/session bootstrap and configuration path; provide Role 5 its import and transaction integration point.
- Define per-request/work-unit transaction boundaries. A worker must lock the `demo_runs` row (`SELECT ... FOR UPDATE` or reviewed equivalent), compare captured generation/status, and perform child writes in that same transaction. Reset must acquire the same row lock, invalidate pending work and increment generation atomically. This intentionally serializes same-run workers for current prototype correctness.
- In one transaction, validate `incident_anomaly_events` trigger row matches `incidents.triggering_anomaly_event_id`; authorize subject/run; enforce status transitions; make verification response and state transition idempotent; create escalation only after timeout.
- Confirm status vocabularies and retry/stale-work outcomes before lifecycle implementation. Role 5 owns database constraints but not those application rules.

### Prasiddh — reading/detector persistence

- Confirm canonical reading names/types/units/timestamps/provenance: recommended prototype fields are `subject_user_id`, `demo_run_id`, `run_generation`, `source_kind=SIMULATED`, `heart_rate_bpm`, `observed_at`, and backend `received_at`.
- Specify validation of BPM values (without clinical claims), support/rejection of other units (no implicit conversion), activity/source values, out-of-order handling, and whether stable `source_record_id` exists.
- Confirm anomaly event identity/result/explanation/severity, detector evidence window, `dedupe_key` scope `(demo_run_id, run_generation, ...)`, and whether a compact summary or `anomaly_readings` table is needed. Role 5 maps only the reviewed contract.

### Vaishnavi — dashboard/location/hospital

- Identify which canonical reading/anomaly/incident fields the dashboard needs and whether dashboard access requires persisted caregiver authorization.
- Define location consent/freshness/capture-time and response shape; confirm whether `incident_location_snapshots` is needed or location remains fetched.
- Recommend whether nearby-hospital fallback is deterministic local data or a persistent `hospital_catalog_entries` table. No live provider integration or acceptance/availability schema is implied.

### Aditya — mobile/demo

- Confirm scenario and subject/run identity from demo start through reading ingestion, verification, reset and replay; generation is a work version, not a new run ID.
- Specify client retry/idempotency identity availability and when a repeated start should return the existing run versus create a new one. Agree reset response and stale-work user behavior with Shubhankar.
- Preserve visible simulated-data labels; display backend-authoritative incident outcome. Mobile does not independently finalize incident state.

## 9. Blockers and implementation authorization checklist

### Historical pre-model gates (still relevant to runtime behavior and extensions)

- Shubhankar's subject/user identity FK target and how it maps to auth identity.
- First-schema scope for ordinary non-demo incidents and runless reading/anomaly paths; do not infer behavior from nullable columns.
- Canonical reading and detector-event field contracts with Prasiddh/Shubhankar, including event evidence choice and key scopes.
- Incident status/state transitions, trigger/support association semantics, reopen policy, verification acceptance/late response, and escalation timeout identity with Shubhankar (and Aditya for client behavior).
- Demo-run subject, generation and reset transaction contract; one shared run-row lock and transaction boundaries.
- Table inclusion for timeline, contact/authorization access workflows, notification attempt history, location snapshots, and hospital catalog.
- UUID generation and timestamp ownership/import conventions sufficient to define `Base`, models, and FK targets.

### Gates for future schema changes and runtime integration

- The initial table/constraint/index set is implemented and applied as recorded in the physical schema document. Any change to that set requires an approved follow-up migration.
- Ordinary incident policy, application lifecycle behavior, idempotency response semantics, and any change to incident trigger/reopen behavior remain unresolved.
- Runtime database operations and DML grants require Shubhankar's engine/session and application permission integration; do not use the bootstrap or migration role for runtime work.
- PostgreSQL integration tests require an isolated test target. Do not use shared or production databases.
- Retention/deletion policy for personal/health/location/contact data remains unresolved; exact periods must be approved before enabling additional stored data, and health data must not be retained indefinitely.
- The existing Alembic metadata registration and downgrade ordering are implemented; future revisions must preserve them and be reviewed before application.

### Can remain open for a later extension

- `profiles`, contact and caregiver tables if their workflows are explicitly out of initial demo scope.
- `anomaly_readings` if detector returns a sufficient compact summary.
- Notification-attempt persistence if mock delivery history is not a current product requirement.
- Hospital catalog table and location snapshots if deterministic mock/fetched-service behavior suffices.
- Source record uniqueness, ordinary non-demo monitoring, new health metrics, detector baselines, device/provider integrations, and raw payload storage.
- Final retention durations for excluded optional tables; health and PII must still have an approved bounded policy before their storage is enabled.

### Role 5 can complete independently after the decisions above

- Extend PostgreSQL integration coverage for timestamps, migration lifecycle, and concurrency, and coordinate CI service setup.
- Maintain schema/index names, migration ordering, database infrastructure notes, and teammate handoffs without changing app-owned lifecycle/configuration.

### Requires Shubhankar's actual integration

- Application settings, engine/session creation, and application database URL/environment configuration; the existing Alembic environment uses a separate migration URL.
- Application transaction and reset/worker generation locking, authorization, trigger-association validation, lifecycle/state/idempotency responses.
- Test fixtures that exercise application transaction behavior. Role 5 can supply DB test cases but cannot substitute for the app seam.

### Recommended next implementation task

Coordinate with Shubhankar on the application engine/session integration and application connection settings, then implement runtime persistence and application DML grants against the existing schema. Add the remaining PostgreSQL migration-lifecycle, timestamp, and generation-reset concurrency tests, and update CI when a safe test service is agreed. Preserve the unresolved contracts in Section 3 for future runtime behavior and schema extensions; do not recreate the models or initial migration.
