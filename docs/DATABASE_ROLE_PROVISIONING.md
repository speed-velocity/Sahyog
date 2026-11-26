# SAHYOG PostgreSQL Role Provisioning

This guide describes the local PostgreSQL role boundary for the approved
database schema. It covers a fresh Docker volume and a separate, explicitly
operator-run procedure for databases in an existing volume. It never resets or
recreates a database or volume.

## Roles and boundaries

| Role | Purpose | Allowed authority |
|---|---|---|
| `sahyog_admin` | PostgreSQL bootstrap and local administration account created by the official image from `POSTGRES_USER`. | Administrative bootstrap only. Never use it from FastAPI or routine application code. |
| `sahyog_migrator` | Dedicated Alembic account. | `CONNECT` to `sahyog_dev` and `sahyog_test`; `USAGE` and `CREATE` on each `public` schema. Objects it creates, including `alembic_version`, are owned by this role. Used online only through `SAHYOG_MIGRATION_DATABASE_URL`. |
| `sahyog_app` | Future FastAPI runtime account. | `CONNECT` to both databases and `USAGE` on `public`. No schema `CREATE`, table ownership, table DML, or sequence privileges are provisioned yet. |

The two service roles are `LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
NOREPLICATION NOBYPASSRLS`. They receive no role memberships. Do not change
ownership of the database or existing application tables as part of role
provisioning. The migrator must own application tables and the Alembic version
table; the bootstrap administrator remains a separate administrative identity.

`sahyog_app` has no table-level DML grants because runtime persistence
operations have not been implemented and audited. Grant only the specific
`SELECT`, `INSERT`, `UPDATE`, or `DELETE` privileges required by actual code
when that work is ready. Do not add blanket grants or sequence privileges in
advance. Default privileges for future migrator-created tables and sequences
are explicitly kept away from `PUBLIC` and `sahyog_app`.

## Local environment variables

Copy `.env.example` to the ignored root `.env`, then replace every password
placeholder with a different, strong local-only value:

```powershell
Copy-Item .env.example .env
notepad .env
```

The variables are:

- `POSTGRES_USER=sahyog_admin` and `POSTGRES_PASSWORD`: bootstrap administrator
  used by the official image on first initialization.
- `POSTGRES_DB=sahyog_dev` and `POSTGRES_PORT`: initial development database
  and localhost port.
- `SAHYOG_MIGRATOR_PASSWORD`: password for the dedicated migration login.
- `SAHYOG_APP_PASSWORD`: password reserved for the runtime login.

Compose passes the two role passwords to the PostgreSQL container environment.
The initialization script reads them with psql's `\getenv` meta-command and
uses psql's quoted variable substitution. PostgreSQL does not expand shell
variables in SQL files. The script disables statement logging for its
provisioning connection and error-statement logging, does not echo password
variables, and clears the psql variables after use. The values remain in the local container environment;
protect Docker access and do not print `docker compose config` output, the
container environment, or credential-bearing connection URLs in shared logs or
reports.

The migration URL is a separate contract. Supply
`SAHYOG_MIGRATION_DATABASE_URL` only to the Alembic process, using
`sahyog_migrator`; it is not added to `.env.example`. The FastAPI connection
settings remain Shubhankar-owned and must use `sahyog_app`, never
`sahyog_admin` or `sahyog_migrator`.

## Fresh-volume initialization

The official PostgreSQL image runs files in
`docker/postgres/init/` in filename order only when its data directory is
empty:

1. `01-create-test-database.sql` creates `sahyog_test`; Compose initializes
   `sahyog_dev` from `POSTGRES_DB`.
2. `02-provision-roles.sql` runs as `sahyog_admin`, creates the two restricted
   logins from the supplied password environment variables, revokes default
   `PUBLIC` database/schema access and grants, and applies the role-specific
   database and schema privileges in both databases.
3. It leaves `public` schema ownership unchanged. `sahyog_migrator` receives
   `USAGE, CREATE`; `sahyog_app` receives `USAGE` only. No table DML is granted.
4. Global and `public`-schema default privileges for objects subsequently
   created by `sahyog_migrator` explicitly revoke table and sequence
   privileges from `PUBLIC` and `sahyog_app`.

Start or update the local service without deleting its volume:

```powershell
docker compose up -d postgres
docker compose ps
```

**Initialization scripts do not rerun on an existing named volume.** Editing
the scripts or `.env` does not provision roles in an already initialized
cluster. Never use `docker compose down -v` for setup or role changes.

## Existing-volume provisioning

This procedure is intentionally manual. It does not create, drop, reset, or
recreate a database, table, or volume, and Compose does not invoke it. It alters
role attributes/passwords and ACLs only. Review current grants and any local
users that rely on `PUBLIC` access first. If a role owns any application table,
or an unexpected elevated role membership is found, stop and resolve that
ownership/membership separately; this procedure does not transfer ownership.

### 1. Connect as the existing administrator

Use the bootstrap superuser that actually exists in the initialized cluster.
Changing `POSTGRES_USER` in `.env` does not create a new administrator in an
existing volume. Set the role name interactively in PowerShell, then connect:

```powershell
$dbAdminRole = Read-Host "Existing PostgreSQL bootstrap superuser role"
docker compose exec -it postgres psql -X -U $dbAdminRole -d sahyog_dev
```

If the container requires password authentication, add psql's `-W` option to
prompt securely. Never pass a password in a command argument, `PGPASSWORD`, or
a SQL literal. In the interactive psql session, first confirm the current
identity and inspect roles, memberships, database ACLs, schema ACLs, defaults,
and table ownership:

```sql
SELECT current_user, session_user;
SET log_statement = 'none';
SET log_min_error_statement = 'panic';

SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls, rolinherit
FROM pg_roles
WHERE rolname IN ('sahyog_admin', 'sahyog_migrator', 'sahyog_app')
ORDER BY rolname;

SELECT granted.rolname AS granted_role, member.rolname AS member_role
FROM pg_auth_members AS m
JOIN pg_roles AS granted ON granted.oid = m.roleid
JOIN pg_roles AS member ON member.oid = m.member
WHERE member.rolname IN ('sahyog_migrator', 'sahyog_app')
   OR granted.rolname IN ('sahyog_migrator', 'sahyog_app');

SELECT d.datname,
       CASE WHEN m.oid IS NULL THEN NULL
            ELSE has_database_privilege(m.oid, d.oid, 'CONNECT') END AS migrator_connect,
       CASE WHEN a.oid IS NULL THEN NULL
            ELSE has_database_privilege(a.oid, d.oid, 'CONNECT') END AS app_connect
FROM pg_database AS d
LEFT JOIN pg_roles AS m ON m.rolname = 'sahyog_migrator'
LEFT JOIN pg_roles AS a ON a.rolname = 'sahyog_app'
WHERE d.datname IN ('sahyog_dev', 'sahyog_test')
ORDER BY d.datname;

SELECT datname, datacl
FROM pg_database
WHERE datname IN ('sahyog_dev', 'sahyog_test')
ORDER BY datname;

SELECT nspname, pg_get_userbyid(nspowner) AS schema_owner, nspacl
FROM pg_namespace
WHERE nspname = 'public';

SELECT schemaname, tablename, tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

SELECT c.relname, c.relkind, pg_get_userbyid(c.relowner) AS owner, c.relacl
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'S')
ORDER BY c.relname;

SELECT d.defaclrole::regrole AS owner_role,
       COALESCE(n.nspname, '<global>') AS schema_name,
       d.defaclobjtype, d.defaclacl
FROM pg_default_acl AS d
LEFT JOIN pg_namespace AS n ON n.oid = d.defaclnamespace
WHERE d.defaclrole IN (SELECT oid FROM pg_roles
                       WHERE rolname IN ('sahyog_migrator', 'sahyog_app'))
  AND (d.defaclnamespace = 0 OR n.nspname = 'public');
```

The reported existing state is that the ten tables in each database (nine
application tables and `alembic_version`) are owned by `sahyog_migrator`.
Confirm that before proceeding. Stop if ownership differs; do not change it as
part of this procedure. Also inspect whether any other local role depends on
`PUBLIC` database or schema access before revoking it.

### 2. Create only missing roles, then restrict both roles

The following psql pattern creates a role only when absent. It emits no
password. Run each statement in the interactive psql session:

```sql
SELECT 'CREATE ROLE sahyog_migrator NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sahyog_migrator')
\gexec

SELECT 'CREATE ROLE sahyog_app NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sahyog_app')
\gexec

ALTER ROLE sahyog_migrator NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE sahyog_app NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

Then set each role password through psql's interactive password prompt, using
the same local-only values entered in `.env`. The entered values are not SQL
literals or command-line arguments:

```text
\password sahyog_migrator
\password sahyog_app
```

Only after both prompts complete, enable the logins:

```sql
ALTER ROLE sahyog_migrator LOGIN;
ALTER ROLE sahyog_app LOGIN;
```

Review membership-query results. These service roles must not be members of
`sahyog_admin` or another role that provides elevated privileges. Revoke only
the specific unexpected memberships after reviewing them; do not change
ownership of existing objects.

For the known service-role memberships, these revokes are safe to run after
reviewing the query above; they do not alter table ownership:

```sql
REVOKE sahyog_admin FROM sahyog_migrator;
REVOKE sahyog_admin FROM sahyog_app;
REVOKE sahyog_migrator FROM sahyog_app;
REVOKE sahyog_app FROM sahyog_migrator;
```

If the query shows any other membership for either service role, inspect its
privileges and revoke that specific membership before continuing.

### 3. Apply grants in both databases

From the administrator session, grant only database connectivity and remove
default `PUBLIC` connect/create/temp privileges. Remove database `CREATE` and
`TEMP` from both service roles as well. Do this only after confirming no other
local user relies on those `PUBLIC` privileges:

```sql
REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE sahyog_dev FROM PUBLIC;
REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE sahyog_test FROM PUBLIC;
REVOKE CREATE, TEMPORARY ON DATABASE sahyog_dev FROM sahyog_migrator, sahyog_app;
REVOKE CREATE, TEMPORARY ON DATABASE sahyog_test FROM sahyog_migrator, sahyog_app;
GRANT CONNECT ON DATABASE sahyog_dev, sahyog_test TO sahyog_migrator, sahyog_app;
```

Apply the following in **each** database, first `sahyog_dev` and then
`sahyog_test`:

```text
\connect sahyog_dev
```

```sql
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM sahyog_app;
GRANT USAGE, CREATE ON SCHEMA public TO sahyog_migrator;
GRANT USAGE ON SCHEMA public TO sahyog_app;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, sahyog_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator
    REVOKE ALL ON TABLES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator
    REVOKE ALL ON SEQUENCES FROM PUBLIC, sahyog_app;
```

Then switch to the test database and repeat the same SQL block:

```text
\connect sahyog_test
```

`REVOKE ALL ON ALL TABLES/SEQUENCES` removes grants to these grantees but does
not delete data or alter object ownership. `REVOKE ALL ON SCHEMA public FROM
PUBLIC` can affect other local roles; review the preflight results and restore
only explicitly approved access for any other role that needs the schema.

### 4. Verify both databases

In each database, confirm effective schema permissions:

```sql
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls, rolinherit
FROM pg_roles
WHERE rolname IN ('sahyog_migrator', 'sahyog_app')
ORDER BY rolname;

SELECT datname,
       has_database_privilege('sahyog_migrator', datname, 'CONNECT') AS migrator_connect,
       has_database_privilege('sahyog_migrator', datname, 'CREATE') AS migrator_create,
       has_database_privilege('sahyog_migrator', datname, 'TEMP') AS migrator_temp,
       has_database_privilege('sahyog_app', datname, 'CONNECT') AS app_connect,
       has_database_privilege('sahyog_app', datname, 'CREATE') AS app_create,
       has_database_privilege('sahyog_app', datname, 'TEMP') AS app_temp
FROM pg_database
WHERE datname IN ('sahyog_dev', 'sahyog_test')
ORDER BY datname;

SELECT current_database(),
       has_schema_privilege('sahyog_migrator', 'public', 'USAGE') AS migrator_usage,
       has_schema_privilege('sahyog_migrator', 'public', 'CREATE') AS migrator_create,
       has_schema_privilege('sahyog_app', 'public', 'USAGE') AS app_usage,
       has_schema_privilege('sahyog_app', 'public', 'CREATE') AS app_create;

SELECT c.relname AS object_name, c.relkind,
       pg_get_userbyid(c.relowner) AS owner,
       has_table_privilege('sahyog_app', c.oid, 'SELECT') AS app_select,
       has_table_privilege('sahyog_app', c.oid, 'INSERT') AS app_insert,
       has_table_privilege('sahyog_app', c.oid, 'UPDATE') AS app_update,
       has_table_privilege('sahyog_app', c.oid, 'DELETE') AS app_delete
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
ORDER BY c.relname;

SELECT c.relname AS sequence_name,
       has_sequence_privilege('sahyog_app', c.oid, 'USAGE') AS app_usage,
       has_sequence_privilege('sahyog_app', c.oid, 'SELECT') AS app_select,
       has_sequence_privilege('sahyog_app', c.oid, 'UPDATE') AS app_update
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'S'
ORDER BY c.relname;

SELECT d.defaclrole::regrole AS owner_role,
       COALESCE(n.nspname, '<global>') AS schema_name,
       d.defaclobjtype, d.defaclacl
FROM pg_default_acl AS d
LEFT JOIN pg_namespace AS n ON n.oid = d.defaclnamespace
WHERE d.defaclrole = 'sahyog_migrator'::regrole
  AND (d.defaclnamespace = 0 OR n.nspname = 'public');
```

Expected: `sahyog_migrator` has schema `USAGE` and `CREATE`; `sahyog_app` has
`USAGE` but not `CREATE`; application table and sequence privileges are false;
both service roles have `CONNECT` but not `CREATE` or `TEMP` on the two
databases, have no elevated role attributes or memberships, and global/schema
default ACLs grant no table/sequence privileges to `PUBLIC`/`sahyog_app`; all application
tables and `alembic_version` remain owned by `sahyog_migrator`. Repeat the
database/schema checks after
`\connect sahyog_test`. If an owner or privilege result differs, stop and
investigate before running migrations or application code.

## Operational cautions

- Fresh initialization runs only when PostgreSQL's data directory is empty.
  Neither editing an init script nor changing `.env` replays it in an existing
  `sahyog-postgres-data` volume.
- The existing-volume procedure is an explicit administrative action. It is
  never run by Compose, Alembic, FastAPI, or ordinary application startup.
- Never delete the named volume to provision roles. Never recreate databases
  to apply ACL changes.
- `sahyog_admin` is a superuser bootstrap identity. Using it from FastAPI would
  bypass the least-privilege boundary and expose every database object to
  routine application compromise.
- Add runtime table grants only after actual reads/writes are implemented and
  reviewed. Keep the `sahyog_app` role free of `CREATE`, ownership, DDL, and
  unneeded sequence privileges.
