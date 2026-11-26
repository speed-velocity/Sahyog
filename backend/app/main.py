"""SAHYOG FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.api.location import router as location_router
from backend.app.api.v1 import router as v1_router
from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal
from backend.app.services.notifier import get_demo_notifier
from backend.app.workers.timeout import run_timeout_worker


def _cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    settings = get_settings()
    stop_event = asyncio.Event()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        worker = None
        if settings.timeout_worker_enabled:
            worker = asyncio.create_task(
                run_timeout_worker(
                    SessionLocal,
                    get_demo_notifier(),
                    stop_event,
                    interval_seconds=settings.timeout_worker_interval_seconds,
                    batch_limit=settings.timeout_worker_batch_size,
                )
            )
        try:
            yield
        finally:
            stop_event.set()
            if worker is not None:
                await worker

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    origins = _cors_origins(settings.cors_allowed_origins)
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health_router)
    app.include_router(v1_router)
    # location_router owns its /api/v1 prefix; mount it outside the versioned
    # router to avoid producing /api/v1/api/v1/... paths.
    app.include_router(location_router)
    return app


app = create_app()
