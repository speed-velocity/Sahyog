# SAHYOG — Physical Database Schema Specification

**Status:** Approved physical schema baseline; implementation status updated for Phase 0A closeout
**Baseline:** `docs/DATABASE_SCHEMA_DESIGN.md`
**Scope:** PostgreSQL table, constraint, index, ORM, migration, concurrency, and test design

> This file translates the logical proposal into the approved PostgreSQL schema baseline. The nine ORM models and initial Alembic migration implement this baseline. API contracts, application engine/session integration, runtime persistence, and application-level database operations remain outside this document and are not claimed to be implemented. Any item still marked proposed or unresolved remains subject to its stated owner review.

## 1. Scope and assumptions

### Repository facts

- **CONFIRMED:** The active branch is `Software-integration-and-database`, tracking `origin/Software-integration-and-database`.
- **CONFIRMED:** `backend/pyproject.toml` declares Python `>=3.12,<3.13`, package name `sahyog-backend`, version `0.1.0`, and `package = false`; the backend source package exists and is run from the workspace rather than installed as a wheel.
- **CONFIRMED:** The manifest declares FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy `>=2.0,<2.1`, Psycopg 3 binary `>=3.3,<3.4`, Alembic `>=1.20,<1.21` in the migrations group, and pytest/Ruff in the dev group. `backend/uv.lock` exists.
- **CONFIRMED:** Nine SQLAlchemy ORM models are registered with the shared `Base.metadata`. Alembic configuration and environment, a migration README/template, and one initial revision exist. The transaction-boundary fix explicitly rolls back the role-verification SELECT transaction before Alembic opens its migration transaction.
- **CONFIRMED (reported for this closeout):** The initial migration has been applied to `sahyog_dev` and `sahyog_test`. Each database has ten tables owned by `sahyog_migrator` (the nine application tables plus Alembic's version table). `sahyog_app` has schema `USAGE` and does not have schema `CREATE`.
- **Provisioning procedure:** Fresh-volume setup and non-destructive existing-volume role instructions are documented in `docs/DATABASE_ROLE_PROVISIONING.md`.
- **CONFIRMED:** Application engine/session integration, runtime persistence, and application-level database DML permission provisioning remain pending. The CI workflow runs locked Ruff and pytest checks but does not provide a PostgreSQL service.
- **HISTORICAL:** Earlier repository inspections preceded the ORM models and Alembic implementation; their descriptions of a backend without models or migrations no longer describe the current repository.

### Proposed physical-design assumptions

- **PROPOSED:** PostgreSQL 16 is the target database; access is synchronous SQLAlchemy 2.x through Psycopg 3. Alembic will own schema changes.
- **PROPOSED:** UUID primary keys, `TIMESTAMPTZ` instants, and normalized UTC values follow the logical design. UUID generation location (application versus database) remains unresolved; no server default is assumed here.
- **PROPOSED:** Current prototype readings are simulated heart-rate values in BPM. No wearable, BLE, provider-specific integration, clinical diagnosis, or raw source-payload persistence is included.
- **HISTORICAL:** Before this physical baseline was approved, the logical design alone was not a migration-ready contract. The nine core tables are now implemented; optional tables, runtime vocabularies, retention policy, and owner contracts that remain unresolved require approval before they are added or used by application behavior.
- **PROPOSED:** A SQLAlchemy `MetaData` naming convention is used for generated constraints; explicit names below take precedence. This document supplies deterministic names to simplify Alembic review and downgrade.

The physical type mapping below is the implemented baseline for the nine core tables; optional candidates and items still marked proposed remain outside the initial schema. “No server default” means the application must supply the value or a later approved migration must define a default. Do not use database defaults to invent product behavior.

## 2. Table-by-table specification

### 2.1 Shared physical conventions

| Concern | Proposed mapping |
|---|---|
| IDs | PostgreSQL `UUID`; SQLAlchemy `Uuid(as_uuid=True)`. Choose application UUID generation only after owner approval; no `gen_random_uuid()` default assumed. |
| Instants | PostgreSQL `TIMESTAMP WITH TIME ZONE` (`TIMESTAMPTZ`); SQLAlchemy `DateTime(timezone=True)`. Application supplies timezone-aware UTC values. |
| Text vocabularies | `TEXT` with application validation. Do not create PostgreSQL enum types until each vocabulary is approved. A `CHECK` for a closed list is also deferred until approved. |
| Optional structured detail | No `JSONB` in the baseline tables. If an approved, minimized detail payload is later needed, define its shape, size, privacy, query purpose, and retention first. |
| Foreign-key deletion | `ON DELETE RESTRICT` (PostgreSQL default behavior) for durable subject, incident, and evidence references unless a row-specific exception is explicitly approved. No broad cascades. `ON UPDATE NO ACTION`; primary identifiers are immutable. |
| Timestamp defaults | No server `now()` defaults are assumed; service-owned times are supplied by the application. Created/updated timestamp policy and database-vs-application clock are unresolved. |
| Nullable idempotency key | Where specified as nullable, a unique constraint permits multiple nulls in PostgreSQL. Partial unique indexes can make this intent explicit and avoid index entries for absent keys. |

Section 4 is the authoritative complete index inventory for every table below, including indexes created implicitly by primary-key and unique constraints. Each table's constraint and index notes refer to that inventory; do not add or omit an index without updating both the table specification and Section 4.

### 2.2 Required and optional tables

The nine core tables in the approved physical schema are implemented by the ORM and initial migration. Decision labels in the table descriptions preserve the original design provenance; they do not mean the implemented core schema is awaiting approval. Optional tables remain candidates and must not be added unless their persistence need is accepted.

#### `users` — required identity anchor (fields unresolved)

Purpose: referenced identity for monitored subjects, contacts, caregiver authorization, actors, and records. Shubhankar owns the identity/auth contract.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `user_id` | `UUID` | No | PK; no server default proposed. |
| `created_at` | `TIMESTAMPTZ` | No | No server default proposed; policy unresolved. |
| `updated_at` | `TIMESTAMPTZ` | No | No server default proposed; policy unresolved. |

Constraints: `CONSTRAINT pk_users PRIMARY KEY (user_id)`. No email/phone columns, uniqueness, or auth fields are specified before the owner contract. Indexes: PK only. Delete/update: referenced rows restrict user deletion; ID updates are not supported. Current prototype: identity anchor required if database-backed user ownership is adopted; exact integration is unresolved.

#### `profiles` — optional, zero-or-one profile per user

Purpose: optional profile attributes whose shape is not defined in the repository contracts.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `user_id` | `UUID` | No | PK and FK to `users.user_id`; no default. |
| Approved profile fields | Owner-selected types | Per contract | None defined. |

Constraints: `pk_profiles`; `fk_profiles_user_id` references `users(user_id) ON DELETE RESTRICT ON UPDATE NO ACTION`. Indexes: PK/FK is the same index; no redundant FK index proposed. Delete/update: profile deletion is explicit; never cascades to user. Current prototype: optional. Profile attributes and whether this table exists are unresolved.

#### `emergency_contacts` — optional until contact workflow is approved

Purpose: contact registration, separate from caregiver authorization.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `contact_id` | `UUID` | No | PK; no default. |
| `subject_user_id` | `UUID` | No | FK to `users.user_id`. |
| `display_name` | `TEXT` | No | None. |
| `destination_value` | `TEXT` | No | PII; no default. |
| `destination_kind` | `TEXT` | No | Vocabulary unresolved. |
| `relationship_label` | `TEXT` | Yes | None. |
| `created_at` | `TIMESTAMPTZ` | No | No server default. |
| `updated_at` | `TIMESTAMPTZ` | No | No server default. |
| `removed_at` | `TIMESTAMPTZ` | Yes | Null while active; removal semantics proposed. |

Constraints: `pk_emergency_contacts`; `fk_emergency_contacts_subject_user_id` → user, restrictive delete; proposed `ck_emergency_contacts_nonempty_destination` checks destination fields are non-empty after the approved normalization rule. No global destination uniqueness. Indexes: `ix_emergency_contacts_subject_removed (subject_user_id, removed_at)` supports active-contact listing. No server defaults. Removal is soft deactivation for new sends; PII erasure is a separate retention action. Current prototype: optional/pending contact workflow approval.

#### `caregiver_authorizations` — optional authorization history

Purpose: preserve caregiver grant and revocation facts; never derive access from contact registration.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `authorization_id` | `UUID` | No | PK; no default. |
| `subject_user_id` | `UUID` | No | FK to user. |
| `caregiver_user_id` | `UUID` | No | FK to user. |
| `consent_evidence_reference` | `TEXT` | Yes | No raw consent payload by default. |
| `granted_at` | `TIMESTAMPTZ` | No | No server default. |
| `revoked_at` | `TIMESTAMPTZ` | Yes | Null while grant is current. |
| `revoked_by_user_id` | `UUID` | Yes | FK to user when present. |

Constraints: `pk_caregiver_authorizations`; restrictive FKs `fk_caregiver_authorizations_subject_user_id` → `users(user_id)`, `fk_caregiver_authorizations_caregiver_user_id` → `users(user_id)`, and `fk_caregiver_authorizations_revoked_by_user_id` → `users(user_id)`. No extra CHECK couples revocation time to actor because system-initiated revocation semantics are unresolved. Index: `uq_caregiver_authorizations_active_pair` unique partial on `(subject_user_id, caregiver_user_id) WHERE revoked_at IS NULL`. No defaults. Revocation facts are preserved; a re-grant is a new row. Current prototype: optional pending consent/auth contract.

#### `demo_runs` — required for three-scenario demo isolation

Purpose: identify a scenario execution and its owning subject. A reset does not reuse a run ID for replay.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `demo_run_id` | `UUID` | No | PK; no default. |
| `subject_user_id` | `UUID` | No | FK to user. |
| `scenario` | `TEXT` | No | Values proposed: `NORMAL`, `TRUE_ANOMALY`, `FALSE_ALARM`; no enum/default. |
| `status` | `TEXT` | No | Vocabulary unresolved; no default. |
| `outcome` | `TEXT` | Yes | Separate from execution status; vocabulary unresolved. |
| `current_generation` | `BIGINT` | No | Must be supplied; proposed check `> 0`; no default assumed. |
| `start_idempotency_key` | `TEXT` | Yes | Format unresolved. |
| `started_at` | `TIMESTAMPTZ` | No | No server default. |
| `completed_at` | `TIMESTAMPTZ` | Yes | None. |
| `reset_at` | `TIMESTAMPTZ` | Yes | None. |

Constraints: `pk_demo_runs`; `fk_demo_runs_subject_user_id` → user; `uq_demo_runs_id_subject (demo_run_id, subject_user_id)` is a required composite-FK target; `ck_demo_runs_generation_positive`; `ck_demo_runs_scenario` limits values to the three approved scenario identifiers; proposed partial unique `uq_demo_runs_subject_start_key` on `(subject_user_id, start_idempotency_key) WHERE start_idempotency_key IS NOT NULL`. Proposed partial unique active-run-per-subject index is deferred until run statuses and concurrency semantics are confirmed. No defaults. Delete/update: restrictive subject reference; no cascade into child records. Current prototype: required.

#### `health_readings` — required canonical simulated BPM readings

Purpose: normalized samples for detection, traceability, and approved dashboard summaries. Raw source payloads are not stored by default.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `reading_id` | `UUID` | No | PK; no default. |
| `subject_user_id` | `UUID` | No | FK to user; composite run target. |
| `demo_run_id` | `UUID` | Yes for ordinary flow; required on demo readings | FK to run when present. |
| `run_generation` | `BIGINT` | Yes iff `demo_run_id` is null | Snapshot of generation captured when work was scheduled. |
| `source_kind` | `TEXT` | No | Current demo value `SIMULATED`; broader vocabulary unresolved. |
| `heart_rate_bpm` | `INTEGER` | No | Canonical BPM; positive check proposed. |
| `observed_at` | `TIMESTAMPTZ` | No | Source/measurement time. |
| `received_at` | `TIMESTAMPTZ` | No | Backend receipt time. |
| `activity_context` | `TEXT` | Yes | Vocabulary unresolved. |
| `source_record_id` | `TEXT` | Yes | Uniqueness scope unresolved; no unique constraint proposed. |
| `ingestion_idempotency_key` | `TEXT` | Yes | Exact key contract unresolved. |

Constraints: `pk_health_readings`; `fk_health_readings_subject_user_id`; `uq_health_readings_id_subject_run (reading_id, subject_user_id, demo_run_id)` for evidence FKs; `fk_health_readings_run_subject (demo_run_id, subject_user_id)` → `demo_runs(demo_run_id, subject_user_id)`; `ck_health_readings_run_generation_pair` requires both run and generation null or both non-null; `ck_health_readings_generation_positive` checks `run_generation IS NULL OR run_generation > 0`; `ck_health_readings_bpm_positive` checks `heart_rate_bpm > 0`; unique partial `uq_health_readings_subject_ingestion_key (subject_user_id, ingestion_idempotency_key) WHERE ingestion_idempotency_key IS NOT NULL`. Query indexes: `ix_health_readings_subject_observed`, `ix_health_readings_run_observed` (Section 4). Do not add an arbitrary clinical range. No defaults. Restrictive FKs; demo reset invalidates work but is not a reading-delete policy. Current prototype: required.

#### `anomaly_events` — required detector output for demo scenarios

Purpose: preserve a detector event distinct from its input readings and any incident. The detector contract remains owned by Prasiddh.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `anomaly_event_id` | `UUID` | No | PK; no default. |
| `subject_user_id` | `UUID` | No | FK to user. |
| `demo_run_id` | `UUID` | No for current prototype | FK to run. |
| `run_generation` | `BIGINT` | No | Captured generation snapshot. |
| `detected_at` | `TIMESTAMPTZ` | No | Detector decision time. |
| `detector_result` | `TEXT` | No | Vocabulary unresolved; no enum/default. |
| `severity` | `TEXT` | Yes | Only if detector contract defines it. |
| `explanation` | `TEXT` | Yes | Minimized, non-diagnostic explanation. |
| `detector_version` | `TEXT` | Yes | Stable version only if supplied. |
| `dedupe_key` | `TEXT` | No | Identity semantics defined by detector contract; format unresolved. |

Constraints: `pk_anomaly_events`; `fk_anomaly_events_subject_user_id`; `uq_anomaly_events_id_subject_run (anomaly_event_id, subject_user_id, demo_run_id)`; `fk_anomaly_events_run_subject` → demo run; `ck_anomaly_events_generation_positive` checks `run_generation > 0`; unique `uq_anomaly_events_run_generation_dedupe (demo_run_id, run_generation, dedupe_key)`. Query indexes: `ix_anomaly_events_subject_detected`, `ix_anomaly_events_run_generation_detected` (Section 4). No defaults. Restrictive references. Generation equality with current run generation is application transaction logic, not an FK. Current prototype: required for anomaly scenarios; `NORMAL` produces no anomaly event. Ordinary non-demo anomaly support remains unresolved.

#### `anomaly_readings` — optional evidence association

Purpose: connect a detector event with multiple canonical readings when the approved event contract requires sample references; omit if a minimized summary is sufficient.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `anomaly_event_id` | `UUID` | No | Part of PK and composite FK. |
| `reading_id` | `UUID` | No | Part of PK and composite FK. |
| `subject_user_id` | `UUID` | No | Composite integrity discriminator. |
| `demo_run_id` | `UUID` | No | Same-run discriminator for current prototype evidence. |

Constraints: `pk_anomaly_readings (anomaly_event_id, reading_id)`; `fk_anomaly_readings_event_subject_run` → `anomaly_events(anomaly_event_id, subject_user_id, demo_run_id)`; `fk_anomaly_readings_reading_subject_run` → `health_readings(reading_id, subject_user_id, demo_run_id)`. No defaults or cascading deletes. Index `ix_anomaly_readings_reading_event (reading_id, anomaly_event_id)` supports reverse lookup. Current prototype: optional.

#### `incidents` — required authoritative incident lifecycle record

Purpose: represent backend-authoritative response lifecycle. It keeps one nullable direct triggering-event reference; if that reference exists in the current prototype, the incident must be run-scoped.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `incident_id` | `UUID` | No | PK; no default. |
| `subject_user_id` | `UUID` | No | FK to user. |
| `demo_run_id` | `UUID` | Yes only for an approved runless incident with no trigger | FK to run. |
| `run_generation` | `BIGINT` | Yes iff `demo_run_id` is null | Snapshot when incident work was scheduled/created. |
| `triggering_anomaly_event_id` | `UUID` | Yes | Nullable direct trigger pointer; paired integrity below. |
| `status` | `TEXT` | No | Incident vocabulary unresolved; no enum/default. |
| `creation_idempotency_key` | `TEXT` | Yes | Format unresolved. |
| `created_at` | `TIMESTAMPTZ` | No | No server default. |
| `updated_at` | `TIMESTAMPTZ` | No | No server default. |
| `verification_deadline_at` | `TIMESTAMPTZ` | Yes | Set by approved lifecycle behavior. |
| `resolved_at` | `TIMESTAMPTZ` | Yes | Set by approved lifecycle behavior. |
| Approved resolution detail | `TEXT` or approved minimized form | Yes | No clinical interpretation; exact field unresolved. |

Constraints: `pk_incidents`; `fk_incidents_subject_user_id`; `uq_incidents_id_subject_run (incident_id, subject_user_id, demo_run_id)` as composite-FK target; `fk_incidents_run_subject (demo_run_id, subject_user_id)` → run; `ck_incidents_run_generation_pair` requires run/generation both null or both present; `ck_incidents_generation_positive` checks `run_generation IS NULL OR run_generation > 0`; **`ck_incidents_trigger_requires_run CHECK (triggering_anomaly_event_id IS NULL OR demo_run_id IS NOT NULL)`**; `fk_incidents_trigger_subject_run (triggering_anomaly_event_id, subject_user_id, demo_run_id)` → `anomaly_events(anomaly_event_id, subject_user_id, demo_run_id)`; unique partial `uq_incidents_subject_creation_key (subject_user_id, creation_idempotency_key) WHERE creation_idempotency_key IS NOT NULL`. If confirmed, `uq_incidents_trigger_event` is a unique partial index on non-null `triggering_anomaly_event_id`; defer pending reopen policy. Query indexes: `ix_incidents_subject_status_created`, `ix_incidents_run_created` (Section 4). The CHECK is essential: without it a null `demo_run_id` would cause a composite FK to be skipped under `MATCH SIMPLE`, allowing a runless incident to point at a run-scoped anomaly. No status CHECK until vocabulary is approved. No defaults. Restrictive FKs. Current prototype: required for true anomaly and false-alarm lifecycle; whether runless incidents enter the first schema is unresolved.

#### `incident_anomaly_events` — proposed current-demo evidence association

Purpose: connect the incident to one triggering event and optional supporting evidence while retaining the direct trigger pointer on `incidents`.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `incident_id` | `UUID` | No | Part of PK and composite FKs. |
| `anomaly_event_id` | `UUID` | No | Part of PK and composite FKs. |
| `subject_user_id` | `UUID` | No | Same-subject discriminator. |
| `demo_run_id` | `UUID` | No | Same-run discriminator; prevents nullable-FK bypass. |
| `evidence_role` | `TEXT` | No | Proposed `TRIGGERING` or `SUPPORTING`; no enum/default. |
| `associated_at` | `TIMESTAMPTZ` | Yes | Optional link timestamp; no default. |

Constraints: `pk_incident_anomaly_events (incident_id, anomaly_event_id)`; `fk_incident_anomaly_events_incident_subject_run` → `incidents(incident_id, subject_user_id, demo_run_id)`; `fk_incident_anomaly_events_event_subject_run` → `anomaly_events(anomaly_event_id, subject_user_id, demo_run_id)`. PostgreSQL partial unique index `uq_incident_anomaly_events_one_trigger_per_incident` on `(incident_id) WHERE evidence_role = 'TRIGGERING'` allows at most one trigger-role row per incident. It does not prove that this row's `anomaly_event_id` equals the incident's direct trigger pointer; Shubhankar must validate equality in the same transaction that writes both. The reverse lookup index is `ix_incident_anomaly_events_event_incident` (Section 4). No default or cascade. Current prototype: proposed for anomaly-linked incidents; semantics need owner approval.

#### `verification_responses` — proposed durable response record

Purpose: record responses to incident verification; exact response vocabulary and acceptance rules remain application-owned/unresolved.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `verification_response_id` | `UUID` | No | PK; no default. |
| `incident_id` | `UUID` | No | FK to incident. |
| `responder_user_id` | `UUID` | No | FK to user. |
| `response_value` | `TEXT` | No | Vocabulary unresolved. |
| `idempotency_key` | `TEXT` | No | Format unresolved. |
| `responded_at` | `TIMESTAMPTZ` | No | No server default. |
| `request_reference` | `TEXT` | Yes | Optional opaque correlation reference only if agreed. |

Constraints: `pk_verification_responses`; restrictive FKs `fk_verification_responses_incident`, `fk_verification_responses_responder`; unique `uq_verification_responses_incident_key (incident_id, idempotency_key)`. No defaults. Index `ix_verification_responses_incident_time (incident_id, responded_at)` supports history. A row's existence does not itself authorize or apply a lifecycle transition. Current prototype: proposed/needed for the verification flow; final persistence policy unresolved.

#### `escalation_attempts` — proposed operational attempts

Purpose: persist timeout-triggered escalation separately from provider notifications.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `escalation_attempt_id` | `UUID` | No | PK; no default. |
| `incident_id` | `UUID` | No | FK to incident. |
| `trigger_reason` | `TEXT` | No | Describes approved timeout reason; vocabulary unresolved. |
| `status` | `TEXT` | No | Escalation vocabulary unresolved. |
| `started_at` | `TIMESTAMPTZ` | No | No server default. |
| `completed_at` | `TIMESTAMPTZ` | Yes | No default. |
| `idempotency_key` | `TEXT` | No | Identity includes the approved timeout generation; format unresolved. |

Constraints: `pk_escalation_attempts`; `fk_escalation_attempts_incident`; `uq_escalation_attempts_incident_key (incident_id, idempotency_key)`; `uq_escalation_attempts_id_incident (escalation_attempt_id, incident_id)` as target for a notification FK that also verifies incident consistency. No defaults. Index `ix_escalation_attempts_incident_time (incident_id, started_at)`; add a status/time work index only if an actual polling query is adopted. No cascade. Current prototype: proposed; lifecycle/persistence details require Shubhankar.

#### `notification_attempts` — optional durable notifier history

Purpose: record one logical attempt per recipient/type/escalation request. This table is optional in the logical design and must not imply successful delivery: proposed `SENT` means provider acceptance only.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `notification_attempt_id` | `UUID` | No | PK; no default. |
| `incident_id` | `UUID` | No | FK to incident. |
| `escalation_attempt_id` | `UUID` | Yes | FK when associated with an escalation. |
| `recipient_reference` | `TEXT` | Yes | Preferred protected reference; exact contract unresolved. |
| `destination_snapshot` | `TEXT` | Yes | Avoid unless approved delivery audit need; sensitive. |
| `notification_type` | `TEXT` | No | Vocabulary unresolved. |
| `result` | `TEXT` | No | Documented terms include `SIMULATED`, `SENT`, `FAILED`; no enum/default. |
| `idempotency_key` | `TEXT` | No | Per logical attempt; format unresolved. |
| `attempted_at` | `TIMESTAMPTZ` | No | No server default. |
| `provider_reference` | `TEXT` | Yes | Opaque provider response reference only if approved. |

Constraints: `pk_notification_attempts`; `fk_notification_attempts_incident`; composite `fk_notification_attempts_escalation_incident (escalation_attempt_id, incident_id)` → `escalation_attempts(escalation_attempt_id, incident_id)`; unique `uq_notification_attempts_incident_key (incident_id, idempotency_key)` unless an approved escalation-scoped key replaces it. Retries are separate attempt rows with distinct identities. No defaults. Index `ix_notification_attempts_incident_time (incident_id, attempted_at)`. Retention and PII minimization apply. Current prototype: optional; whether persistence is required is unresolved.

#### `incident_location_snapshots` — optional point-in-time location

Purpose: capture authorized location associated with an incident if the approved location workflow requires persistence. Subject is derived through incident, not duplicated.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `location_snapshot_id` | `UUID` | No | PK; no default. |
| `incident_id` | `UUID` | No | FK to incident. |
| `captured_at` | `TIMESTAMPTZ` | No | Time observed by source; no default. |
| `latitude` | `NUMERIC(9,6)` | No | Precision proposed; no default. |
| `longitude` | `NUMERIC(9,6)` | No | Precision proposed; no default. |
| `accuracy_meters` | `NUMERIC(9,2)` | Yes | Only if location provider supplies it. |
| `source_kind` | `TEXT` | Yes | Only if the approved contract supplies it. |

Constraints: `pk_incident_location_snapshots`; `fk_incident_location_snapshots_incident`; proposed `ck_incident_location_latitude_range` (`-90 <= latitude <= 90`); `ck_incident_location_longitude_range` (`-180 <= longitude <= 180`); proposed `ck_incident_location_accuracy_nonnegative`. Index `ix_incident_location_incident_captured (incident_id, captured_at DESC)`. No defaults. Restrict deletes; separate approved retention/deletion. Current prototype: optional.

#### `incident_timeline_events` — proposed append-only incident history

Purpose: durable minimum event history for the required incident timeline. This is a proposed architectural decision from the logical design, not existing functionality.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `timeline_event_id` | `UUID` | No | PK; no default. |
| `incident_id` | `UUID` | No | FK to incident. |
| `event_type` | `TEXT` | No | Lifecycle vocabulary requires owner confirmation. |
| `occurred_at` | `TIMESTAMPTZ` | No | Event instant; no default. |
| `actor_user_id` | `UUID` | Yes | FK to user when known. |
| `event_idempotency_key` | `TEXT` | No | Stable event identity scoped to incident; format unresolved. |
| `details` | `TEXT` | Yes | Minimized, non-sensitive detail only; no raw health payload. |

Constraints: `pk_incident_timeline_events`; `fk_incident_timeline_events_incident`; `fk_incident_timeline_events_actor`; unique `uq_incident_timeline_events_incident_key (incident_id, event_idempotency_key)`. Index `ix_incident_timeline_events_incident_time (incident_id, occurred_at, timeline_event_id)`. No defaults. Append-only in normal application operations; retention purge must be an explicitly authorized separate process. Current prototype: proposed to meet timeline need; owner must confirm fields, event vocabulary, and retention.

#### `hospital_catalog_entries` — optional local fallback data

Purpose: local seeded/cached candidate only if Vaishnavi's approved hospital workflow needs persistent catalog data; not a live provider integration.

| Column | PostgreSQL type | Null? | Key / default |
|---|---|---:|---|
| `hospital_id` | `UUID` | No | PK; no default. |
| `display_name` | `TEXT` | No | None. |
| `latitude` | `NUMERIC(9,6)` | No | Precision proposed. |
| `longitude` | `NUMERIC(9,6)` | No | Precision proposed. |
| `source_kind` | `TEXT` | No | Seed/source label; vocabulary unresolved. |
| `address` | `TEXT` | Yes | Include only if approved. |
| `created_at` | `TIMESTAMPTZ` | Yes | Only if catalog lifecycle needs it; no default. |
| `updated_at` | `TIMESTAMPTZ` | Yes | Only if catalog lifecycle needs it; no default. |

Constraints: `pk_hospital_catalog_entries`; proposed `ck_hospital_catalog_entries_latitude_range` (`-90 <= latitude <= 90`) and `ck_hospital_catalog_entries_longitude_range` (`-180 <= longitude <= 180`). No provider IDs, availability, acceptance, or emergency-response fields. No indexes beyond PK until an approved lookup demonstrates a need; no spatial extension is assumed. No defaults. Delete/update behavior and seed replacement policy require Vaishnavi/Role 5 agreement. Current prototype: optional; a bundled local data file may be preferable and is unresolved.

### 2.3 Logical candidates deliberately not mapped to tables

- **Source-compatible health input:** application-boundary object only; raw payload persistence remains disabled by default. It is not a relational table in the logical design.
- **Detector baseline/configuration:** no table is specified. Revisit only if Prasiddh's approved detector contract requires durable configuration/version records; do not add speculative fields or indexes.

## 3. Referential integrity and guarantee boundaries

### 3.1 Required unique FK targets

PostgreSQL requires the referenced column set of a foreign key to be backed by a primary key, unique constraint, or suitable unique index. Proposed targets:

| Target table | Required unique target | Used by |
|---|---|---|
| `demo_runs` | `(demo_run_id, subject_user_id)` | Run-scoped readings, anomalies, incidents. |
| `health_readings` | `(reading_id, subject_user_id, demo_run_id)` | `anomaly_readings`. |
| `anomaly_events` | `(anomaly_event_id, subject_user_id, demo_run_id)` | Incident trigger reference and evidence associations. |
| `incidents` | `(incident_id, subject_user_id, demo_run_id)` | Incident evidence association. |

These are database constraints, not merely ORM relationships. SQLAlchemy must map each composite FK as a single `ForeignKeyConstraint`, not independent column FKs that fail to express tuple consistency.

### 3.2 Subject and run consistency

- A `demo_runs` row has exactly one required `subject_user_id`; that subject owns the run.
- A reading with `demo_run_id` must reference `(demo_run_id, subject_user_id)` on `demo_runs`; for demo readings, `run_generation` must also be non-null. Runless ordinary readings, if supported, require both run and generation null.
- Current-prototype `anomaly_events` always require a run, subject, and generation snapshot and reference the run's matching subject.
- A run-scoped incident references its run with the same subject. `ck_incidents_run_generation_pair` requires run and generation both set or both null.
- A trigger reference requires `demo_run_id IS NOT NULL` through `ck_incidents_trigger_requires_run`. Its composite FK `(triggering_anomaly_event_id, subject_user_id, demo_run_id)` must match the referenced anomaly's event, subject, and run. This prevents an incident with null run ID from bypassing tuple checking under PostgreSQL's default `MATCH SIMPLE` behavior.
- `anomaly_readings` has non-null subject/run columns and two composite FKs to the event and reading, so evidence cannot cross either subject or run.
- `incident_anomaly_events` has non-null subject/run columns and composite FKs to the incident and anomaly. Its partial unique index allows at most one `TRIGGERING` role per incident. The application transaction must also ensure that association's anomaly ID equals the incident's direct trigger pointer; an ordinary CHECK constraint cannot compare rows in two tables.

### 3.3 Database-enforced versus application-enforced rules

| Rule | Enforcement boundary |
|---|---|
| IDs, required columns, PKs, FK existence, same-subject/run tuples, run/generation paired nullability, trigger-requires-run, positive generation, BPM positivity, approved coordinate ranges, idempotency uniqueness | PostgreSQL constraints/indexes. |
| One `TRIGGERING` association row per incident | PostgreSQL partial unique index. |
| Association event ID equals `incidents.triggering_anomaly_event_id` | Shubhankar verifies in the same transaction; not expressible as a basic row CHECK. |
| Caller is authorized for subject/run; requested subject matches ownership; run is active; worker generation equals current generation; incident state transition and timeout behavior are valid | Shubhankar's application transaction and authorization logic. |
| Detector identity/evidence semantics, key creation/replay response, notification retries, location consent/freshness, retention schedule | Owning application/team contracts; DB stores/enforces approved identities but cannot infer the semantics. |

`run_generation` on child rows is a historical snapshot. It intentionally does not FK to mutable `demo_runs.current_generation`; otherwise reset would invalidate historical rows. The composite run/subject FK guarantees identity ownership, while atomic application transaction behavior handles freshness.

### 3.4 Deletion and retention

Use restrictive foreign keys for ordinary deletion. Reset changes/invalidate run execution and pending work; it does not cascade-delete readings, incidents, timeline, users, or unrelated data. Keep/reset records only for an approved bounded purpose and retention period; no exact period is set and health data must not be retained indefinitely. Physical deletion/anonymization is a separate approved retention operation. Optional PII snapshots should be minimized and separately purged under policy.

## 4. Index strategy

All names are proposed and must be kept within PostgreSQL's 63-byte identifier limit. Do not add speculative indexes beyond the list. Primary-key and unique constraints create their own indexes; do not duplicate them.

| Exact name | Table / columns | Unique? / predicate | Query or integrity purpose |
|---|---|---|---|
| `pk_users` | `users(user_id)` | Unique PK | Identity references. |
| `pk_profiles` | `profiles(user_id)` | Unique PK | One profile per user. |
| `pk_emergency_contacts` | `emergency_contacts(contact_id)` | Unique PK | Contact identity. |
| `ix_emergency_contacts_subject_removed` | `emergency_contacts(subject_user_id, removed_at)` | Non-unique | List active/recently removed contacts for a subject. |
| `pk_caregiver_authorizations` | `caregiver_authorizations(authorization_id)` | Unique PK | Grant identity. |
| `uq_caregiver_authorizations_active_pair` | `caregiver_authorizations(subject_user_id, caregiver_user_id)` | Unique; `WHERE revoked_at IS NULL` | Enforce at most one active authorization per pair. |
| `pk_demo_runs` | `demo_runs(demo_run_id)` | Unique PK | Run identity. |
| `uq_demo_runs_id_subject` | `demo_runs(demo_run_id, subject_user_id)` | Unique | Composite child FK target. |
| `uq_demo_runs_subject_start_key` | `demo_runs(subject_user_id, start_idempotency_key)` | Unique; `WHERE start_idempotency_key IS NOT NULL` | Idempotent demo start per subject. |
| `pk_health_readings` | `health_readings(reading_id)` | Unique PK | Reading identity. |
| `uq_health_readings_id_subject_run` | `health_readings(reading_id, subject_user_id, demo_run_id)` | Unique | Composite evidence FK target. |
| `uq_health_readings_subject_ingestion_key` | `health_readings(subject_user_id, ingestion_idempotency_key)` | Unique partial; key `IS NOT NULL` | Ingestion replay protection. |
| `ix_health_readings_subject_observed` | `health_readings(subject_user_id, observed_at DESC)` | Non-unique | Recent reading history per subject. |
| `ix_health_readings_run_observed` | `health_readings(demo_run_id, observed_at)` | Non-unique | Readings for a run in time order. |
| `pk_anomaly_events` | `anomaly_events(anomaly_event_id)` | Unique PK | Detector event identity. |
| `uq_anomaly_events_id_subject_run` | `anomaly_events(anomaly_event_id, subject_user_id, demo_run_id)` | Unique | Run-scoped FK target. |
| `uq_anomaly_events_run_generation_dedupe` | `anomaly_events(demo_run_id, run_generation, dedupe_key)` | Unique | Detector replay prevention. |
| `ix_anomaly_events_subject_detected` | `anomaly_events(subject_user_id, detected_at DESC)` | Non-unique | Recent events per subject. |
| `ix_anomaly_events_run_generation_detected` | `anomaly_events(demo_run_id, run_generation, detected_at)` | Non-unique | Events for a run generation in time order. |
| `pk_anomaly_readings` | `anomaly_readings(anomaly_event_id, reading_id)` | Unique PK | Association uniqueness. |
| `ix_anomaly_readings_reading_event` | `anomaly_readings(reading_id, anomaly_event_id)` | Non-unique | Reverse reading-to-events lookup. |
| `pk_incidents` | `incidents(incident_id)` | Unique PK | Incident identity. |
| `uq_incidents_id_subject_run` | `incidents(incident_id, subject_user_id, demo_run_id)` | Unique | Run-scoped evidence FK target. |
| `uq_incidents_subject_creation_key` | `incidents(subject_user_id, creation_idempotency_key)` | Unique partial; key `IS NOT NULL` | Incident creation replay protection. |
| `uq_incidents_trigger_event` | `incidents(triggering_anomaly_event_id)` | Unique partial; trigger `IS NOT NULL`; defer until reopen policy approved | Optional one incident per trigger event. |
| `ix_incidents_subject_status_created` | `incidents(subject_user_id, status, created_at DESC)` | Non-unique | Subject incident list filtered by state. |
| `ix_incidents_run_created` | `incidents(demo_run_id, created_at)` | Non-unique | Run-specific incident lookup. |
| `pk_incident_anomaly_events` | `incident_anomaly_events(incident_id, anomaly_event_id)` | Unique PK | Evidence pair uniqueness. |
| `uq_incident_anomaly_events_one_trigger_per_incident` | `incident_anomaly_events(incident_id)` | Unique partial; `WHERE evidence_role = 'TRIGGERING'` | At most one trigger-role association for each incident. |
| `ix_incident_anomaly_events_event_incident` | `incident_anomaly_events(anomaly_event_id, incident_id)` | Non-unique | Reverse anomaly-to-incident lookup. |
| `pk_verification_responses` | `verification_responses(verification_response_id)` | Unique PK | Response identity. |
| `uq_verification_responses_incident_key` | `verification_responses(incident_id, idempotency_key)` | Unique | Verification request replay protection. |
| `ix_verification_responses_incident_time` | `verification_responses(incident_id, responded_at)` | Non-unique | Incident response history. |
| `pk_escalation_attempts` | `escalation_attempts(escalation_attempt_id)` | Unique PK | Attempt identity. |
| `uq_escalation_attempts_id_incident` | `escalation_attempts(escalation_attempt_id, incident_id)` | Unique | Composite target to ensure an optional notification escalation belongs to the same incident. |
| `uq_escalation_attempts_incident_key` | `escalation_attempts(incident_id, idempotency_key)` | Unique | Timeout/escalation duplicate prevention. |
| `ix_escalation_attempts_incident_time` | `escalation_attempts(incident_id, started_at)` | Non-unique | Incident escalation history. |
| `pk_notification_attempts` | `notification_attempts(notification_attempt_id)` | Unique PK | Attempt identity. |
| `uq_notification_attempts_incident_key` | `notification_attempts(incident_id, idempotency_key)` | Unique | Logical notification duplicate prevention; retries need distinct keys. |
| `ix_notification_attempts_incident_time` | `notification_attempts(incident_id, attempted_at)` | Non-unique | Incident notification history. |
| `pk_incident_location_snapshots` | `incident_location_snapshots(location_snapshot_id)` | Unique PK | Snapshot identity. |
| `ix_incident_location_incident_captured` | `incident_location_snapshots(incident_id, captured_at DESC)` | Non-unique | Latest incident location lookup. |
| `pk_incident_timeline_events` | `incident_timeline_events(timeline_event_id)` | Unique PK | Timeline event identity. |
| `uq_incident_timeline_events_incident_key` | `incident_timeline_events(incident_id, event_idempotency_key)` | Unique | Prevent duplicate timeline event append. |
| `ix_incident_timeline_events_incident_time` | `incident_timeline_events(incident_id, occurred_at, timeline_event_id)` | Non-unique | Stable incident timeline order. |
| `pk_hospital_catalog_entries` | `hospital_catalog_entries(hospital_id)` | Unique PK | Optional catalog identity. |

All unique FK-target entries above are explicitly needed by composite references; a simple single-column FK to a primary key reuses its PK index. An index for the optional `status` queue scan or hospital proximity query is omitted until an actual query and contract are approved.

**Foreign-key index review:** PostgreSQL does not automatically create an index on referencing (child-side) FK columns. Section 4 includes indexes only where an identified lookup/history query or composite integrity target justifies one. Review child-side indexes against actual read patterns and parent-delete/update checks; do not index every FK indiscriminately.

## 5. SQLAlchemy implementation mapping

- Use SQLAlchemy 2.x declarative mappings and typed `Mapped[...]` attributes with `mapped_column`; no async engine/session APIs.
- Map UUID values with `sqlalchemy.Uuid(as_uuid=True)`. Do not add a UUID extension or driver beyond the approved Psycopg binary dependency.
- Map instants with `DateTime(timezone=True)` and use timezone-aware Python datetimes; normalize to UTC at the owner-approved boundary.
- Map free-form/constrained vocabularies as `Text`/`String`; avoid `Enum` and PostgreSQL enum DDL until incident, run, verification, escalation, notification, and detector vocabularies are confirmed.
- Do not use `JSONB` for generic event dumps. If minimized timeline details later need structure, document its schema and privacy/retention need before choosing JSONB.
- Map every composite FK using `ForeignKeyConstraint([...], [...], name=...)`. Map checks with `CheckConstraint(..., name=...)`; represent partial unique indexes using `Index(name, columns..., unique=True, postgresql_where=...)`.
- Map the trigger association uniqueness with a PostgreSQL partial unique `Index` using `evidence_role == 'TRIGGERING'`. SQLAlchemy metadata must match Alembic DDL exactly.
- Map ORM relationships with explicit `foreign_keys`/`primaryjoin` where a subject has multiple user roles or incident has both direct trigger and association links. Avoid eager loading collections by default; use explicit `selectinload` for bounded collections and pagination/limits for history. Avoid unbounded `joinedload` across readings/evidence/attempts.
- Avoid ORM `cascade="all, delete-orphan"` for durable health, incident, authorization, timeline, and run history. Database FKs remain restrictive. Any in-memory cascade must not imply database deletion policy.
- Use a SQLAlchemy naming convention on `MetaData` (proposed): `ix_%(table_name)s_%(column_0_name)s`, `uq_%(table_name)s_%(column_0_name)s`, `ck_%(table_name)s_%(constraint_name)s`, `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`, `pk_%(table_name)s`. For CHECKs, pass the semantic suffix as `constraint_name` so the resulting DDL name matches the `ck_<table>_<suffix>` names above. Give multi-column indexes and all named constraints explicit names from this specification; ensure generated names remain unique and under PostgreSQL's identifier limit.
- **Integration point fact:** No application engine/session bootstrap module exists; Shubhankar owns creating it. Role 5's models expose shared metadata/imports without creating a competing engine, session factory, settings object, or application database URL convention. The application bootstrap import path remains unresolved and must be agreed before runtime integration.

## 6. Alembic migration plan

Alembic is initialized and the single initial revision implements the selected core schema. The revision has been applied to both development and test databases as reported above. The dependency ordering below records the schema relationships and remains useful for reviewing future revisions; it is not an instruction to recreate the initial migration.

### Upgrade order

1. Agree ID/time conventions, table inclusion, names, vocabularies, application transaction contracts, and retention gates.
2. **Implemented:** Alembic environment and initial revision use the shared `Base.metadata` and the dedicated `SAHYOG_MIGRATION_DATABASE_URL` contract. The migration connection verifies the `sahyog_migrator` role and does not create or reuse the application engine/session.
3. Create foundational `users` and optional `profiles`, `emergency_contacts`, `caregiver_authorizations`; create `demo_runs` after `users`.
4. Create `health_readings` after `users` and `demo_runs`; create `anomaly_events` after `users` and `demo_runs`.
5. Create `incidents` after users, runs, and anomaly events so trigger composite references can be added. Where circular ordering arises, create base table first, then add named composite constraints after both sides exist.
6. Create optional `anomaly_readings` and `incident_anomaly_events` after both parent tables and their unique composite FK target constraints exist. Add `uq_incident_anomaly_events_one_trigger_per_incident` as a PostgreSQL partial unique index only after the evidence role values are confirmed.
7. Create `verification_responses`, `escalation_attempts`, optional `notification_attempts`, optional `incident_location_snapshots`, and proposed `incident_timeline_events` after `incidents` (and escalation before notification).
8. Create optional `hospital_catalog_entries` only if its storage choice is approved. Add secondary indexes after base tables and FK targets are in place.
9. Review generated DDL and constraints against the specification; never let autogenerate silently accept data-contract changes.

### Downgrade order

Drop secondary/partial indexes and association/child tables before their referenced parents: hospital entries (independent), timeline/location/notification/verification/escalation, incident-anomaly and anomaly-reading associations, then incidents, anomaly events, readings, demo runs, authorization/contact/profile, and finally users. Drop constraints before dropping a referenced target only when separate revision boundaries require it. Downgrade is schema-only and must not be used as a production data deletion procedure.

### Partial indexes and PostgreSQL 16 verification

Use Alembic `op.create_index(..., unique=True, postgresql_where=...)` and `op.drop_index(...)` for partial unique indexes. Alembic revision source should carry explicit names and predicates; inspect the emitted PostgreSQL DDL. On a disposable PostgreSQL 16 database, test a clean `upgrade head`, inspect constraints/index predicates, test representative valid/invalid inserts, then `downgrade base` and verify schema removal. Recreate a fresh database and upgrade again. Do not use SQLite as proof of PostgreSQL composite-FK, partial-index, locking, or timezone semantics.

## 7. Demo reset and concurrency design

### Generation model

`demo_runs.current_generation BIGINT NOT NULL` is the live monotonic concurrency token. Child records with demo provenance store a non-null `run_generation` snapshot: `health_readings` (when run-scoped), `anomaly_events`, and `incidents`. The snapshot records which generation produced the row and remains unchanged after reset. It is not a foreign key to the mutable current generation; old rows remain referentially valid through `(demo_run_id, subject_user_id)` and retention policy. Do not treat generation as a new run ID. A replay starts a separate `demo_run_id`.

### Required transaction protocol (Shubhankar application ownership)

Use the same PostgreSQL row as the serialization point for both reset and every worker transaction that can write run-scoped state. A generation read in a separate transaction followed by writes in another transaction is unsafe and prohibited. `SELECT ... FOR UPDATE` intentionally serializes workers for the same demo run, even when they might otherwise write independent child rows. This is an accepted correctness-over-concurrency trade-off for the current deterministic prototype; workers for different runs are not serialized by this run-row lock.

**Worker transaction (proposed):**

1. Begin one SQLAlchemy `Session` transaction on the synchronous Psycopg connection (use PostgreSQL `READ COMMITTED` or an explicitly reviewed equivalent; retry whole transactions on serialization failures if a stronger isolation level is selected).
2. Select the target `demo_runs` row by `demo_run_id` using `SELECT ... FOR UPDATE` (SQLAlchemy `with_for_update()`). Do not rely on a previously cached ORM object; refresh/populate from the locked database row.
3. In that transaction, verify caller/subject authorization, active run status, and equality of captured `(demo_run_id, run_generation)` with the row's subject and `current_generation`.
4. If stale, inactive, or mismatched, perform no child writes and return/raise the owner-approved stale-work outcome. Otherwise insert/update the required readings/events/incidents and idempotency records in the same transaction while holding the lock.
5. Commit once all transaction-owned writes complete; rollback all on failure. No provider/network call is made while holding the database row lock; record durable intent transactionally, then call external systems under separately approved outbox/retry semantics.

**Reset transaction (proposed):**

1. Begin one transaction and select the same run row `FOR UPDATE`.
2. Validate caller authorization and selected-run ownership in application code.
3. Mark the run non-active/resetting according to the status contract, increment `current_generation`, set reset time, and invalidate/cancel pending run-scoped work records as approved.
4. Commit the generation bump and state change together. Do not delete unrelated records and do not reuse the run identity for a replay.

**Serialization:** If a worker locks first, reset waits; the worker may commit only its old-generation writes before reset increments the generation. Once reset commits, subsequent workers acquire the row lock, observe new generation/non-active status, and reject old snapshots. If reset locks first, the worker waits and then sees the committed new generation/status and performs no stale write. Both paths are safe because validation and writes share one transaction and lock. Use a consistent lock order (run row before child rows) to reduce deadlocks. Handle deadlock/serialization errors with bounded, owner-approved retry of the entire idempotent transaction, never an unbounded loop.

A conditional-write alternative is acceptable only if the worker's conditional statement both checks active status/current generation and gates all child writes in the same database transaction, with affected-row/`RETURNING` success checked before commit. A check followed by a later independent transaction is not acceptable. Shubhankar owns the application/session transaction protocol and lifecycle result; Role 5 owns the FK/unique/check constraints and PostgreSQL integration tests that support and verify it.

### Idempotency interactions

The logical design leaves exact key formats to owners. Persist approved identities at their documented scopes: demo start in `demo_runs`, reading ingestion in `health_readings`, detector dedupe in `anomaly_events`, incident create in `incidents`, verification in `verification_responses`, timeout attempt in `escalation_attempts`, notification attempt in `notification_attempts` if adopted, and timeline append in `incident_timeline_events`. Unique constraints prevent duplicate persistence under concurrency; Shubhankar must handle a unique conflict by returning/reusing the prior operation result only according to the approved API contract. Intentional notification retries use distinct logical attempt identities. A unique constraint alone does not validate semantics or invoke providers.

## 8. PostgreSQL integration tests and remaining strategy

The repository implements 27 PostgreSQL integration tests in
`backend/tests/test_postgresql_schema.py`, using the guarded fixtures in
`backend/tests/conftest.py`. They target the isolated `sahyog_test` database
and actual PostgreSQL schema constraints. No shared or production database or
real notification credentials are used. Test implementation is distinct from
successful runtime validation against PostgreSQL.

Implemented coverage includes:

1. **Schema readiness:** required nine tables plus `alembic_version`; revision
   matches expected head.
2. **CHECKs:** supported demo scenario, positive heart rate and generation,
   run/generation pair consistency, and trigger-requires-run.
3. **Composite FKs:** same-subject/run integrity for readings, incident
   triggers, and incident-anomaly evidence associations.
4. **Trigger integrity:** reject a second `TRIGGERING` association for one
   incident. Trigger-pointer and association equality remains an application
   transaction responsibility.
5. **Idempotency:** uniqueness for demo start, reading ingestion, anomaly
   dedupe, incident creation, verification, escalation, and timeline events.
6. **Restrictive deletion:** reject deletion of referenced users, runs,
   incidents, or anomalies.

Future test work includes reset/worker concurrency with two independent
sessions, migration upgrade/downgrade lifecycle, and timezone round-trip
behavior. Reset concurrency depends on Shubhankar's application transaction
behavior and generation locking; it is not covered by the current 27 tests.

Historical validation: an earlier local PostgreSQL test run, before the
latest timeout and failed-transaction handling adjustments, reported 19 tests
passed and was interrupted while waiting in the verification-idempotency test.
That was not a full-suite pass and does not validate the current test
implementation. This documentation update does not rerun PostgreSQL tests;
record any later execution result separately.

## 9. Ownership and integration boundaries

| Owner | Responsibility | Physical-schema boundary |
|---|---|---|
| Role 5 | SQLAlchemy models, Alembic migrations, database constraints, schema tests, PostgreSQL development infrastructure, and integration coordination. | Implements only approved schema contracts; owns names and migration/test design. Does not create the application engine/session bootstrap. |
| Shubhankar | Engine/session bootstrap, application transaction behavior, lifecycle and generation validation. | Supplies the real integration point and owns lock/transaction protocol, authorization, trigger-association equality, stale-work response, and cross-row lifecycle checks. |
| Prasiddh | Source/canonical reading and anomaly detector contracts. | Defines reading source/unit/time semantics, detector evidence/window and stable deduplication identity; Role 5 maps only reviewed contracts. |
| Vaishnavi | Dashboard, location and hospital integration contracts. | Defines displayed fields, location consent/freshness and response shape; confirms whether location/hospital persistence is needed. |
| Aditya | Flutter client and demo scenario behavior. | Confirms scenario/run identity, reset/replay and client retry semantics; consumes backend-authoritative incident result. |

The nine ORM models, shared metadata, Alembic environment, and initial migration are implemented. The migration has been applied to `sahyog_dev` and `sahyog_test` as reported for this closeout. No application engine/session module, runtime persistence operations, or application-level DML permission provisioning is implemented. Do not represent proposed API or lifecycle contracts as existing runtime interfaces.

## 10. Open decisions before runtime integration or schema extensions

1. Exact persisted incident status vocabulary and allowed transitions.
2. Incident reopening policy and whether a triggering anomaly can ever create another incident; this controls `uq_incidents_trigger_event`.
3. Whether notification attempts require persistence and the final notification idempotency scope.
4. Whether hospital catalog entries require PostgreSQL persistence or a bundled/local seed resource.
5. Exact retention periods and deletion/anonymization rules for health, incident/timeline, contact, location, notification, and reset records; no indefinite health-data retention.
6. Source-record ID uniqueness scope and whether the first prototype has a stable source ID.
7. Idempotency key formats and request replay responses for every operation.
8. Whether ordinary non-demo incidents will be supported by runtime behavior. The initial schema retains nullable incident/run fields but requires a run for a triggering anomaly; any schema change or runless anomaly/evidence support needs an approved follow-up design and migration before implementation.
9. Identity/auth table contract, profile shape/cardinality, contact channel vocabulary, and authorization consent/revocation behavior.
10. Canonical reading field names, timestamp semantics, supported source units/conversion policy, BPM bounds, and activity vocabulary.
11. Detector result/severity/evidence vocabulary, `anomaly_readings` need, detector-version identity, and ordinary non-demo events.
12. Demo-run status/outcome vocabulary, active-run uniqueness scope, generation lifecycle, reset-visible state, and stale-work response.
13. Verification response vocabulary, late/duplicate response behavior, escalation lifecycle/retry rules, and notification provider-result semantics (`SENT` means provider acceptance only in this proposal).
14. Location snapshot precision/access/consent/retention and hospital fallback contract.
15. Incident timeline approval, event vocabulary, minimal details, idempotency semantics, append-only exceptions, and retention.
16. UUID generation ownership, timestamp clock policy, and the actual Shubhankar engine/session/module integration point.

**Readiness:** This document is the approved physical schema baseline, and the initial schema implementation and 27 schema/constraint PostgreSQL integration test cases are in place. Remaining work includes Shubhankar's engine/session integration, runtime persistence and DML permission provisioning, PostgreSQL runtime validation, and future migration-lifecycle, timestamp, and concurrency tests. Unresolved decisions above continue to govern future extensions and application contracts.
