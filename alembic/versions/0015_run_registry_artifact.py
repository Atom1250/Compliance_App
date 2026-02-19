"""Add run_registry_artifact table for run-scoped registry outputs.

Revision ID: 0015_run_registry_artifact
Revises: 0014_company_juris_compiler_mode
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0015_run_registry_artifact"
down_revision: str | None = "0014_company_juris_compiler_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_registry_artifact",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("artifact_key", sa.String(length=64), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_run_registry_artifact_run_id", "run_registry_artifact", ["run_id"])
    op.create_index("ix_run_registry_artifact_tenant_id", "run_registry_artifact", ["tenant_id"])
    op.create_index("ix_run_registry_artifact_checksum", "run_registry_artifact", ["checksum"])
    op.create_index(
        "ux_run_registry_artifact_run_tenant_key",
        "run_registry_artifact",
        ["run_id", "tenant_id", "artifact_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_run_registry_artifact_run_tenant_key", table_name="run_registry_artifact")
    op.drop_index("ix_run_registry_artifact_checksum", table_name="run_registry_artifact")
    op.drop_index("ix_run_registry_artifact_tenant_id", table_name="run_registry_artifact")
    op.drop_index("ix_run_registry_artifact_run_id", table_name="run_registry_artifact")
    op.drop_table("run_registry_artifact")
