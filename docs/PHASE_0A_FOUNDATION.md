# Phase 0A Repository Foundation

**Status:** Phase 0A.1 and Phase 0A.2 tooling implemented; local dependency, lint, formatting, and test checks passed. GitHub Actions has not yet been run on GitHub.
**Owner:** Role 5 — Software Integration Lead + Database Engineer

## Approved technology baseline

The proposed integration baseline is:

- Python 3.12 and uv
- `pyproject.toml` and `uv.lock`
- FastAPI and Uvicorn
- SQLAlchemy 2.x with synchronous database access
- PostgreSQL 16 and Psycopg 3 with the binary extra
- Alembic
- Pydantic Settings
- pytest and Ruff
- GitHub Actions

These selections establish the adopted baseline. Backend application configuration, models, and migrations remain future work subject to their owners' review.

## Ownership boundaries

| Area | Owner | Boundary |
|---|---|---|
| Backend application and bootstrap | Shubhankar | Owns FastAPI and Uvicorn, Pydantic Settings and direct Pydantic decisions, application configuration, settings, and database engine/bootstrap integration. |
| Database infrastructure and persistence | Role 5 | Owns SQLAlchemy and Psycopg dependencies, PostgreSQL development infrastructure, Alembic and migration tooling. Database access uses synchronous SQLAlchemy with Psycopg 3 binary. |
| Python project manifest and lock | Shared coordination | Shubhankar owns application runtime dependencies; Role 5 owns database and migration dependencies plus lock generation. Changes to `backend/pyproject.toml` or `backend/uv.lock` must keep both groups consistent. |
| Test, lint, and CI coordination | Role 5, with component owners | Role 5 coordinates pytest/Ruff setup and GitHub Actions. Component owners maintain tests and resolve failures in their owned code. |
| Repository configuration, CI, and foundation documentation | Role 5 | Owns root repository setup, GitHub Actions workflow, and approved repository documentation. |

No dependency is added beyond the selected baseline without justification and approval. This document does not define application routes, data schemas, database tables, or environment-variable names.

## Phase 0A checklist

### Phase 0A.1 — approved repository foundation

- [x] `.gitignore` — exclude local secrets, caches, generated build files, and editor/OS artifacts while preserving source, migrations, and lockfiles.
- [x] `README.md` — describe project scope, selected baseline, Windows prerequisites, repository state, and ownership/documentation links.
- [x] `docs/PHASE_0A_FOUNDATION.md` — record baseline selections, ownership boundaries, and deferred Phase 0A.2 work.

### Phase 0A.2 — tooling implementation

- [x] `backend/pyproject.toml` — declare the adopted baseline, migration/dev groups, pytest and Ruff configuration. The source tree is not yet an installable package, so uv package mode is disabled until a real package structure exists.
- [x] `backend/uv.lock` — generated from the manifest; locked dependency installation succeeded and `uv lock --check` passed.
- [x] `backend/tests/test_project_metadata.py` — smoke-check agreed package metadata and dependency grouping without specifying application behavior.
- [ ] `backend/app/core/config.py` — backend application configuration, owned by Shubhankar. Role 5 coordinates only; do not implement until approved.
- [ ] `.env.example` — document only configuration keys and placeholder values agreed with the backend and component owners; do not invent names.
- [x] `.github/workflows/ci.yml` — configured to run locked dependency installation, Ruff lint/format checks, and pytest on push and pull request. Local Ruff lint and formatting checks passed, and pytest passed (1 test). GitHub Actions has not yet been run on GitHub. No PostgreSQL service is required for the current metadata-only test; add an isolated PostgreSQL 16 service when integration tests need it.

## Local setup documentation

The root README lists the adopted Windows backend tooling and verification commands. Backend source, database configuration, and Alembic environment are not present yet; do not infer application startup, connection setting names, or schema from the tooling files. PostgreSQL provisioning method and exact dashboard Node version remain to be confirmed.

## Integration gates

Remaining Phase 0A.2 integration gates:

1. Shubhankar reviews the generated `backend/uv.lock` alongside the shared manifest.
2. Agree on application configuration settings before writing `.env.example` or backend configuration.
3. Add a PostgreSQL 16 CI service only when database integration tests are added.
