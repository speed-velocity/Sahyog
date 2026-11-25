from datetime import UTC

from backend.app.core.clock import utc_now
from backend.app.main import create_app


def test_utc_clock_returns_aware_utc_timestamp() -> None:
    timestamp = utc_now()

    assert timestamp.tzinfo == UTC


def test_application_has_versioned_router_seam() -> None:
    app = create_app()

    assert "/health" in app.openapi()["paths"]
