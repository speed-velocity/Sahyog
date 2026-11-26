"""SAHYOG FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api.health import router as health_router
from backend.app.api.location import router as location_router
from backend.app.api.v1 import router as v1_router
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(health_router)
    app.include_router(v1_router)
    # location_router owns its /api/v1 prefix; mount it outside the versioned
    # router to avoid producing /api/v1/api/v1/... paths.
    app.include_router(location_router)
    return app


app = create_app()
