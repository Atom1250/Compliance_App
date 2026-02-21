"""Add regulatory_research_cache table.

Revision ID: 0024_regulatory_research_cache
Revises: 0023_regctx_quality_foundation
Create Date: 2026-02-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0024_regulatory_research_cache"
down_revision: str | None = "0023_regctx_quality_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    timestamp_default = sa.text("now()") if is_postgres else sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "regulatory_research_cache",
        sa.Column("request_hash", sa.Text(), primary_key=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("corpus_key", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer_markdown", sa.Text(), nullable=False),
        sa.Column("citations_jsonb", json_type, nullable=False, server_default="[]"),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=timestamp_default,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('success','failed')", name="ck_rr_cache_status"),
    )
    op.create_index(
        "ix_regulatory_research_cache_expires_at",
        "regulatory_research_cache",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_regulatory_research_cache_expires_at", table_name="regulatory_research_cache")
    op.drop_table("regulatory_research_cache")
