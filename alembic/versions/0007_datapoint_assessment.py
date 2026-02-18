"""Add datapoint assessment storage table.

Revision ID: 0007_datapoint_assessment
Revises: 0006_materiality
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007_datapoint_assessment"
down_revision: str | None = "0006_materiality"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datapoint_assessment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("datapoint_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("evidence_chunk_ids", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("retrieval_params", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("run_id", "datapoint_key", name="uq_assessment_run_datapoint"),
    )
    op.create_index("ix_datapoint_assessment_run_id", "datapoint_assessment", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_datapoint_assessment_run_id", table_name="datapoint_assessment")
    op.drop_table("datapoint_assessment")
