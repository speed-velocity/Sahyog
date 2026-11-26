"""Protected incident retrieval and verification routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import (
    can_access_subject,
    require_active_principal,
)
from backend.app.db.session import get_db
from backend.app.models.incidents import Incident
from backend.app.schemas.api import IncidentResponse
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from backend.app.schemas.incidents import VerificationResponse
from backend.app.services.incident_service import (
    IncidentNotAwaitingVerification,
    IncidentServiceError,
    VerificationExpired,
    record_verification_response,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentResponse])
def list_incidents(
    subject_user_id: UUID | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> list[IncidentResponse]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    requested_subject = subject_user_id or principal.user_id
    if not can_access_subject(session, principal, requested_subject):
        raise HTTPException(status_code=403, detail="Incident access denied")
    query = select(Incident).where(Incident.subject_user_id == requested_subject)
    if status_filter is not None:
        query = query.where(Incident.status == status_filter)
    incidents = session.scalars(
        query.order_by(Incident.created_at.desc()).limit(limit)
    ).all()
    return [IncidentResponse.model_validate(incident) for incident in incidents]


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> IncidentResponse:
    incident = session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not can_access_subject(session, principal, incident.subject_user_id):
        raise HTTPException(status_code=403, detail="Incident access denied")
    return IncidentResponse.model_validate(incident)


@router.post("/{incident_id}/verification", response_model=IncidentResponse)
def verify_incident(
    incident_id: UUID,
    request: VerificationResponse,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> IncidentResponse:
    incident = session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if (
        principal.role is not UserRole.SUBJECT
        or principal.user_id != incident.subject_user_id
    ):
        raise HTTPException(
            status_code=403, detail="Only the monitored subject may verify"
        )
    try:
        updated = record_verification_response(
            session,
            incident_id=incident_id,
            responder_user_id=principal.user_id,
            response_value=request.response,
            idempotency_key=request.idempotency_key,
            request_reference=request.request_reference,
        )
        session.commit()
    except VerificationExpired as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IncidentNotAwaitingVerification as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IncidentServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IncidentResponse.model_validate(updated)
