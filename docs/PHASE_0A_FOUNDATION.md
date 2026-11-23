# Phase 0A Repository Foundation

**Status:** Phase 0A.1 implemented; Phase 0A.2 awaits final integration review.
**Owner:** Role 5 — Software Integration Lead + Database Engineer

## Approved technology baseline

The proposed integration baseline is:

- Python 3.12 and uv
- `pyproject.toml` and `uv.lock`
- FastAPI
- SQLAlchemy 2.x and Alembic
- PostgreSQL 16 and Psycopg 3
- Pydantic Settings
- pytest and Ruff
- GitHub Actions

These selections establish the intended baseline. Backend manifests, configuration, models, and migrations remain subject to Phase 0A.2 integration review.

## Ownership boundaries

| Area | Owner | Boundary |
|---|---|---|
| Backend application and bootstrap | Shubhankar | Owns general backend application code, `backend/app/core/` configuration, application startup, and application-level dependencies such as FastAPI and Pydantic Settings. |
| Database infrastructure and persistence | Role 5 | Owns database models, Alembic migrations, PostgreSQL development setup, and database-specific dependencies: SQLAlchemy, Alembic, and Psycopg. Coordinate database connection behavior with Shubhankar. |
| Python project manifest and lock | Shared coordination | Shubhankar owns application dependency requirements. Role 5 owns integration of database/tooling requirements and lockfile consistency. Changes to `backend/pyproject.toml` or `backend/uv.lock` require coordination and review from both owners. |
| Test and lint tooling | Role 5, with component owners | Role 5 coordinates pytest/Ruff configuration and CI. Component owners maintain tests and resolve failures in their owned code. |
| Repository configuration, CI, and foundation documentation | Role 5 | Owns root repository setup, GitHub Actions workflow, and approved repository documentation. |

No dependency is added beyond the selected baseline without justification and approval. This document does not define application routes, data schemas, database tables, or environment-variable names.

## Phase 0A checklist

### Phase 0A.1 — approved repository foundation

- [x] `.gitignore` — exclude local secrets, caches, generated build files, and editor/OS artifacts while preserving source, migrations, and lockfiles.
- [x] `README.md` — describe project scope, selected baseline, Windows prerequisites, repository state, and ownership/documentation links.
- [x] `docs/PHASE_0A_FOUNDATION.md` — record baseline selections, ownership boundaries, and deferred Phase 0A.2 work.

### Phase 0A.2 — awaiting final integration review

- [ ] `backend/pyproject.toml` — declare the approved runtime and development dependencies and tool configuration. Coordinate application dependency ownership with Shubhankar.
- [ ] `backend/uv.lock` — lock the resolved dependency graph for reproducible installs.
- [ ] `backend/app/core/config.py` — backend application configuration, owned by Shubhankar. Role 5 coordinates only; do not implement until approved.
- [ ] `.env.example` — document only configuration keys and placeholder values agreed with the backend and component owners; do not invent names.
- [ ] `.github/workflows/ci.yml` — run agreed lint and test commands using the selected Python/uv baseline. Confirm PostgreSQL service needs for integration tests before adding them.

## Local setup documentation

The root README lists required Windows tools and verification commands. Detailed install, migration, seed/reset, and run commands must be added only after the corresponding manifests and application scripts exist and have been verified. PostgreSQL provisioning method and exact dashboard Node version remain to be confirmed.

## Integration gates

Before Phase 0A.2 implementation:

1. Shubhankar confirms ownership and contents of backend application dependencies in the shared manifest.
2. Agree on the dependency groups and development commands for pytest and Ruff.
3. Agree on application configuration settings before writing `.env.example` or backend config.
4. Confirm whether CI needs a PostgreSQL service for integration tests.
5. Review the Phase 0A.2 file set and integration impact before merging.
