"""Incident and its durable verification, escalation, and timeline records."""

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
    Text,
    UniqueConstraint,
    Uuid,
    and_,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.demo import DemoRun
from backend.app.models.identity import User
from backend.app.models.readings import AnomalyEvent


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["demo_run_id", "subject_user_id"],
            ["demo_runs.demo_run_id", "demo_runs.subject_user_id"],
            name="fk_incidents_run_subject",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["triggering_anomaly_event_id", "subject_user_id", "demo_run_id"],
            [
                "anomaly_events.anomaly_event_id",
                "anomaly_events.subject_user_id",
                "anomaly_events.demo_run_id",
            ],
            name="fk_incidents_trigger_subject_run",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        UniqueConstraint(
            "incident_id",
            "subject_user_id",
            name="uq_incidents_id_subject",
        ),
        UniqueConstraint(
            "incident_id",
            "subject_user_id",
            "demo_run_id",
            name="uq_incidents_id_subject_run",
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
        CheckConstraint(
            "triggering_anomaly_event_id IS NULL OR demo_run_id IS NOT NULL",
            name="trigger_requires_run",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="fk_incidents_subject_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    demo_run_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    run_generation: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    triggering_anomaly_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    creation_idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    verification_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    subject_user: Mapped[User] = relationship(
        "User",
        back_populates="incidents",
        foreign_keys=[subject_user_id],
    )
    demo_run: Mapped[DemoRun | None] = relationship(
        "DemoRun",
        back_populates="incidents",
        foreign_keys=[demo_run_id, subject_user_id],
        primaryjoin=and_(
            foreign(demo_run_id) == DemoRun.demo_run_id,
            subject_user_id == DemoRun.subject_user_id,
        ),
        overlaps="subject_user,incidents",
    )
    triggering_anomaly_event: Mapped[AnomalyEvent | None] = relationship(
        "AnomalyEvent",
        back_populates="triggering_incidents",
        foreign_keys=[triggering_anomaly_event_id, subject_user_id, demo_run_id],
        primaryjoin=and_(
            foreign(triggering_anomaly_event_id) == AnomalyEvent.anomaly_event_id,
            subject_user_id == AnomalyEvent.subject_user_id,
            demo_run_id == AnomalyEvent.demo_run_id,
        ),
        overlaps="incidents,subject_user,demo_run,triggering_incidents",
    )
    evidence_links: Mapped[list[IncidentAnomalyEvent]] = relationship(
        "IncidentAnomalyEvent",
        back_populates="incident",
        foreign_keys="[IncidentAnomalyEvent.incident_id, IncidentAnomalyEvent.subject_user_id, IncidentAnomalyEvent.demo_run_id]",
        primaryjoin=(
            "and_(Incident.incident_id == IncidentAnomalyEvent.incident_id, "
            "Incident.subject_user_id == IncidentAnomalyEvent.subject_user_id, "
            "Incident.demo_run_id == IncidentAnomalyEvent.demo_run_id)"
        ),
        overlaps="subject_user,demo_run,triggering_anomaly_event,incident_evidence_links",
    )
    verification_responses: Mapped[list[VerificationResponse]] = relationship(
        "VerificationResponse",
        back_populates="incident",
        foreign_keys="VerificationResponse.incident_id",
    )
    escalation_attempts: Mapped[list[EscalationAttempt]] = relationship(
        "EscalationAttempt",
        back_populates="incident",
        foreign_keys="EscalationAttempt.incident_id",
    )
    timeline_events: Mapped[list[IncidentTimelineEvent]] = relationship(
        "IncidentTimelineEvent",
        back_populates="incident",
        foreign_keys="IncidentTimelineEvent.incident_id",
    )


class IncidentAnomalyEvent(Base):
    __tablename__ = "incident_anomaly_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["incident_id", "subject_user_id", "demo_run_id"],
            [
                "incidents.incident_id",
                "incidents.subject_user_id",
                "incidents.demo_run_id",
            ],
            name="fk_incident_anomaly_events_incident_subject_run",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["anomaly_event_id", "subject_user_id", "demo_run_id"],
            [
                "anomaly_events.anomaly_event_id",
                "anomaly_events.subject_user_id",
                "anomaly_events.demo_run_id",
            ],
            name="fk_incident_anomaly_events_event_subject_run",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
    )

    incident_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    anomaly_event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    demo_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    evidence_role: Mapped[str] = mapped_column(Text, nullable=False)
    associated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    incident: Mapped[Incident] = relationship(
        "Incident",
        back_populates="evidence_links",
        foreign_keys=[incident_id, subject_user_id, demo_run_id],
        primaryjoin=and_(
            incident_id == Incident.incident_id,
            subject_user_id == Incident.subject_user_id,
            demo_run_id == Incident.demo_run_id,
        ),
        overlaps="demo_run,subject_user,triggering_anomaly_event,incident_evidence_links",
    )
    anomaly_event: Mapped[AnomalyEvent] = relationship(
        "AnomalyEvent",
        back_populates="incident_evidence_links",
        foreign_keys=[anomaly_event_id, subject_user_id, demo_run_id],
        primaryjoin=and_(
            anomaly_event_id == AnomalyEvent.anomaly_event_id,
            subject_user_id == AnomalyEvent.subject_user_id,
            demo_run_id == AnomalyEvent.demo_run_id,
        ),
        overlaps="demo_run,subject_user,triggering_incidents,evidence_links,incident",
    )


class VerificationResponse(Base):
    __tablename__ = "verification_responses"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "idempotency_key",
            name="uq_verification_responses_incident_key",
        ),
    )

    verification_response_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "incidents.incident_id",
            name="fk_verification_responses_incident",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    responder_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="fk_verification_responses_responder",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    response_value: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    request_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped[Incident] = relationship(
        "Incident", back_populates="verification_responses", foreign_keys=[incident_id]
    )
    responder_user: Mapped[User] = relationship(
        "User",
        back_populates="verification_responses",
        foreign_keys=[responder_user_id],
    )


class EscalationAttempt(Base):
    __tablename__ = "escalation_attempts"
    __table_args__ = (
        UniqueConstraint(
            "escalation_attempt_id",
            "incident_id",
            name="uq_escalation_attempts_id_incident",
        ),
        UniqueConstraint(
            "incident_id",
            "idempotency_key",
            name="uq_escalation_attempts_incident_key",
        ),
    )

    escalation_attempt_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "incidents.incident_id",
            name="fk_escalation_attempts_incident",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)

    incident: Mapped[Incident] = relationship(
        "Incident", back_populates="escalation_attempts", foreign_keys=[incident_id]
    )


class IncidentTimelineEvent(Base):
    __tablename__ = "incident_timeline_events"
    __table_args__ = (
        UniqueConstraint(
            "incident_id",
            "event_idempotency_key",
            name="uq_incident_timeline_events_incident_key",
        ),
    )

    timeline_event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True
    )
    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "incidents.incident_id",
            name="fk_incident_timeline_events_incident",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="fk_incident_timeline_events_actor",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=True,
    )
    event_idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped[Incident] = relationship(
        "Incident", back_populates="timeline_events", foreign_keys=[incident_id]
    )
    actor_user: Mapped[User | None] = relationship(
        "User",
        back_populates="timeline_actor_events",
        foreign_keys=[actor_user_id],
    )


Index(
    "uq_incidents_subject_creation_key",
    Incident.subject_user_id,
    Incident.creation_idempotency_key,
    unique=True,
    postgresql_where=Incident.creation_idempotency_key.is_not(None),
)
Index(
    "ix_incidents_subject_status_created",
    Incident.subject_user_id,
    Incident.status,
    Incident.created_at.desc(),
)
Index("ix_incidents_run_created", Incident.demo_run_id, Incident.created_at)
Index(
    "uq_incident_anomaly_events_one_trigger_per_incident",
    IncidentAnomalyEvent.incident_id,
    unique=True,
    postgresql_where=IncidentAnomalyEvent.evidence_role == "TRIGGERING",
)
Index(
    "ix_incident_anomaly_events_event_incident",
    IncidentAnomalyEvent.anomaly_event_id,
    IncidentAnomalyEvent.incident_id,
)
Index(
    "ix_verification_responses_incident_time",
    VerificationResponse.incident_id,
    VerificationResponse.responded_at,
)
Index(
    "ix_escalation_attempts_incident_time",
    EscalationAttempt.incident_id,
    EscalationAttempt.started_at,
)
Index(
    "ix_incident_timeline_events_incident_time",
    IncidentTimelineEvent.incident_id,
    IncidentTimelineEvent.occurred_at,
    IncidentTimelineEvent.timeline_event_id,
)
