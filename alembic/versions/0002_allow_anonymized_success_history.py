"""Allow successful history rows to be anonymized after user deletion.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("check_in_records") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_check_in_records_ck_check_in_records_success_shape"),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_check_in_records_success_score"),
            "status <> 'success' OR similarity_score IS NOT NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("check_in_records") as batch_op:
        batch_op.drop_constraint(op.f("ck_check_in_records_success_score"), type_="check")
        batch_op.create_check_constraint(
            op.f("ck_check_in_records_ck_check_in_records_success_shape"),
            "status <> 'success' OR (user_id IS NOT NULL AND similarity_score IS NOT NULL)",
        )
