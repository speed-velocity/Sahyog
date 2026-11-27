"""Subject-controlled caregiver authorization routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.auth import require_active_principal
from backend.app.db.session import get_db
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole
from backend.app.schemas.authorization import (
    AuthorizationCreateRequest,
    AuthorizationResponse,
    AuthorizedSubjectResponse,
    AuthorizedSubjectsResponse,
)
from backend.app.services.authorization import (
    AuthorizationServiceError,
    grant_caregiver_access,
    list_active_authorizations,
    revoke_caregiver_access,
)

router = APIRouter(prefix="/authorizations", tags=["authorizations"])


def _require_subject(principal: AuthenticatedPrincipal) -> None:
    if principal.role is not UserRole.SUBJECT:
        raise HTTPException(status_code=403, detail="Only subjects may manage access")


@router.get("", response_model=list[AuthorizationResponse])
def list_access(
    limit: int = Query(default=100, ge=1, le=100),
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> list[AuthorizationResponse]:
    """List active grants visible to the authenticated subject or caregiver."""

    try:
        authorizations = list_active_authorizations(
            session,
            user_id=principal.user_id,
            role=principal.role,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [AuthorizationResponse.model_validate(item) for item in authorizations]


@router.get("/me", response_model=AuthorizedSubjectsResponse)
def list_my_subjects(
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> AuthorizedSubjectsResponse:
    """Return active subjects assigned to the authenticated caregiver."""

    if principal.role is not UserRole.CAREGIVER:
        raise HTTPException(
            status_code=403,
            detail="Only caregivers may list authorized subjects",
        )
    authorizations = list_active_authorizations(
        session,
        user_id=principal.user_id,
        role=principal.role,
    )
    return AuthorizedSubjectsResponse(
        authorized_subjects=[
            AuthorizedSubjectResponse.model_validate(item) for item in authorizations
        ]
    )


@router.post("", response_model=AuthorizationResponse, status_code=201)
def grant_access(
    request: AuthorizationCreateRequest,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> AuthorizationResponse:
    _require_subject(principal)
    try:
        authorization = grant_caregiver_access(
            session,
            subject_user_id=principal.user_id,
            caregiver_user_id=request.caregiver_user_id,
        )
        session.commit()
    except AuthorizationServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthorizationResponse.model_validate(authorization)


@router.delete("/{authorization_id}", response_model=AuthorizationResponse)
def revoke_access(
    authorization_id: UUID,
    principal: AuthenticatedPrincipal = Depends(require_active_principal),
    session: Session = Depends(get_db),
) -> AuthorizationResponse:
    _require_subject(principal)
    try:
        authorization = revoke_caregiver_access(
            session,
            subject_user_id=principal.user_id,
            authorization_id=authorization_id,
        )
        session.commit()
    except AuthorizationServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AuthorizationResponse.model_validate(authorization)
