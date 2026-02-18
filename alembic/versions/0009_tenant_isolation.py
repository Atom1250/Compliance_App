"""Add tenant isolation columns.

Revision ID: 0009_tenant_isolation
Revises: 0008_run_cache_entry
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009_tenant_isolation"
down_revision: str | None = "0008_run_cache_entry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
    )
    op.add_column(
        "document",
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
    )
    op.add_column(
        "run",
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
    )
    op.create_index("ix_company_tenant_id", "company", ["tenant_id"])
    op.create_index("ix_document_tenant_id", "document", ["tenant_id"])
    op.create_index("ix_run_tenant_id", "run", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_run_tenant_id", table_name="run")
    op.drop_index("ix_document_tenant_id", table_name="document")
    op.drop_index("ix_company_tenant_id", table_name="company")
    op.drop_column("run", "tenant_id")
    op.drop_column("document", "tenant_id")
    op.drop_column("company", "tenant_id")
