"""Add regulatory_source_document table for curated source register ingestion.

Revision ID: 0021_regulatory_source_document
Revises: 0020_company_doc_link
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0021_regulatory_source_document"
down_revision: str | None = "0020_company_doc_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    raw_row_json_type: sa.types.TypeEngine = (
        postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()
    )
    timestamp_default = sa.text("now()") if is_postgres else sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "regulatory_source_document",
        sa.Column("record_id", sa.Text(), primary_key=True),
        sa.Column("jurisdiction", sa.Text(), nullable=False),
        sa.Column("document_name", sa.Text(), nullable=False),
        sa.Column("document_type", sa.Text(), nullable=True),
        sa.Column("framework_level", sa.Text(), nullable=True),
        sa.Column("legal_reference", sa.Text(), nullable=True),
        sa.Column("issuing_body", sa.Text(), nullable=True),
        sa.Column("supervisory_authority", sa.Text(), nullable=True),
        sa.Column("official_source_url", sa.Text(), nullable=True),
        sa.Column("source_format", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("scope_applicability", sa.Text(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("last_checked_date", sa.Date(), nullable=True),
        sa.Column("update_frequency", sa.Text(), nullable=True),
        sa.Column("version_identifier", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("keywords_tags", sa.Text(), nullable=True),
        sa.Column("notes_for_db_tagging", sa.Text(), nullable=True),
        sa.Column("source_sheets", sa.Text(), nullable=True),
        sa.Column("row_checksum", sa.Text(), nullable=False),
        sa.Column("raw_row_json", raw_row_json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=timestamp_default, nullable=False),
    )
    op.create_index(
        "idx_regsrc_jurisdiction",
        "regulatory_source_document",
        ["jurisdiction"],
    )
    op.create_index(
        "idx_regsrc_framework_level",
        "regulatory_source_document",
        ["framework_level"],
    )
    op.create_index(
        "idx_regsrc_status",
        "regulatory_source_document",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("idx_regsrc_status", table_name="regulatory_source_document")
    op.drop_index("idx_regsrc_framework_level", table_name="regulatory_source_document")
    op.drop_index("idx_regsrc_jurisdiction", table_name="regulatory_source_document")
    op.drop_table("regulatory_source_document")
