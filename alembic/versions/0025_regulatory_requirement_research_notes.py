"""Add regulatory_requirement_research_notes table.

Revision ID: 0025_reg_research_notes
Revises: 0024_regulatory_research_cache
Create Date: 2026-02-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0025_reg_research_notes"
down_revision: str | None = "0024_regulatory_research_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

    op.create_table(
        "regulatory_requirement_research_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("requirement_id", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("corpus_key", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer_markdown", sa.Text(), nullable=False),
        sa.Column("citations_jsonb", json_type, nullable=False, server_default="[]"),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_rr_notes_requirement_created_at",
        "regulatory_requirement_research_notes",
        ["requirement_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_rr_notes_request_hash",
        "regulatory_requirement_research_notes",
        ["request_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rr_notes_request_hash", table_name="regulatory_requirement_research_notes")
    op.drop_index(
        "ix_rr_notes_requirement_created_at", table_name="regulatory_requirement_research_notes"
    )
    op.drop_table("regulatory_requirement_research_notes")
