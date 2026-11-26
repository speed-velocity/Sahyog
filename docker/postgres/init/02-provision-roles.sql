-- Official PostgreSQL image initialization scripts run only for an empty data directory.
-- This script receives secrets from the container environment through psql's \getenv.
-- It never echoes those values and suppresses statement logging for this session.
\set ON_ERROR_STOP on
\set ECHO none
\getenv migrator_password SAHYOG_MIGRATOR_PASSWORD
\getenv app_password SAHYOG_APP_PASSWORD

SET log_statement = 'none';
SET log_min_error_statement = 'panic';

DO $$
BEGIN
    IF current_user <> 'sahyog_admin' THEN
        RAISE EXCEPTION 'Role provisioning must run as sahyog_admin';
    END IF;
    IF current_database() <> 'sahyog_dev' THEN
        RAISE EXCEPTION 'Role provisioning must start in sahyog_dev';
    END IF;
END
$$;

CREATE ROLE sahyog_migrator
    LOGIN PASSWORD :'migrator_password'
    NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE sahyog_app
    LOGIN PASSWORD :'app_password'
    NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE sahyog_dev FROM PUBLIC;
REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE sahyog_test FROM PUBLIC;
REVOKE CREATE, TEMPORARY ON DATABASE sahyog_dev FROM sahyog_migrator, sahyog_app;
REVOKE CREATE, TEMPORARY ON DATABASE sahyog_test FROM sahyog_migrator, sahyog_app;
GRANT CONNECT ON DATABASE sahyog_dev, sahyog_test TO sahyog_migrator, sahyog_app;

\connect sahyog_dev
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM sahyog_app;
GRANT USAGE, CREATE ON SCHEMA public TO sahyog_migrator;
GRANT USAGE ON SCHEMA public TO sahyog_app;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, sahyog_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator
    REVOKE ALL ON TABLES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator
    REVOKE ALL ON SEQUENCES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM PUBLIC, sahyog_app;

\connect sahyog_test
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM sahyog_app;
GRANT USAGE, CREATE ON SCHEMA public TO sahyog_migrator;
GRANT USAGE ON SCHEMA public TO sahyog_app;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC, sahyog_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator
    REVOKE ALL ON TABLES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator
    REVOKE ALL ON SEQUENCES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC, sahyog_app;
ALTER DEFAULT PRIVILEGES FOR ROLE sahyog_migrator IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM PUBLIC, sahyog_app;

\unset migrator_password
\unset app_password
