"""Dashboard summary response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LatestReadingSummary(BaseModel):
    reading_id: UUID
    heart_rate_bpm: int
    observed_at: datetime
    source_kind: str


class DashboardOverview(BaseModel):
    subject_user_id: UUID
    monitoring_status: str
    latest_reading: LatestReadingSummary | None
    active_incident: UUID | None
    incident_status: str | None
    latest_update_at: datetime | None
