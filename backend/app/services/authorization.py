"""Subject-controlled caregiver authorization service."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.clock import utc_now
from backend.app.models.auth import AuthIdentity, CaregiverAuthorization
from backend.app.schemas.auth import UserRole


class AuthorizationServiceError(RuntimeError):
    """Raised when an authorization operation is not allowed."""


def list_active_authorizations(
    session: Session, *, user_id: UUID, role: UserRole, limit: int = 100
) -> list[CaregiverAuthorization]:
    """Return active authorizations visible to the authenticated principal.

    Caregivers discover subjects through their incoming grants. Subjects see
    the grants they issued. No caller-supplied subject identifier is used for
    authorization discovery.
    """

    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    column = (
        CaregiverAuthorization.caregiver_user_id
        if role is UserRole.CAREGIVER
        else CaregiverAuthorization.subject_user_id
    )
    return list(
        session.scalars(
            select(CaregiverAuthorization)
            .where(
                column == user_id,
                CaregiverAuthorization.revoked_at.is_(None),
            )
            .order_by(CaregiverAuthorization.granted_at.desc())
            .limit(limit)
        ).all()
    )


def grant_caregiver_access(
    session: Session, *, subject_user_id: UUID, caregiver_user_id: UUID
) -> CaregiverAuthorization:
    if subject_user_id == caregiver_user_id:
        raise AuthorizationServiceError("a subject cannot authorize themselves")
    caregiver = session.get(AuthIdentity, caregiver_user_id)
    if caregiver is None or caregiver.role != UserRole.CAREGIVER.value:
        raise AuthorizationServiceError("target user is not an active caregiver")
    if caregiver.disabled:
        raise AuthorizationServiceError("target caregiver is disabled")

    current = session.scalar(
        select(CaregiverAuthorization)
        .where(
            CaregiverAuthorization.subject_user_id == subject_user_id,
            CaregiverAuthorization.caregiver_user_id == caregiver_user_id,
        )
        .order_by(CaregiverAuthorization.granted_at.desc())
    )
    if current is not None and current.revoked_at is None:
        return current
    authorization = CaregiverAuthorization(
        authorization_id=uuid4(),
        subject_user_id=subject_user_id,
        caregiver_user_id=caregiver_user_id,
        granted_at=utc_now(),
        revoked_at=None,
    )
    session.add(authorization)
    return authorization


def revoke_caregiver_access(
    session: Session, *, subject_user_id: UUID, authorization_id: UUID
) -> CaregiverAuthorization:
    authorization = session.scalar(
        select(CaregiverAuthorization).where(
            CaregiverAuthorization.authorization_id == authorization_id,
            CaregiverAuthorization.subject_user_id == subject_user_id,
        )
    )
    if authorization is None:
        raise AuthorizationServiceError("authorization was not found")
    if authorization.revoked_at is None:
        authorization.revoked_at = utc_now()
    return authorization
