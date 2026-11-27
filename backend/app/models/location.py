"""Persisted location snapshot model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Text,
    Uuid,
    and_,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.demo import DemoRun
from backend.app.models.identity import User
from backend.app.models.incidents import Incident


class LocationSnapshotRecord(Base):
    """Append-only persisted location snapshot anchored to a subject, run, or incident."""

    __tablename__ = "location_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["demo_run_id", "subject_user_id"],
            ["demo_runs.demo_run_id", "demo_runs.subject_user_id"],
            name="fk_location_snapshots_run_subject",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["incident_id", "subject_user_id"],
            ["incidents.incident_id", "incidents.subject_user_id"],
            name="fk_location_snapshots_incident_subject",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["incident_id", "subject_user_id", "demo_run_id"],
            [
                "incidents.incident_id",
                "incidents.subject_user_id",
                "incidents.demo_run_id",
            ],
            name="fk_location_snapshots_incident_subject_run",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
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
            "latitude >= -90 AND latitude <= 90",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="longitude_range",
        ),
        CheckConstraint(
            "accuracy_meters IS NULL OR "
            "(accuracy_meters > 0 AND accuracy_meters <= 100000)",
            name="accuracy_range",
        ),
        CheckConstraint(
            "length(btrim(source_kind)) > 0",
            name="source_kind_nonempty",
        ),
    )

    location_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    subject_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="fk_location_snapshots_subject_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        nullable=False,
    )
    incident_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    demo_run_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    run_generation: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    accuracy_meters: Mapped[float | None] = mapped_column(Double, nullable=True)
    source_kind: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    subject_user: Mapped[User] = relationship(
        "User",
        foreign_keys=[subject_user_id],
    )
    demo_run: Mapped[DemoRun | None] = relationship(
        "DemoRun",
        foreign_keys=[demo_run_id, subject_user_id],
        primaryjoin=and_(
            foreign(demo_run_id) == DemoRun.demo_run_id,
            subject_user_id == DemoRun.subject_user_id,
        ),
        overlaps="subject_user",
    )
    incident: Mapped[Incident | None] = relationship(
        "Incident",
        foreign_keys=[incident_id, subject_user_id],
        primaryjoin=and_(
            foreign(incident_id) == Incident.incident_id,
            subject_user_id == Incident.subject_user_id,
        ),
        overlaps="demo_run,subject_user",
    )


Index(
    "ix_location_snapshots_subject_captured_received",
    LocationSnapshotRecord.subject_user_id,
    LocationSnapshotRecord.captured_at.desc(),
    LocationSnapshotRecord.received_at.desc(),
)
Index(
    "ix_location_snapshots_incident_captured_received",
    LocationSnapshotRecord.incident_id,
    LocationSnapshotRecord.captured_at.desc(),
    LocationSnapshotRecord.received_at.desc(),
    postgresql_where=LocationSnapshotRecord.incident_id.is_not(None),
)
Index(
    "ix_location_snapshots_run_captured_received",
    LocationSnapshotRecord.demo_run_id,
    LocationSnapshotRecord.run_generation,
    LocationSnapshotRecord.captured_at.desc(),
    LocationSnapshotRecord.received_at.desc(),
    postgresql_where=LocationSnapshotRecord.demo_run_id.is_not(None),
)
