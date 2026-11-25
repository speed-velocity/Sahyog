"""Alembic environment for SAHYOG's shared SQLAlchemy metadata."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import ArgumentError
from sqlalchemy.pool import NullPool

# `backend.app...` is the established model import convention. Add the
# repository root explicitly so Alembic works from either supported cwd.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
repository_root_text = str(REPOSITORY_ROOT)
if repository_root_text not in sys.path:
    sys.path.insert(0, repository_root_text)

from backend.app import models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = models.Base.metadata


def _migration_url() -> URL:
    """Return the dedicated migration URL without exposing it in errors."""
    raw_url = os.environ.get("SAHYOG_MIGRATION_DATABASE_URL")
    if not raw_url:
        raise RuntimeError(
            "Online migrations require SAHYOG_MIGRATION_DATABASE_URL; "
            "supply it through the developer or deployment environment."
        )

    try:
        url = make_url(raw_url)
    except ArgumentError:
        raise RuntimeError(
            "SAHYOG_MIGRATION_DATABASE_URL must be a valid SQLAlchemy URL."
        ) from None

    # A plain PostgreSQL URL is normalized explicitly to the approved Psycopg 3
    # driver. Other PostgreSQL drivers and non-PostgreSQL URLs are rejected.
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            "Online migrations require the synchronous PostgreSQL Psycopg 3 driver."
        )
    if url.username != "sahyog_migrator":
        raise RuntimeError(
            "SAHYOG_MIGRATION_DATABASE_URL must authenticate as sahyog_migrator."
        )
    return url


def run_migrations_offline() -> None:
    """Render SQL without requiring credentials or a live database."""
    context.configure(
        url="postgresql+psycopg://",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations through a short-lived, migration-only connection."""
    engine = create_engine(_migration_url(), poolclass=NullPool, echo=False)
    try:
        with engine.connect() as connection:
            roles = connection.execute(text("SELECT current_user, session_user")).one()
            if roles != ("sahyog_migrator", "sahyog_migrator"):
                raise RuntimeError(
                    "The migration connection must have both current_user and "
                    "session_user set to sahyog_migrator."
                )
            # SQLAlchemy 2.x autobegins for the role-check SELECT. End that
            # read-only transaction so Alembic can own and commit its DDL tx.
            connection.rollback()
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
