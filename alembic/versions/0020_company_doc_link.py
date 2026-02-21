"""Add company_document_link and run_manifest.report_template_version.

Revision ID: 0020_company_doc_link
Revises: 0019_chunk_content_tsv_text
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0020_company_doc_link"
down_revision: str | None = "0019_chunk_content_tsv_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_document_link",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "company_id",
            "document_id",
            "tenant_id",
            name="uq_company_document_link_company_document",
        ),
    )
    op.create_index(
        "ix_company_document_link_company_id",
        "company_document_link",
        ["company_id"],
    )
    op.create_index(
        "ix_company_document_link_document_id",
        "company_document_link",
        ["document_id"],
    )
    op.create_index(
        "ix_company_document_link_tenant_id",
        "company_document_link",
        ["tenant_id"],
    )
    op.add_column(
        "run_manifest",
        sa.Column(
            "report_template_version",
            sa.String(length=64),
            nullable=False,
            server_default="legacy_v1",
        ),
    )


def downgrade() -> None:
    op.drop_column("run_manifest", "report_template_version")
    op.drop_index("ix_company_document_link_tenant_id", table_name="company_document_link")
    op.drop_index("ix_company_document_link_document_id", table_name="company_document_link")
    op.drop_index("ix_company_document_link_company_id", table_name="company_document_link")
    op.drop_table("company_document_link")
