"""Initial system-of-record schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_document_company_id", "document", ["company_id"])

    op.create_table(
        "document_file",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_document_file_document_id", "document_file", ["document_id"])
    op.create_index("ix_document_file_sha256_hash", "document_file", ["sha256_hash"])

    op.create_table(
        "run",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_run_company_id", "run", ["company_id"])

    op.create_table(
        "run_event",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_run_event_run_id", "run_event", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_event_run_id", table_name="run_event")
    op.drop_table("run_event")

    op.drop_index("ix_run_company_id", table_name="run")
    op.drop_table("run")

    op.drop_index("ix_document_file_sha256_hash", table_name="document_file")
    op.drop_index("ix_document_file_document_id", table_name="document_file")
    op.drop_table("document_file")

    op.drop_index("ix_document_company_id", table_name="document")
    op.drop_table("document")

    op.drop_table("company")
