"""Canonical simulated reading and detector-event models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class HealthReading(Base):
    __tablename__ = "health_readings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["demo_run_id", "subject_user_id"],
            ["demo_runs.demo_run_id", "demo_runs.subject_user_id"],
            name="fk_health_readings_run_subject",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        UniqueConstraint(
            "reading_id",
            "subject_user_id",
            "demo_run_id",
            name="uq_health_readings_id_subject_run",
        ),
        CheckConstraint(
            "(demo_run_id IS NULL AND run_generation IS NULL) OR "
            "(demo_run_id IS NOT NULL AND run_generation IS NOT NULL)",
            name="run_generation_pair",
        ),
        CheckConstraint(
            "run_generation IS NULL OR run_generation > 0",
            name="generation_positive",
        ),
        CheckConstraint("heart_rate_bpm > 0", name="bpm_positive"),
    )

    reading_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="fk_health_readings_subject_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    demo_run_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    run_generation: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    heart_rate_bpm: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    activity_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    subject_user: Mapped[User] = relationship(
        "User",
        back_populates="health_readings",
        foreign_keys=[subject_user_id],
    )
    demo_run: Mapped[DemoRun | None] = relationship(
        "DemoRun",
        back_populates="health_readings",
        foreign_keys=[demo_run_id, subject_user_id],
        overlaps="subject_user,health_readings",
    )


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["demo_run_id", "subject_user_id"],
            ["demo_runs.demo_run_id", "demo_runs.subject_user_id"],
            name="fk_anomaly_events_run_subject",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        UniqueConstraint(
            "anomaly_event_id",
            "subject_user_id",
            "demo_run_id",
            name="uq_anomaly_events_id_subject_run",
        ),
        CheckConstraint("run_generation > 0", name="generation_positive"),
        UniqueConstraint(
            "demo_run_id",
            "run_generation",
            "dedupe_key",
            name="uq_anomaly_events_run_generation_dedupe",
        ),
    )

    anomaly_event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="fk_anomaly_events_subject_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    demo_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    run_generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    detector_result: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    detector_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)

    subject_user: Mapped[User] = relationship(
        "User",
        back_populates="anomaly_events",
        foreign_keys=[subject_user_id],
    )
    demo_run: Mapped[DemoRun] = relationship(
        "DemoRun",
        back_populates="anomaly_events",
        foreign_keys=[demo_run_id, subject_user_id],
        overlaps="subject_user,anomaly_events",
    )
    triggering_incidents: Mapped[list[Incident]] = relationship(
        "Incident",
        back_populates="triggering_anomaly_event",
        foreign_keys="[Incident.triggering_anomaly_event_id, Incident.subject_user_id, Incident.demo_run_id]",
        primaryjoin=(
            "and_(AnomalyEvent.anomaly_event_id == Incident.triggering_anomaly_event_id, "
            "AnomalyEvent.subject_user_id == Incident.subject_user_id, "
            "AnomalyEvent.demo_run_id == Incident.demo_run_id)"
        ),
        overlaps="incidents,subject_user,demo_run",
    )
    incident_evidence_links: Mapped[list[IncidentAnomalyEvent]] = relationship(
        "IncidentAnomalyEvent",
        back_populates="anomaly_event",
        foreign_keys="[IncidentAnomalyEvent.anomaly_event_id, IncidentAnomalyEvent.subject_user_id, IncidentAnomalyEvent.demo_run_id]",
        primaryjoin=(
            "and_(AnomalyEvent.anomaly_event_id == IncidentAnomalyEvent.anomaly_event_id, "
            "AnomalyEvent.subject_user_id == IncidentAnomalyEvent.subject_user_id, "
            "AnomalyEvent.demo_run_id == IncidentAnomalyEvent.demo_run_id)"
        ),
        overlaps="incident_links,subject_user,demo_run,triggering_incidents",
    )


Index(
    "uq_health_readings_subject_ingestion_key",
    HealthReading.subject_user_id,
    HealthReading.ingestion_idempotency_key,
    unique=True,
    postgresql_where=HealthReading.ingestion_idempotency_key.is_not(None),
)
Index(
    "ix_health_readings_subject_observed",
    HealthReading.subject_user_id,
    HealthReading.observed_at.desc(),
)
Index(
    "ix_health_readings_run_observed",
    HealthReading.demo_run_id,
    HealthReading.observed_at,
)
Index(
    "ix_anomaly_events_subject_detected",
    AnomalyEvent.subject_user_id,
    AnomalyEvent.detected_at.desc(),
)
Index(
    "ix_anomaly_events_run_generation_detected",
    AnomalyEvent.demo_run_id,
    AnomalyEvent.run_generation,
    AnomalyEvent.detected_at,
)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.models.demo import DemoRun
    from backend.app.models.identity import User
    from backend.app.models.incidents import Incident, IncidentAnomalyEvent
