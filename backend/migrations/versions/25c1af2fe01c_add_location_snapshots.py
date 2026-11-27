"""add location snapshots

Revision ID: 25c1af2fe01c
Revises: 2f4d5b1a8c77
Create Date: 2026-11-26 13:14:22.296109
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "25c1af2fe01c"
down_revision: str | Sequence[str] | None = "2f4d5b1a8c77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_incidents_id_subject",
        "incidents",
        ["incident_id", "subject_user_id"],
    )
    op.create_table(
        "location_snapshots",
        sa.Column("location_id", sa.Uuid(), nullable=False),
        sa.Column("subject_user_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("demo_run_id", sa.Uuid(), nullable=True),
        sa.Column("run_generation", sa.BigInteger(), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("accuracy_meters", sa.Double(), nullable=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(demo_run_id IS NULL AND run_generation IS NULL) OR (demo_run_id IS NOT NULL AND run_generation IS NOT NULL)",
            name=op.f("ck_location_snapshots_run_generation_pair"),
        ),
        sa.CheckConstraint(
            "run_generation IS NULL OR run_generation > 0",
            name=op.f("ck_location_snapshots_generation_positive"),
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name=op.f("ck_location_snapshots_latitude_range"),
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name=op.f("ck_location_snapshots_longitude_range"),
        ),
        sa.CheckConstraint(
            "accuracy_meters IS NULL OR (accuracy_meters > 0 AND accuracy_meters <= 100000)",
            name=op.f("ck_location_snapshots_accuracy_range"),
        ),
        sa.CheckConstraint(
            "length(btrim(source_kind)) > 0",
            name=op.f("ck_location_snapshots_source_kind_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["demo_run_id", "subject_user_id"],
            ["demo_runs.demo_run_id", "demo_runs.subject_user_id"],
            name="fk_location_snapshots_run_subject",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id", "subject_user_id"],
            ["incidents.incident_id", "incidents.subject_user_id"],
            name="fk_location_snapshots_incident_subject",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id", "subject_user_id", "demo_run_id"],
            [
                "incidents.incident_id",
                "incidents.subject_user_id",
                "incidents.demo_run_id",
            ],
            name="fk_location_snapshots_incident_subject_run",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.user_id"],
            name="fk_location_snapshots_subject_user_id",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("location_id", name=op.f("pk_location_snapshots")),
    )
    op.create_index(
        "ix_location_snapshots_subject_captured_received",
        "location_snapshots",
        [
            "subject_user_id",
            sa.literal_column("captured_at DESC"),
            sa.literal_column("received_at DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_location_snapshots_incident_captured_received",
        "location_snapshots",
        [
            "incident_id",
            sa.literal_column("captured_at DESC"),
            sa.literal_column("received_at DESC"),
        ],
        unique=False,
        postgresql_where=sa.text("incident_id IS NOT NULL"),
    )
    op.create_index(
        "ix_location_snapshots_run_captured_received",
        "location_snapshots",
        [
            "demo_run_id",
            "run_generation",
            sa.literal_column("captured_at DESC"),
            sa.literal_column("received_at DESC"),
        ],
        unique=False,
        postgresql_where=sa.text("demo_run_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_location_snapshots_run_captured_received",
        table_name="location_snapshots",
        postgresql_where=sa.text("demo_run_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_location_snapshots_incident_captured_received",
        table_name="location_snapshots",
        postgresql_where=sa.text("incident_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_location_snapshots_subject_captured_received",
        table_name="location_snapshots",
    )
    op.drop_table("location_snapshots")
    op.drop_constraint("uq_incidents_id_subject", "incidents", type_="unique")
