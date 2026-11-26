-- Official PostgreSQL image initialization scripts run only when the data directory is empty.
-- This script is executed as the bootstrap administrator during first initialization.
-- It creates only the separate local test database; it does not create application roles or schema.
CREATE DATABASE sahyog_test;
