"""Add company jurisdiction/regime fields and run compiler_mode.

Revision ID: 0014_company_juris_compiler_mode
Revises: 0013_regulatory_bundle_table
Create Date: 2026-02-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0014_company_juris_compiler_mode"
down_revision: str | None = "0013_regulatory_bundle_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "company",
        sa.Column("regulatory_jurisdictions", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "company",
        sa.Column("regulatory_regimes", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "run",
        sa.Column("compiler_mode", sa.String(length=32), nullable=False, server_default="legacy"),
    )


def downgrade() -> None:
    op.drop_column("run", "compiler_mode")
    op.drop_column("company", "regulatory_regimes")
    op.drop_column("company", "regulatory_jurisdictions")
