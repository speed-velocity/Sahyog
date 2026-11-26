"""Shared API response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: UUID
    subject_user_id: UUID
    demo_run_id: UUID | None
    run_generation: int | None
    status: str
    created_at: datetime
    updated_at: datetime
    verification_deadline_at: datetime | None
    resolved_at: datetime | None
