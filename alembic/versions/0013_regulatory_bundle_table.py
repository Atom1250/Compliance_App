"""Add regulatory_bundle table for registry payload storage.

Revision ID: 0013_regulatory_bundle_table
Revises: 0012_company_year_range
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0013_regulatory_bundle_table"
down_revision: str | None = "0012_company_year_range"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "regulatory_bundle",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bundle_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("jurisdiction", sa.String(length=64), nullable=False),
        sa.Column("regime", sa.String(length=64), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_regulatory_bundle_bundle_id", "regulatory_bundle", ["bundle_id"])
    op.create_index("ix_regulatory_bundle_version", "regulatory_bundle", ["version"])
    op.create_index("ix_regulatory_bundle_checksum", "regulatory_bundle", ["checksum"])


def downgrade() -> None:
    op.drop_index("ix_regulatory_bundle_checksum", table_name="regulatory_bundle")
    op.drop_index("ix_regulatory_bundle_version", table_name="regulatory_bundle")
    op.drop_index("ix_regulatory_bundle_bundle_id", table_name="regulatory_bundle")
    op.drop_table("regulatory_bundle")
