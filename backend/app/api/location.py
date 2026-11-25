"""Location and nearby-hospital routes owned by the dashboard/location role."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from backend.app.services.location import (
    DEFAULT_HOSPITAL_RESULT_LIMIT,
    MAX_HOSPITAL_RESULT_LIMIT,
    MIN_HOSPITAL_RESULT_LIMIT,
    LocationService,
    LocationSnapshot,
    LocationUpdateRejected,
    LocationUpdateRequest,
    NearbyHospitalsResponse,
)
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1", tags=["location"])
_location_service = LocationService()


def get_location_service() -> LocationService:
    return _location_service


def _problem(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


@router.post(
    "/location/updates",
    response_model=LocationSnapshot,
    status_code=status.HTTP_201_CREATED,
)
def submit_location_update(
    update: LocationUpdateRequest,
    service: Annotated[LocationService, Depends(get_location_service)],
) -> LocationSnapshot | JSONResponse:
    try:
        return service.record_location(update)
    except LocationUpdateRejected as error:
        return _problem(
            422,
            "INVALID_LOCATION_TIMESTAMP",
            str(error),
        )


@router.get("/location/latest", response_model=LocationSnapshot)
def get_latest_location(
    service: Annotated[LocationService, Depends(get_location_service)],
    subject_user_id: Annotated[UUID | None, Query()] = None,
    incident_id: Annotated[UUID | None, Query()] = None,
) -> LocationSnapshot | JSONResponse:
    if (subject_user_id is None) == (incident_id is None):
        return _problem(
            status.HTTP_400_BAD_REQUEST,
            "LOCATION_QUERY_INVALID",
            "Provide exactly one of subject_user_id or incident_id.",
        )

    snapshot = (
        service.latest_for_subject(subject_user_id)
        if subject_user_id is not None
        else service.latest_for_incident(incident_id)
    )
    if snapshot is None:
        return _problem(
            status.HTTP_404_NOT_FOUND,
            "LOCATION_NOT_AVAILABLE",
            "No authorised location snapshot is available for the requested record.",
        )
    return snapshot


@router.get("/hospitals/nearby", response_model=NearbyHospitalsResponse)
def get_nearby_hospitals(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    service: Annotated[LocationService, Depends(get_location_service)],
    limit: Annotated[
        int,
        Query(
            ge=MIN_HOSPITAL_RESULT_LIMIT,
            le=MAX_HOSPITAL_RESULT_LIMIT,
        ),
    ] = DEFAULT_HOSPITAL_RESULT_LIMIT,
) -> NearbyHospitalsResponse | JSONResponse:
    try:
        return service.nearby_hospitals(latitude, longitude, limit)
    except Exception:  # noqa: BLE001
        return _problem(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "HOSPITAL_DIRECTORY_UNAVAILABLE",
            "The hospital directory is unavailable. Demo fallback data could not be read.",
        )
