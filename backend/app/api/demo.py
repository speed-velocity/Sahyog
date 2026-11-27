"""Protected demo-run routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.auth import can_access_subject, require_active_principal
from backend.app.db.session import get_db
from backend.app.models.demo import DemoRun
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from backend.app.schemas.demo import DemoRunCreateRequest, DemoRunResponse
from backend.app.services.demo import create_demo_run, reset_demo_run

router = APIRouter(prefix="/demo/runs", tags=["demo"])


@router.post("", response_model=DemoRunResponse, status_code=201)
def start_demo(
    request: DemoRunCreateRequest,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> DemoRunResponse:
    if principal.role is not UserRole.SUBJECT:
        raise HTTPException(status_code=403, detail="Only subjects may start demos")
    try:
        run = create_demo_run(
            session,
            subject_user_id=principal.user_id,
            scenario=request.scenario,
            start_idempotency_key=request.start_idempotency_key,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DemoRunResponse.model_validate(run)


@router.get("/{demo_run_id}", response_model=DemoRunResponse)
def get_demo(
    demo_run_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> DemoRunResponse:
    run = session.get(DemoRun, demo_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Demo run not found")
    if not can_access_subject(session, principal, run.subject_user_id):
        raise HTTPException(status_code=403, detail="Demo access denied")
    return DemoRunResponse.model_validate(run)


@router.post("/{demo_run_id}/reset", response_model=DemoRunResponse)
def reset_demo(
    demo_run_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> DemoRunResponse:
    if principal.role is not UserRole.SUBJECT:
        raise HTTPException(status_code=403, detail="Only subjects may reset demos")
    try:
        run = reset_demo_run(
            session, demo_run_id=demo_run_id, subject_user_id=principal.user_id
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DemoRunResponse.model_validate(run)
