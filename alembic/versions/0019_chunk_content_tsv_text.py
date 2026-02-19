"""Normalize chunk.content_tsv to text for Postgres compatibility.

Revision ID: 0019_chunk_content_tsv_text
Revises: 0018_embedding_vector_column
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019_chunk_content_tsv_text"
down_revision: str | None = "0018_embedding_vector_column"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE chunk ALTER COLUMN content_tsv TYPE text USING content_tsv::text"
    )


def downgrade() -> None:
    # Reverting to tsvector would be lossy for plain-text content and is intentionally omitted.
    return
