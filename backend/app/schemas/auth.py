"""Authentication and authorization API schemas."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserRole(StrEnum):
    SUBJECT = "SUBJECT"
    CAREGIVER = "CAREGIVER"


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login_identifier: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=12, max_length=256)
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    user_id: UUID
    role: UserRole


class AuthenticatedPrincipal(BaseModel):
    user_id: UUID
    role: UserRole
