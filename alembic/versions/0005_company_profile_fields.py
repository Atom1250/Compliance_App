"""Add company profile fields for applicability evaluation.

Revision ID: 0005_company_profile
Revises: 0004_requirements
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_company_profile"
down_revision: str | None = "0004_requirements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("company", sa.Column("employees", sa.Integer(), nullable=True))
    op.add_column("company", sa.Column("turnover", sa.Float(), nullable=True))
    op.add_column("company", sa.Column("listed_status", sa.Boolean(), nullable=True))
    op.add_column("company", sa.Column("reporting_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("company", "reporting_year")
    op.drop_column("company", "listed_status")
    op.drop_column("company", "turnover")
    op.drop_column("company", "employees")
