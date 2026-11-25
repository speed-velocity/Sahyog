"""Small transaction boundary helper for multi-step backend workflows."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal


@contextmanager
def transaction() -> Iterator[Session]:
    """Commit once on success and roll back once on failure."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
