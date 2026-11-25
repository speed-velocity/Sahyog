"""Authentication credentials and caregiver authorization records."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AuthIdentity(Base):
    __tablename__ = "auth_identities"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="NO ACTION"),
        primary_key=True,
    )
    login_identifier: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CaregiverAuthorization(Base):
    __tablename__ = "caregiver_authorizations"

    authorization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="NO ACTION"),
        nullable=False,
    )
    caregiver_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="NO ACTION"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


Index(
    "uq_caregiver_authorizations_active_pair",
    CaregiverAuthorization.subject_user_id,
    CaregiverAuthorization.caregiver_user_id,
    unique=True,
    postgresql_where=CaregiverAuthorization.revoked_at.is_(None),
)
