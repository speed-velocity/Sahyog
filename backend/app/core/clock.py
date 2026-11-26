"""Centralized UTC clock used by backend services and tests."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return an aware UTC timestamp from the system clock."""

    return datetime.now(UTC)
