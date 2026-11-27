"""Caregiver authorization schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuthorizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caregiver_user_id: UUID


class AuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    authorization_id: UUID
    subject_user_id: UUID
    caregiver_user_id: UUID
    granted_at: datetime
    revoked_at: datetime | None


class AuthorizedSubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_user_id: UUID
    granted_at: datetime
    revoked_at: datetime | None


class AuthorizedSubjectsResponse(BaseModel):
    authorized_subjects: list[AuthorizedSubjectResponse]
