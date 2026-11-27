from __future__ import annotations

import pytest
from backend.app.core.config import Settings
from backend.app.db.session import SessionLocal
from backend.app.main import _cors_origins, create_app
from backend.app.services.notifier import get_demo_notifier
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


def test_cors_origins_parsing() -> None:
    raw = "http://localhost:3000,http://127.0.0.1:3000"
    assert _cors_origins(raw) == ["http://localhost:3000", "http://127.0.0.1:3000"]

    raw_messy = "  http://localhost:3000 , ,   ,, http://localhost:5173  , http://127.0.0.1:5173  "
    assert _cors_origins(raw_messy) == [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    assert _cors_origins("") == []
    assert _cors_origins("   ") == []
    assert _cors_origins(",, ,  ,") == []


def test_cors_preflight_allowed_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    test_settings = Settings(
        cors_allowed_origins="http://localhost:3000,http://127.0.0.1:3000",
        timeout_worker_enabled=False,
    )
    monkeypatch.setattr("backend.app.main.get_settings", lambda: test_settings)
    app = create_app()
    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert "GET" in response.headers.get("access-control-allow-methods", "")


def test_cors_disallowed_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    test_settings = Settings(
        cors_allowed_origins="http://localhost:3000",
        timeout_worker_enabled=False,
    )
    monkeypatch.setattr("backend.app.main.get_settings", lambda: test_settings)
    app = create_app()
    with TestClient(app) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://untrusted-domain.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") is None


def test_cors_empty_origins_omits_middleware(monkeypatch: pytest.MonkeyPatch) -> None:
    test_settings = Settings(
        cors_allowed_origins="  ,  ,  ",
        timeout_worker_enabled=False,
    )
    monkeypatch.setattr("backend.app.main.get_settings", lambda: test_settings)
    app = create_app()
    middleware_classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware not in middleware_classes


def test_lifespan_worker_enabled_startup_and_clean_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_settings = Settings(
        timeout_worker_enabled=True,
        timeout_worker_interval_seconds=0.25,
        timeout_worker_batch_size=20,
    )
    monkeypatch.setattr("backend.app.main.get_settings", lambda: test_settings)

    worker_started = False
    worker_stopped = False
    received_params = {}

    async def fake_run_timeout_worker(
        session_factory,
        notifier,
        stop_event,
        *,
        interval_seconds=1.0,
        batch_limit=50,
    ) -> None:
        nonlocal worker_started, worker_stopped, received_params
        worker_started = True
        received_params = {
            "session_factory": session_factory,
            "notifier": notifier,
            "interval_seconds": interval_seconds,
            "batch_limit": batch_limit,
        }
        await stop_event.wait()
        worker_stopped = True

    monkeypatch.setattr("backend.app.main.run_timeout_worker", fake_run_timeout_worker)

    app = create_app()
    with TestClient(app):
        assert worker_started is True
        assert not worker_stopped
        assert received_params["session_factory"] is SessionLocal
        assert received_params["notifier"] == get_demo_notifier()
        assert received_params["interval_seconds"] == 0.25
        assert received_params["batch_limit"] == 20

    assert worker_stopped is True


def test_lifespan_worker_disabled_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    test_settings = Settings(
        timeout_worker_enabled=False,
    )
    monkeypatch.setattr("backend.app.main.get_settings", lambda: test_settings)

    worker_invoked = False

    async def fake_run_timeout_worker(*_args, **_kwargs) -> None:
        nonlocal worker_invoked
        worker_invoked = True

    monkeypatch.setattr("backend.app.main.run_timeout_worker", fake_run_timeout_worker)

    app = create_app()
    with TestClient(app) as client:
        assert worker_invoked is False
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "sahyog-backend"}


def test_location_routes_mounted_correctly() -> None:
    app = create_app()
    routes = set(app.openapi()["paths"].keys())

    assert "/api/v1/location/updates" in routes
    assert "/api/v1/location/latest" in routes
    assert "/api/v1/hospitals/nearby" in routes
    assert not any(path.startswith("/api/v1/api/v1") for path in routes)
