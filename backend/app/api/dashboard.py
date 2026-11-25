"""Backend-authoritative dashboard summary route."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import can_access_subject, require_active_principal
from backend.app.db.session import get_db
from backend.app.models.incidents import Incident
from backend.app.models.readings import HealthReading
from backend.app.schemas.auth import AuthenticatedPrincipal
from backend.app.schemas.dashboard import DashboardOverview, LatestReadingSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def overview(
    subject_user_id: UUID | None = None,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> DashboardOverview:
    requested_subject = subject_user_id or principal.user_id
    if not can_access_subject(session, principal, requested_subject):
        raise HTTPException(status_code=403, detail="Dashboard access denied")
    reading = session.scalar(
        select(HealthReading)
        .where(HealthReading.subject_user_id == requested_subject)
        .order_by(HealthReading.observed_at.desc())
        .limit(1)
    )
    incident = session.scalar(
        select(Incident)
        .where(
            Incident.subject_user_id == requested_subject,
            Incident.status.in_(
                ["PENDING_VERIFICATION", "ESCALATION_IN_PROGRESS", "ESCALATED"]
            ),
        )
        .order_by(Incident.created_at.desc())
        .limit(1)
    )
    latest_update = None
    latest_reading = None
    if reading is not None:
        latest_reading = LatestReadingSummary(
            reading_id=reading.reading_id,
            heart_rate_bpm=reading.heart_rate_bpm,
            observed_at=reading.observed_at,
            source_kind=reading.source_kind,
        )
        latest_update = reading.received_at
    if incident is not None and (
        latest_update is None or incident.updated_at > latest_update
    ):
        latest_update = incident.updated_at
    return DashboardOverview(
        subject_user_id=requested_subject,
        monitoring_status="INCIDENT_ACTIVE" if incident else "NORMAL",
        latest_reading=latest_reading,
        active_incident=incident.incident_id if incident else None,
        incident_status=incident.status if incident else None,
        latest_update_at=latest_update,
    )
