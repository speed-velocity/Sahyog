"""Local OAuth2 password login and registration routes."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.auth import authenticate_user, create_access_token, hash_password
from backend.app.core.clock import utc_now
from backend.app.db.session import get_db
from backend.app.models.auth import AuthIdentity
from backend.app.models.identity import User
from backend.app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserRole,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(request: RegisterRequest, session: Session = Depends(get_db)):
    if session.scalar(
        select(AuthIdentity).where(
            AuthIdentity.login_identifier == request.login_identifier
        )
    ):
        raise HTTPException(status_code=409, detail="Login identifier already exists")

    now = utc_now()
    user = User(user_id=uuid4(), created_at=now, updated_at=now)
    identity = AuthIdentity(
        user_id=user.user_id,
        login_identifier=request.login_identifier,
        password_hash=hash_password(request.password),
        role=request.role.value,
        disabled=False,
        created_at=now,
        updated_at=now,
    )
    try:
        # User must be persisted first because AuthIdentity has a foreign key
        # to users and no ORM relationship establishes the dependency.
        session.add(user)
        session.flush()
        session.add(identity)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409, detail="Login identifier already exists"
        ) from exc
    return RegisterResponse(user_id=user.user_id, role=request.role)


@router.post("/token", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db),
):
    identity = authenticate_user(session, form.username, form.password)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(
            user_id=identity.user_id, role=UserRole(identity.role)
        )
    )
