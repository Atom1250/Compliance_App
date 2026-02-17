"""Add document_page table for deterministic extracted page text.

Revision ID: 0002_document_page
Revises: 0001_initial
Create Date: 2026-02-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_document_page"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_page",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_page_doc_page"),
    )
    op.create_index("ix_document_page_document_id", "document_page", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_document_page_document_id", table_name="document_page")
    op.drop_table("document_page")
