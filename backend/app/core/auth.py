"""JWT authentication and caregiver authorization dependencies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.models.auth import AuthIdentity, CaregiverAuthorization
from backend.app.schemas.auth import AuthenticatedPrincipal, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
password_hash = PasswordHash.recommended()
dummy_password_hash = password_hash.hash("sahyog-dummy-password")


def _secret_key() -> str:
    secret = get_settings().auth_secret_key
    if len(secret) < 32:
        raise RuntimeError("SAHYOG_AUTH_SECRET_KEY must contain at least 32 characters")
    return secret


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def authenticate_user(
    session: Session, login_identifier: str, password: str
) -> AuthIdentity | None:
    identity = session.scalar(
        select(AuthIdentity).where(AuthIdentity.login_identifier == login_identifier)
    )
    if identity is None:
        password_hash.verify(password, dummy_password_hash)
        return None
    if identity.disabled or not verify_password(password, identity.password_hash):
        return None
    return identity


def create_access_token(*, user_id: UUID, role: UserRole) -> str:
    now = datetime.now(UTC)
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iss": settings.auth_issuer,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, _secret_key(), algorithm="HS256")


def get_current_principal(
    token: str = Depends(oauth2_scheme),
) -> AuthenticatedPrincipal:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            _secret_key(),
            algorithms=["HS256"],
            issuer=get_settings().auth_issuer,
            options={"require": ["sub", "role", "iss", "iat", "exp", "jti"]},
        )
        return AuthenticatedPrincipal(
            user_id=UUID(payload["sub"]), role=UserRole(payload["role"])
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise unauthorized from exc


def require_active_principal(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    identity = session.get(AuthIdentity, principal.user_id)
    if identity is None or identity.disabled:
        raise HTTPException(status_code=401, detail="User is inactive")
    return principal


def can_access_subject(
    session: Session, principal: AuthenticatedPrincipal, subject_user_id: UUID
) -> bool:
    if principal.user_id == subject_user_id:
        return True
    if principal.role is not UserRole.CAREGIVER:
        return False
    return (
        session.scalar(
            select(CaregiverAuthorization.authorization_id).where(
                CaregiverAuthorization.subject_user_id == subject_user_id,
                CaregiverAuthorization.caregiver_user_id == principal.user_id,
                CaregiverAuthorization.revoked_at.is_(None),
            )
        )
        is not None
    )
