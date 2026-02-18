"""Add requirements bundle system tables.

Revision ID: 0004_requirements
Revises: 0003_chunk_embedding
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_requirements"
down_revision: str | None = "0003_chunk_embedding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "requirement_bundle",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bundle_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("standard", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("bundle_id", "version", name="uq_requirement_bundle_id_version"),
    )

    op.create_table(
        "datapoint_def",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "requirement_bundle_id",
            sa.Integer(),
            sa.ForeignKey("requirement_bundle.id"),
            nullable=False,
        ),
        sa.Column("datapoint_key", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("disclosure_reference", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "requirement_bundle_id",
            "datapoint_key",
            name="uq_datapoint_def_bundle_datapoint",
        ),
    )
    op.create_index("ix_datapoint_def_requirement_bundle_id", "datapoint_def", ["requirement_bundle_id"])

    op.create_table(
        "applicability_rule",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "requirement_bundle_id",
            sa.Integer(),
            sa.ForeignKey("requirement_bundle.id"),
            nullable=False,
        ),
        sa.Column("rule_id", sa.String(length=128), nullable=False),
        sa.Column("datapoint_key", sa.String(length=128), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "requirement_bundle_id",
            "rule_id",
            name="uq_applicability_rule_bundle_rule",
        ),
    )
    op.create_index(
        "ix_applicability_rule_requirement_bundle_id",
        "applicability_rule",
        ["requirement_bundle_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_applicability_rule_requirement_bundle_id", table_name="applicability_rule")
    op.drop_table("applicability_rule")

    op.drop_index("ix_datapoint_def_requirement_bundle_id", table_name="datapoint_def")
    op.drop_table("datapoint_def")

    op.drop_table("requirement_bundle")
