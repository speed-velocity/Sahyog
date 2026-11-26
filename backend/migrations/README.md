# SAHYOG database migrations

Alembic uses the shared metadata from `backend.app.models.Base.metadata`. The
environment imports all nine ORM models and does not initialize the FastAPI
application's engine or session factory.

## Connection roles

Online Alembic commands require `SAHYOG_MIGRATION_DATABASE_URL` to be supplied
by the developer or deployment environment. The URL must use PostgreSQL with
the synchronous Psycopg 3 driver and authenticate as `sahyog_migrator`. The
environment rejects other roles and drivers; it never falls back to the
runtime `sahyog_app` role, `sahyog_admin`, or container bootstrap credentials.
It also verifies the connected PostgreSQL session's effective and authenticated
roles before invoking migration operations.
The URL is not stored in this repository, `alembic.ini`, or the root
`.env.example`, and the migration environment does not print it.

Runtime application settings and the migration connection are separate
contracts. Shubhankar owns the application's engine/session bootstrap; this
Alembic environment creates only a short-lived migration connection.

## Commands

From the repository root, provide an approved migration URL in the current
PowerShell session, then invoke Alembic with its config path:

```powershell
$env:SAHYOG_MIGRATION_DATABASE_URL = "<approved URL for sahyog_migrator>"
uv run --project backend --locked --group migrations alembic -c backend/alembic.ini history
```

From `backend/`, the equivalent config is discovered in the current directory:

```powershell
$env:SAHYOG_MIGRATION_DATABASE_URL = "<approved URL for sahyog_migrator>"
uv run --locked --group migrations alembic history
```

Create an initial revision only after the migration connection points to an
approved isolated database and the generated operations have been reviewed
against `docs/PHYSICAL_DATABASE_SCHEMA.md`:

```powershell
uv run --locked --group migrations alembic revision --autogenerate -m "initial schema"
```

Offline SQL generation does not require the migration URL or a live database:

```powershell
uv run --project backend --locked --group migrations alembic -c backend/alembic.ini upgrade head --sql
```

Do not run migrations against a shared or production database. Do not put
credentials in command history, source files, or tracked configuration.

## Downgrades and data loss

The initial migration's downgrade drops all nine tables and their data.
Perform downgrades only against disposable databases or databases with an
appropriate backup. Normal deployment should use forward migrations; do not
use a downgrade as a production data-deletion or recovery procedure.
