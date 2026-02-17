"""Add chunk and embedding tables with pgvector extension bootstrap.

Revision ID: 0003_chunk_embedding
Revises: 0002_document_page
Create Date: 2026-02-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_chunk_embedding"
down_revision: str | None = "0002_document_page"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    content_tsv_type = postgresql.TSVECTOR() if is_postgres else sa.Text()

    op.create_table(
        "chunk",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("document.id"), nullable=False),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_tsv", content_tsv_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("chunk_id", name="uq_chunk_chunk_id"),
    )
    op.create_index("ix_chunk_document_id", "chunk", ["document_id"])

    op.create_table(
        "embedding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("chunk.id"), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("chunk_id", "model_name", name="uq_embedding_chunk_model"),
    )
    op.create_index("ix_embedding_chunk_id", "embedding", ["chunk_id"])


def downgrade() -> None:
    op.drop_index("ix_embedding_chunk_id", table_name="embedding")
    op.drop_table("embedding")

    op.drop_index("ix_chunk_document_id", table_name="chunk")
    op.drop_table("chunk")
