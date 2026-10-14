"""Create the initial face check-in schema.

Revision ID: 0001
Revises:
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

pk_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", pk_type, sa.Identity(always=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "face_profiles",
        sa.Column("id", pk_type, sa.Identity(always=True), nullable=False),
        sa.Column("user_id", pk_type, nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=False),
        sa.Column("embedding_dim", sa.SmallInteger(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("embedding_dim > 0", name="ck_face_profiles_dim"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_face_profiles_user_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_face_profiles"),
    )
    op.create_index("ix_face_profiles_user_id", "face_profiles", ["user_id"], unique=False)
    op.create_table(
        "check_in_records",
        sa.Column("id", pk_type, sa.Identity(always=True), nullable=False),
        sa.Column("user_id", pk_type, nullable=True),
        sa.Column("matched_face_profile_id", pk_type, nullable=True),
        sa.Column("checkin_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "status <> 'success' OR (user_id IS NOT NULL AND similarity_score IS NOT NULL)",
            name="ck_check_in_records_success_shape",
        ),
        sa.CheckConstraint(
            "status IN ('success', 'unmatched', 'no_face')",
            name="ck_check_in_records_status",
        ),
        sa.ForeignKeyConstraint(
            ["matched_face_profile_id"],
            ["face_profiles.id"],
            name="fk_check_in_records_matched_face_profile_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_check_in_records_user_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_check_in_records"),
    )
    op.create_index(
        "ix_check_in_records_checkin_time",
        "check_in_records",
        ["checkin_time"],
        unique=False,
    )
    op.create_index(
        "ix_check_in_records_user_id_checkin_time",
        "check_in_records",
        ["user_id", "checkin_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_check_in_records_user_id_checkin_time", table_name="check_in_records")
    op.drop_index("ix_check_in_records_checkin_time", table_name="check_in_records")
    op.drop_table("check_in_records")
    op.drop_index("ix_face_profiles_user_id", table_name="face_profiles")
    op.drop_table("face_profiles")
    op.drop_table("users")
