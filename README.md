# SAHYOG — Detect. Verify. Respond.

SAHYOG is a simulated health-monitoring and emergency-response prototype. Its target architecture is a Flutter Android app, FastAPI backend, PostgreSQL database, and React caregiver dashboard. The three demo scenarios are `NORMAL`, `TRUE_ANOMALY`, and `FALSE_ALARM`; they are intended to use the same processing pipeline.

This repository contains the project requirements, architecture, and initial backend tooling. Backend application code, mobile app, and dashboard are being added in phases. Do not treat simulated readings or notifications as real wearable measurements or delivered emergency communications.

## Technology baseline

The adopted integration baseline is Python 3.12, uv, FastAPI, Uvicorn, SQLAlchemy 2.x with synchronous database access, Alembic, PostgreSQL 16, Psycopg 3 with its binary extra, Pydantic Settings, pytest, Ruff, and GitHub Actions. Mobile and dashboard tooling follows the approved project architecture. Backend application configuration remains owned by Shubhankar.

## Windows development prerequisites

Install the project toolchain using the official distribution instructions for each tool. The project baseline currently specifies:

- Git
- Python 3.12
- uv
- PostgreSQL 16 and its command-line client (`psql`)
- Uvicorn, Psycopg, and other backend Python dependencies installed by uv from the backend lockfile
- Flutter SDK and Android SDK for mobile work
- Node.js for dashboard work; the exact version will be recorded with the dashboard manifest

From PowerShell, verify the tools available on your machine:

```powershell
Set-Location E:\sahyog-repo
git status --short --branch
py -3.12 --version
uv --version
psql --version
flutter --version
node --version
```

Some tools are only needed for their corresponding component. Install backend dependencies and run checks from PowerShell with:

```powershell
Set-Location E:\sahyog-repo\backend
uv sync --locked --group migrations --group dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

The application source, database settings, and migration environment are not present yet, so backend startup and database connection commands will be documented after those owner-managed components are implemented. Psycopg's binary extra avoids requiring a local compiler or separately installed client library for the Python driver; a local PostgreSQL 16 server is still required for database-backed work.

## Project documents

- [PRD.md](PRD.md) — product behavior and scope
- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) — proposed architecture and contracts
- [TEAM.md](TEAM.md) — role ownership
- [Agents.md](Agents.md) — coding-agent instructions
- [HandOff.md](HandOff.md) — shared progress and integration tracker
- [docs/PHASE_0A_FOUNDATION.md](docs/PHASE_0A_FOUNDATION.md) — repository baseline and foundation ownership

## Development and integration

Use the assigned feature branch and coordinate shared contracts with the component owners. Keep secrets in local environment configuration; never commit credentials or place backend secrets in mobile or dashboard code. Role 5 coordinates database infrastructure, migrations, repository tooling, CI, and cross-component integration. See `TEAM.md` and `HandOff.md` before taking on component-owned work.
