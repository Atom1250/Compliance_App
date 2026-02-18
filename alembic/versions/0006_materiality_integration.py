"""Add materiality topic mapping and run-level materiality table.

Revision ID: 0006_materiality
Revises: 0005_company_profile
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_materiality"
down_revision: str | None = "0005_company_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "datapoint_def",
        sa.Column("materiality_topic", sa.String(length=64), nullable=False, server_default="general"),
    )

    op.create_table(
        "run_materiality",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("is_material", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("run_id", "topic", name="uq_run_materiality_run_topic"),
    )
    op.create_index("ix_run_materiality_run_id", "run_materiality", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_materiality_run_id", table_name="run_materiality")
    op.drop_table("run_materiality")
    op.drop_column("datapoint_def", "materiality_topic")
