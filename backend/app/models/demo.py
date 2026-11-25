"""Demo-run model and the run's generation snapshot anchor."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class DemoRun(Base):
    __tablename__ = "demo_runs"
    __table_args__ = (
        UniqueConstraint(
            "demo_run_id", "subject_user_id", name="uq_demo_runs_id_subject"
        ),
        CheckConstraint("current_generation > 0", name="generation_positive"),
        CheckConstraint(
            "scenario IN ('NORMAL', 'TRUE_ANOMALY', 'FALSE_ALARM')",
            name="scenario",
        ),
    )

    demo_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="fk_demo_runs_subject_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    start_idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    subject_user: Mapped[User] = relationship(
        "User",
        back_populates="demo_runs",
        foreign_keys=[subject_user_id],
    )
    health_readings: Mapped[list[HealthReading]] = relationship(
        "HealthReading",
        back_populates="demo_run",
        foreign_keys="[HealthReading.demo_run_id, HealthReading.subject_user_id]",
        overlaps="subject_user,health_readings",
    )
    anomaly_events: Mapped[list[AnomalyEvent]] = relationship(
        "AnomalyEvent",
        back_populates="demo_run",
        foreign_keys="[AnomalyEvent.demo_run_id, AnomalyEvent.subject_user_id]",
        overlaps="subject_user,anomaly_events",
    )
    incidents: Mapped[list[Incident]] = relationship(
        "Incident",
        back_populates="demo_run",
        foreign_keys="[Incident.demo_run_id, Incident.subject_user_id]",
        primaryjoin=(
            "and_(DemoRun.demo_run_id == Incident.demo_run_id, "
            "DemoRun.subject_user_id == Incident.subject_user_id)"
        ),
        overlaps="subject_user,incidents",
    )


Index(
    "uq_demo_runs_subject_start_key",
    DemoRun.subject_user_id,
    DemoRun.start_idempotency_key,
    unique=True,
    postgresql_where=DemoRun.start_idempotency_key.is_not(None),
)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.models.identity import User
    from backend.app.models.incidents import Incident
    from backend.app.models.readings import AnomalyEvent, HealthReading
