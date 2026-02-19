"""Add embedding vector column with pgvector-backed Postgres path.

Revision ID: 0018_embedding_vector_column
Revises: 0017_run_input_snapshot
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0018_embedding_vector_column"
down_revision: str | None = "0017_run_input_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("ALTER TABLE embedding ADD COLUMN IF NOT EXISTS embedding_vector vector")
        op.execute(
            "UPDATE embedding SET embedding_vector = embedding::vector "
            "WHERE embedding_vector IS NULL AND embedding LIKE '[%'"
        )
        return

    op.add_column("embedding", sa.Column("embedding_vector", sa.Text(), nullable=True))
    op.execute("UPDATE embedding SET embedding_vector = embedding WHERE embedding_vector IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("ALTER TABLE embedding DROP COLUMN IF EXISTS embedding_vector")
        return

    op.drop_column("embedding", "embedding_vector")
