"""Add versioned rule policy to scenarios.

Revision ID: 20260813_0002
Revises: 20260813_0001
Create Date: 2026-08-13
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0002"
down_revision: str | None = "20260813_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.add_column(
            sa.Column("rule_policy", sa.JSON(), server_default=sa.text("'{}'"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("scenarios") as batch_op:
        batch_op.drop_column("rule_policy")
