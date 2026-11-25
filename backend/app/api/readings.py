"""Reading ingestion route and detector integration boundary."""

from datetime import UTC, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.auth import require_active_principal
from backend.app.core.clock import utc_now
from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.schemas.auth import AuthenticatedPrincipal
from backend.app.schemas.readings import ReadingRequest, ReadingResponse
from backend.app.services.detector_adapter import Detector, DetectorReading
from backend.app.services.incident_service import create_incident_for_anomaly
from backend.app.services.reading_service import (
    DetectorUnavailable,
    persist_reading,
)

router = APIRouter(prefix="/readings", tags=["readings"])


def get_detector() -> Detector:
    raise HTTPException(
        status_code=503,
        detail="authoritative detector provider is not configured",
    )


@router.post("", response_model=ReadingResponse, status_code=202)
def ingest_reading(
    request: ReadingRequest,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
    detector: Detector = Depends(get_detector),
) -> ReadingResponse:
    if request.source_kind != "SIMULATED":
        raise HTTPException(
            status_code=422, detail="Only SIMULATED readings are supported"
        )
    if request.observed_at.tzinfo is None:
        raise HTTPException(
            status_code=422, detail="observed_at must include a timezone"
        )
    try:
        result = detector.detect(
            [
                DetectorReading(
                    observed_at=request.observed_at.astimezone(UTC),
                    heart_rate_bpm=request.heart_rate_bpm,
                    activity_context=request.activity_context,
                )
            ]
        )
        reading, event = persist_reading(
            session,
            subject_user_id=principal.user_id,
            demo_run_id=request.demo_run_id,
            heart_rate_bpm=request.heart_rate_bpm,
            observed_at=request.observed_at,
            source_kind=request.source_kind,
            activity_context=request.activity_context,
            source_record_id=request.source_record_id,
            ingestion_idempotency_key=request.ingestion_idempotency_key,
            detector_result=result,
        )
        incident_id: UUID | None = None
        if event is not None:
            session.flush()
            incident = create_incident_for_anomaly(
                session,
                anomaly_event_id=event.anomaly_event_id,
                verification_deadline_at=utc_now()
                + timedelta(seconds=get_settings().verification_timeout_seconds),
                creation_idempotency_key=f"anomaly:{event.dedupe_key}",
            )
            incident_id = incident.incident_id
        session.commit()
    except DetectorUnavailable as exc:
        session.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ReadingResponse(
        reading_id=reading.reading_id,
        demo_run_id=reading.demo_run_id,
        accepted=True,
        detection_status="ANOMALY_DETECTED" if event else "NORMAL",
        anomaly_event_id=event.anomaly_event_id if event else None,
        incident_id=incident_id,
    )
