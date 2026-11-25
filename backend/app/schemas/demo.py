"""Demo-run API schemas."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Scenario(StrEnum):
    NORMAL = "NORMAL"
    TRUE_ANOMALY = "TRUE_ANOMALY"
    FALSE_ALARM = "FALSE_ALARM"


class DemoRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: Scenario
    start_idempotency_key: str = Field(min_length=1, max_length=256)


class DemoRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    demo_run_id: UUID
    subject_user_id: UUID
    scenario: Scenario
    status: str
    outcome: str | None
    current_generation: int
    started_at: datetime
    completed_at: datetime | None
    reset_at: datetime | None
