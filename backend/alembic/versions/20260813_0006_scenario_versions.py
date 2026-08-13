"""Add scenario version audit history.

Revision ID: 20260813_0006
Revises: 20260813_0005
Create Date: 2026-08-13
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0006"
down_revision: str | None = "20260813_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id", "version_number", name="uq_scenario_version_number"),
    )
    op.create_index(op.f("ix_scenario_versions_scenario_id"), "scenario_versions", ["scenario_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scenario_versions_scenario_id"), table_name="scenario_versions")
    op.drop_table("scenario_versions")
