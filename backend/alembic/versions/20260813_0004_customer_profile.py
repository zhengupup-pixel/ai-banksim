"""Add scenario customer profiles.

Revision ID: 20260813_0004
Revises: 20260813_0003
Create Date: 2026-08-13
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0004"
down_revision: str | None = "20260813_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.add_column(
            sa.Column("customer_profile", sa.JSON(), server_default=sa.text("'{}'"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.drop_column("customer_profile")
