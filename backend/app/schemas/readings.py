"""Canonical simulated reading API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReadingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demo_run_id: UUID
    source_kind: str = Field(default="SIMULATED", min_length=1, max_length=32)
    heart_rate_bpm: int = Field(gt=0)
    observed_at: datetime
    activity_context: str | None = Field(default=None, max_length=64)
    source_record_id: str | None = Field(default=None, max_length=128)
    ingestion_idempotency_key: str = Field(min_length=1, max_length=256)


class ReadingResponse(BaseModel):
    reading_id: UUID
    demo_run_id: UUID
    accepted: bool
    detection_status: str
    anomaly_event_id: UUID | None = None
    incident_id: UUID | None = None
