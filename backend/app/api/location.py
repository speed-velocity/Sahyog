"""Location and nearby-hospital routes owned by the dashboard/location role."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.core.auth import can_access_subject, require_active_principal
from backend.app.db.session import get_db
from backend.app.models.demo import DemoRun
from backend.app.models.incidents import Incident
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
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
from backend.app.services.location_persistence import (
    DemoRunNotFoundError,
    IncidentNotFoundError,
    get_latest_location_record_for_incident,
    get_latest_location_record_for_subject,
    persist_location_snapshot,
    snapshot_record_to_schema,
)

router = APIRouter(prefix="/api/v1", tags=["location"])
_location_service = LocationService()


def get_location_service() -> LocationService:
    return _location_service


def _problem(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def _validate_update_scope(
    update: LocationUpdateRequest,
    principal: AuthenticatedPrincipal,
    session: Session,
) -> JSONResponse | None:
    if (
        principal.role is not UserRole.SUBJECT
        or principal.user_id != update.subject_user_id
    ):
        return _problem(
            status.HTTP_403_FORBIDDEN,
            "LOCATION_ACCESS_DENIED",
            "Only the authenticated subject may submit their location.",
        )
    if update.demo_run_id is not None:
        run = session.get(DemoRun, update.demo_run_id)
        if run is None or run.subject_user_id != principal.user_id:
            return _problem(
                status.HTTP_403_FORBIDDEN,
                "LOCATION_ACCESS_DENIED",
                "The demo run is not owned by the authenticated subject.",
            )
    if update.incident_id is not None:
        incident = session.get(Incident, update.incident_id)
        if incident is None or incident.subject_user_id != principal.user_id:
            return _problem(
                status.HTTP_403_FORBIDDEN,
                "LOCATION_ACCESS_DENIED",
                "The incident is not owned by the authenticated subject.",
            )
    return None


@router.post(
    "/location/updates",
    response_model=LocationSnapshot,
    status_code=status.HTTP_201_CREATED,
)
def submit_location_update(
    update: LocationUpdateRequest,
    service: Annotated[LocationService, Depends(get_location_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_active_principal)],
    session: Annotated[Session, Depends(get_db)],
) -> LocationSnapshot | JSONResponse:
    scope_error = _validate_update_scope(update, principal, session)
    if scope_error is not None:
        return scope_error
    try:
        snapshot = service.prepare_snapshot(update)
    except LocationUpdateRejected as error:
        return _problem(
            422,
            "INVALID_LOCATION_TIMESTAMP",
            str(error),
        )

    try:
        record = persist_location_snapshot(
            session,
            update=update,
            location_snapshot_id=snapshot.location_snapshot_id,
            received_at=snapshot.received_at,
        )
        session.commit()
    except (DemoRunNotFoundError, IncidentNotFoundError) as error:
        session.rollback()
        return _problem(
            status.HTTP_400_BAD_REQUEST,
            "LOCATION_SCOPE_INVALID",
            str(error),
        )
    except Exception:  # noqa: BLE001
        session.rollback()
        return _problem(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "LOCATION_PERSISTENCE_FAILED",
            "A database error occurred while persisting the location snapshot.",
        )

    if record.demo_run_id != snapshot.demo_run_id:
        snapshot = snapshot.model_copy(update={"demo_run_id": record.demo_run_id})
        update = update.model_copy(update={"demo_run_id": record.demo_run_id})

    service.publish_snapshot(snapshot, update=update)
    return snapshot


@router.get("/location/latest", response_model=LocationSnapshot)
def get_latest_location(
    service: Annotated[LocationService, Depends(get_location_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(require_active_principal)],
    session: Annotated[Session, Depends(get_db)],
    subject_user_id: Annotated[UUID | None, Query()] = None,
    incident_id: Annotated[UUID | None, Query()] = None,
) -> LocationSnapshot | JSONResponse:
    if (subject_user_id is None) == (incident_id is None):
        return _problem(
            status.HTTP_400_BAD_REQUEST,
            "LOCATION_QUERY_INVALID",
            "Provide exactly one of subject_user_id or incident_id.",
        )

    if subject_user_id is not None:
        if not can_access_subject(session, principal, subject_user_id):
            return _problem(
                status.HTTP_403_FORBIDDEN,
                "LOCATION_ACCESS_DENIED",
                "Location access denied for the requested subject.",
            )
        snapshot = service.latest_for_subject(subject_user_id)
        if snapshot is None:
            record = get_latest_location_record_for_subject(session, subject_user_id)
            if record is not None:
                snapshot = snapshot_record_to_schema(
                    record,
                    now=service.current_time(),
                    stale_after_seconds=service.stale_after_seconds,
                )
                service.publish_snapshot(snapshot)
    else:
        incident = session.get(Incident, incident_id)
        if incident is None or not can_access_subject(
            session, principal, incident.subject_user_id
        ):
            return _problem(
                status.HTTP_403_FORBIDDEN,
                "LOCATION_ACCESS_DENIED",
                "Location access denied for the requested incident.",
            )
        snapshot = service.latest_for_incident(incident_id)
        if snapshot is None:
            record = get_latest_location_record_for_incident(session, incident_id)
            if record is not None:
                snapshot = snapshot_record_to_schema(
                    record,
                    now=service.current_time(),
                    stale_after_seconds=service.stale_after_seconds,
                )
                service.publish_snapshot(snapshot)

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
    _principal: Annotated[AuthenticatedPrincipal, Depends(require_active_principal)],
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
