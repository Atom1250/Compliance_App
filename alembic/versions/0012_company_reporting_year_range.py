"""Add reporting year range fields to company profile.

Revision ID: 0012_company_year_range
Revises: 0011_run_tenant_isolation
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0012_company_year_range"
down_revision: str | None = "0011_run_tenant_isolation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("company", sa.Column("reporting_year_start", sa.Integer(), nullable=True))
    op.add_column("company", sa.Column("reporting_year_end", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE company
        SET reporting_year_start = reporting_year,
            reporting_year_end = reporting_year
        WHERE reporting_year IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("company", "reporting_year_end")
    op.drop_column("company", "reporting_year_start")
