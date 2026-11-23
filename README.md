# SAHYOG — Detect. Verify. Respond.

SAHYOG is a simulated health-monitoring and emergency-response prototype. Its target architecture is a Flutter Android app, FastAPI backend, PostgreSQL database, and React caregiver dashboard. The three demo scenarios are `NORMAL`, `TRUE_ANOMALY`, and `FALSE_ALARM`; they are intended to use the same processing pipeline.

This repository currently contains the project requirements and architecture documents. Application components and their run commands are being added in phases. Do not treat simulated readings or notifications as real wearable measurements or delivered emergency communications.

## Technology baseline

The proposed integration baseline is Python 3.12, uv, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL 16, Psycopg 3, Pydantic Settings, pytest, Ruff, and GitHub Actions. Mobile and dashboard tooling follows the approved project architecture. Backend manifests and application configuration are not part of the repository foundation phase.

## Windows development prerequisites

Install the project toolchain using the official distribution instructions for each tool. The project baseline currently specifies:

- Git
- Python 3.12
- uv
- PostgreSQL 16 and its command-line client (`psql`)
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

Some tools are only needed for their corresponding component. The backend manifest, database settings, migration commands, and component startup commands will be documented after their implementation and integration review. No application start command is available in the current foundation-only tree.

## Project documents

- [PRD.md](PRD.md) — product behavior and scope
- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) — proposed architecture and contracts
- [TEAM.md](TEAM.md) — role ownership
- [Agents.md](Agents.md) — coding-agent instructions
- [HandOff.md](HandOff.md) — shared progress and integration tracker
- [docs/PHASE_0A_FOUNDATION.md](docs/PHASE_0A_FOUNDATION.md) — repository baseline and foundation ownership

## Development and integration

Use the assigned feature branch and coordinate shared contracts with the component owners. Keep secrets in local environment configuration; never commit credentials or place backend secrets in mobile or dashboard code. Role 5 coordinates database infrastructure, migrations, repository tooling, CI, and cross-component integration. See `TEAM.md` and `HandOff.md` before taking on component-owned work.
