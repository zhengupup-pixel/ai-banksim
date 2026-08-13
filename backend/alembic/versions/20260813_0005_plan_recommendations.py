"""Link recommendations to generated training plans.

Revision ID: 20260813_0005
Revises: 20260813_0004
Create Date: 2026-08-13
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0005"
down_revision: str | None = "20260813_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.add_column(sa.Column("plan_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_recommendations_plan_id_training_plans", "training_plans", ["plan_id"], ["id"]
        )
        batch_op.create_index("ix_recommendations_plan_id", ["plan_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("recommendations") as batch_op:
        batch_op.drop_index("ix_recommendations_plan_id")
        batch_op.drop_constraint("fk_recommendations_plan_id_training_plans", type_="foreignkey")
        batch_op.drop_column("plan_id")
