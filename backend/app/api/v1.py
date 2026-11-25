"""Versioned API router seam for approved SAHYOG endpoints."""

from fastapi import APIRouter

from backend.app.api.auth import router as auth_router
from backend.app.api.authorizations import router as authorizations_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.demo import router as demo_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.readings import router as readings_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(authorizations_router)
router.include_router(demo_router)
router.include_router(dashboard_router)
router.include_router(readings_router)
router.include_router(incidents_router)
