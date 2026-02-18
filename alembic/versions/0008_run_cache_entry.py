"""Add run hash cache table for reproducible output reuse.

Revision ID: 0008_run_cache_entry
Revises: 0007_datapoint_assessment
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008_run_cache_entry"
down_revision: str | None = "0007_datapoint_assessment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_cache_entry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("run_hash", sa.String(length=64), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("run_hash", name="uq_run_cache_entry_run_hash"),
    )
    op.create_index("ix_run_cache_entry_run_id", "run_cache_entry", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_cache_entry_run_id", table_name="run_cache_entry")
    op.drop_table("run_cache_entry")
