"""Add run manifest table.

Revision ID: 0010_run_manifest
Revises: 0009_tenant_isolation
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0010_run_manifest"
down_revision: str | None = "0009_tenant_isolation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "run_manifest",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("document_hashes", sa.Text(), nullable=False),
        sa.Column("bundle_id", sa.String(length=128), nullable=False),
        sa.Column("bundle_version", sa.String(length=64), nullable=False),
        sa.Column("retrieval_params", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("git_sha", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index("ix_run_manifest_run_id", "run_manifest", ["run_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_run_manifest_run_id", table_name="run_manifest")
    op.drop_table("run_manifest")
