"""Offline schema, model, and Alembic migration tests for location snapshots."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from backend.app import models
from backend.app.models.incidents import Incident
from backend.app.models.location import LocationSnapshotRecord
from sqlalchemy import BigInteger, DateTime, Double, Text, UniqueConstraint, Uuid


def _alembic_config() -> Config:
    repo_backend = Path(__file__).resolve().parents[1]
    ini_path = repo_backend / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(repo_backend / "migrations"))
    return cfg


def test_location_snapshot_model_registered_in_metadata() -> None:
    assert hasattr(models, "LocationSnapshotRecord")
    assert "LocationSnapshotRecord" in models.__all__
    assert models.LocationSnapshotRecord is LocationSnapshotRecord
    assert "location_snapshots" in models.Base.metadata.tables

    table = models.Base.metadata.tables["location_snapshots"]
    assert table.name == "location_snapshots"


def test_location_snapshot_model_columns_match_expected_spec() -> None:
    table = LocationSnapshotRecord.__table__
    cols = table.c

    expected_types = {
        "location_id": Uuid,
        "subject_user_id": Uuid,
        "incident_id": Uuid,
        "demo_run_id": Uuid,
        "run_generation": BigInteger,
        "latitude": Double,
        "longitude": Double,
        "accuracy_meters": Double,
        "source_kind": Text,
        "captured_at": DateTime,
        "received_at": DateTime,
    }

    assert set(cols.keys()) == set(expected_types.keys())

    for col_name, expected_type in expected_types.items():
        assert isinstance(cols[col_name].type, expected_type), (
            f"Column {col_name} type {type(cols[col_name].type)} does not match {expected_type}"
        )

    # Check timezone on datetimes
    assert cols["captured_at"].type.timezone is True
    assert cols["received_at"].type.timezone is True

    # Check nullability
    nullable_cols = {"incident_id", "demo_run_id", "run_generation", "accuracy_meters"}
    for col_name in expected_types:
        if col_name in nullable_cols:
            assert cols[col_name].nullable is True
        else:
            assert cols[col_name].nullable is False

    assert cols["location_id"].primary_key is True


def test_location_snapshot_constraint_and_index_names() -> None:
    table = LocationSnapshotRecord.__table__

    # Check check-constraints
    ck_names = {
        ck.name for ck in table.constraints if ck.name and ck.name.startswith("ck_")
    }
    expected_cks = {
        "ck_location_snapshots_run_generation_pair",
        "ck_location_snapshots_generation_positive",
        "ck_location_snapshots_latitude_range",
        "ck_location_snapshots_longitude_range",
        "ck_location_snapshots_accuracy_range",
        "ck_location_snapshots_source_kind_nonempty",
    }
    assert expected_cks <= ck_names

    # Check foreign keys
    fk_names = {fk.name for fk in table.foreign_key_constraints}
    expected_fks = {
        "fk_location_snapshots_subject_user_id",
        "fk_location_snapshots_run_subject",
        "fk_location_snapshots_incident_subject",
        "fk_location_snapshots_incident_subject_run",
    }
    assert expected_fks == fk_names

    # Check indexes
    idx_names = {idx.name for idx in table.indexes}
    expected_idxs = {
        "ix_location_snapshots_subject_captured_received",
        "ix_location_snapshots_incident_captured_received",
        "ix_location_snapshots_run_captured_received",
    }
    assert expected_idxs == idx_names


def test_incidents_model_has_unique_constraint_for_composite_fks() -> None:
    table = Incident.__table__
    uq_names = {c.name for c in table.constraints if isinstance(c, UniqueConstraint)}

    assert "uq_incidents_id_subject" in uq_names
    assert "uq_incidents_id_subject_run" in uq_names

    uq_id_subject = next(
        c for c in table.constraints if c.name == "uq_incidents_id_subject"
    )
    assert [col.name for col in uq_id_subject.columns] == [
        "incident_id",
        "subject_user_id",
    ]


def test_alembic_revision_chain_and_heads() -> None:
    cfg = _alembic_config()
    scripts = ScriptDirectory.from_config(cfg)

    heads = scripts.get_heads()
    assert heads == ["25c1af2fe01c"], (
        f"Expected single head 25c1af2fe01c, found {heads}"
    )

    head_rev = scripts.get_revision("25c1af2fe01c")
    assert head_rev is not None
    assert head_rev.down_revision == "2f4d5b1a8c77"

    pred_rev = scripts.get_revision("2f4d5b1a8c77")
    assert pred_rev is not None
    assert pred_rev.down_revision == "99e748e414e3"


def test_offline_upgrade_sql_generation_and_order() -> None:
    cfg = _alembic_config()
    buf = io.StringIO()

    with contextlib.redirect_stdout(buf):
        command.upgrade(cfg, "2f4d5b1a8c77:25c1af2fe01c", sql=True)

    sql = buf.getvalue()
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql

    # Verify unique constraint created on incidents
    assert (
        "ALTER TABLE incidents ADD CONSTRAINT uq_incidents_id_subject UNIQUE (incident_id, subject_user_id);"
        in sql
    )

    # Verify table creation and columns
    assert "CREATE TABLE location_snapshots (" in sql
    assert "location_id UUID NOT NULL" in sql
    assert "subject_user_id UUID NOT NULL" in sql
    assert "latitude DOUBLE PRECISION NOT NULL" in sql
    assert "longitude DOUBLE PRECISION NOT NULL" in sql
    assert "accuracy_meters DOUBLE PRECISION" in sql
    assert "source_kind TEXT NOT NULL" in sql
    assert "captured_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "received_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql

    # Verify indexes
    assert "CREATE INDEX ix_location_snapshots_subject_captured_received" in sql
    assert "CREATE INDEX ix_location_snapshots_incident_captured_received" in sql
    assert "WHERE incident_id IS NOT NULL" in sql
    assert "CREATE INDEX ix_location_snapshots_run_captured_received" in sql
    assert "WHERE demo_run_id IS NOT NULL" in sql

    # Verify order: constraint on incidents must precede location_snapshots table creation
    uq_pos = sql.index("ALTER TABLE incidents ADD CONSTRAINT uq_incidents_id_subject")
    create_table_pos = sql.index("CREATE TABLE location_snapshots")
    assert uq_pos < create_table_pos, (
        "uq_incidents_id_subject must be created before location_snapshots"
    )


def test_offline_downgrade_sql_generation_and_order() -> None:
    cfg = _alembic_config()
    buf = io.StringIO()

    with contextlib.redirect_stdout(buf):
        command.downgrade(cfg, "25c1af2fe01c:2f4d5b1a8c77", sql=True)

    sql = buf.getvalue()
    assert "BEGIN;" in sql
    assert "COMMIT;" in sql

    # Verify index drops, table drop, and constraint removal
    assert "DROP INDEX ix_location_snapshots_run_captured_received;" in sql
    assert "DROP INDEX ix_location_snapshots_incident_captured_received;" in sql
    assert "DROP INDEX ix_location_snapshots_subject_captured_received;" in sql
    assert "DROP TABLE location_snapshots;" in sql
    assert "ALTER TABLE incidents DROP CONSTRAINT uq_incidents_id_subject;" in sql

    # Verify safe reverse order: indexes dropped before table, table dropped before parent unique constraint
    drop_idx_pos = sql.index(
        "DROP INDEX ix_location_snapshots_subject_captured_received"
    )
    drop_table_pos = sql.index("DROP TABLE location_snapshots")
    drop_uq_pos = sql.index(
        "ALTER TABLE incidents DROP CONSTRAINT uq_incidents_id_subject"
    )

    assert drop_idx_pos < drop_table_pos, (
        "Indexes must be dropped before location_snapshots table"
    )
    assert drop_table_pos < drop_uq_pos, (
        "location_snapshots must be dropped before uq_incidents_id_subject"
    )


def test_location_snapshot_foreign_keys_ondelete_restrict() -> None:
    """Verify all foreign key constraints on location_snapshots specify ON DELETE RESTRICT."""
    from backend.app.models.location import LocationSnapshotRecord

    fk_by_name = {
        fk.name: fk for fk in LocationSnapshotRecord.__table__.foreign_key_constraints
    }

    assert "fk_location_snapshots_run_subject" in fk_by_name
    assert fk_by_name["fk_location_snapshots_run_subject"].ondelete == "RESTRICT"

    assert "fk_location_snapshots_incident_subject" in fk_by_name
    assert fk_by_name["fk_location_snapshots_incident_subject"].ondelete == "RESTRICT"

    assert "fk_location_snapshots_incident_subject_run" in fk_by_name
    assert (
        fk_by_name["fk_location_snapshots_incident_subject_run"].ondelete == "RESTRICT"
    )

    subject_fks = [
        fk
        for fk in LocationSnapshotRecord.__table__.foreign_keys
        if fk.name == "fk_location_snapshots_subject_user_id"
    ]
    assert len(subject_fks) == 1
    assert subject_fks[0].ondelete == "RESTRICT"
