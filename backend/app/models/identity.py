"""Identity anchor model; authentication fields are intentionally absent."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    demo_runs: Mapped[list[DemoRun]] = relationship(
        "DemoRun",
        back_populates="subject_user",
        foreign_keys="DemoRun.subject_user_id",
    )
    health_readings: Mapped[list[HealthReading]] = relationship(
        "HealthReading",
        back_populates="subject_user",
        foreign_keys="HealthReading.subject_user_id",
    )
    anomaly_events: Mapped[list[AnomalyEvent]] = relationship(
        "AnomalyEvent",
        back_populates="subject_user",
        foreign_keys="AnomalyEvent.subject_user_id",
    )
    incidents: Mapped[list[Incident]] = relationship(
        "Incident",
        back_populates="subject_user",
        foreign_keys="Incident.subject_user_id",
    )
    verification_responses: Mapped[list[VerificationResponse]] = relationship(
        "VerificationResponse",
        back_populates="responder_user",
        foreign_keys="VerificationResponse.responder_user_id",
    )
    timeline_actor_events: Mapped[list[IncidentTimelineEvent]] = relationship(
        "IncidentTimelineEvent",
        back_populates="actor_user",
        foreign_keys="IncidentTimelineEvent.actor_user_id",
    )


# These imports make the forward annotations available to type checkers without
# introducing runtime imports or a database/bootstrap dependency.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.models.demo import DemoRun
    from backend.app.models.incidents import (
        Incident,
        IncidentTimelineEvent,
        VerificationResponse,
    )
    from backend.app.models.readings import AnomalyEvent, HealthReading
