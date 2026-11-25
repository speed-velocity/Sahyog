"""add local authentication and caregiver authorization

Revision ID: 2f4d5b1a8c77
Revises: 99e748e414e3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2f4d5b1a8c77"
down_revision: str | Sequence[str] | None = "99e748e414e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_identities",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("login_identifier", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_auth_identities_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_auth_identities"),
        sa.UniqueConstraint(
            "login_identifier", name="uq_auth_identities_login_identifier"
        ),
    )
    op.create_table(
        "caregiver_authorizations",
        sa.Column("authorization_id", sa.Uuid(), nullable=False),
        sa.Column("subject_user_id", sa.Uuid(), nullable=False),
        sa.Column("caregiver_user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["caregiver_user_id"],
            ["users.user_id"],
            name="fk_caregiver_authorizations_caregiver_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.user_id"],
            name="fk_caregiver_authorizations_subject_user_id",
            ondelete="RESTRICT",
            onupdate="NO ACTION",
        ),
        sa.PrimaryKeyConstraint("authorization_id", name="pk_caregiver_authorizations"),
    )
    op.create_index(
        "uq_caregiver_authorizations_active_pair",
        "caregiver_authorizations",
        ["subject_user_id", "caregiver_user_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_caregiver_authorizations_active_pair",
        table_name="caregiver_authorizations",
    )
    op.drop_table("caregiver_authorizations")
    op.drop_table("auth_identities")
