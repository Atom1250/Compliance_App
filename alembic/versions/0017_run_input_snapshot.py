"""Add run_input_snapshot table for immutable run input freezing.

Revision ID: 0017_run_input_snapshot
Revises: 0016_discovery_candidate
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0017_run_input_snapshot"
down_revision: str | None = "0016_discovery_candidate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_input_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_run_input_snapshot_run_id", "run_input_snapshot", ["run_id"], unique=True)
    op.create_index("ix_run_input_snapshot_tenant_id", "run_input_snapshot", ["tenant_id"])
    op.create_index("ix_run_input_snapshot_checksum", "run_input_snapshot", ["checksum"])


def downgrade() -> None:
    op.drop_index("ix_run_input_snapshot_checksum", table_name="run_input_snapshot")
    op.drop_index("ix_run_input_snapshot_tenant_id", table_name="run_input_snapshot")
    op.drop_index("ix_run_input_snapshot_run_id", table_name="run_input_snapshot")
    op.drop_table("run_input_snapshot")
