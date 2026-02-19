"""Add document_discovery_candidate table for persisted auto-discovery decisions.

Revision ID: 0016_document_discovery_candidate
Revises: 0015_run_registry_artifact
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0016_document_discovery_candidate"
down_revision: str | None = "0015_run_registry_artifact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_discovery_candidate",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_document_discovery_candidate_company_id",
        "document_discovery_candidate",
        ["company_id"],
    )
    op.create_index(
        "ix_document_discovery_candidate_tenant_id",
        "document_discovery_candidate",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_discovery_candidate_tenant_id", table_name="document_discovery_candidate"
    )
    op.drop_index(
        "ix_document_discovery_candidate_company_id", table_name="document_discovery_candidate"
    )
    op.drop_table("document_discovery_candidate")

