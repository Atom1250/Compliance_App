"""Extend regulatory bundle metadata and run manifest regulatory context.

Revision ID: 0022_regctx_manifest_ext
Revises: 0021_regulatory_source_document
Create Date: 2026-02-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022_regctx_manifest_ext"
down_revision: str | None = "0021_regulatory_source_document"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if not _column_exists("regulatory_bundle", "source_record_ids"):
        op.add_column(
            "regulatory_bundle",
            sa.Column("source_record_ids", sa.JSON(), nullable=False, server_default="[]"),
        )
    if not _column_exists("regulatory_bundle", "effective_from"):
        op.add_column("regulatory_bundle", sa.Column("effective_from", sa.Date(), nullable=True))
    if not _column_exists("regulatory_bundle", "effective_to"):
        op.add_column("regulatory_bundle", sa.Column("effective_to", sa.Date(), nullable=True))
    if not _column_exists("regulatory_bundle", "status"):
        op.add_column(
            "regulatory_bundle",
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        )
    if not _column_exists("regulatory_bundle", "updated_at"):
        op.add_column(
            "regulatory_bundle",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
    op.create_index(
        "ix_regulatory_bundle_status",
        "regulatory_bundle",
        ["status"],
        unique=False,
        if_not_exists=True,
    )
    if not is_sqlite:
        op.create_unique_constraint(
            "uq_regulatory_bundle_triplet",
            "regulatory_bundle",
            ["regime", "bundle_id", "version"],
        )

    if not _column_exists("run_manifest", "regulatory_registry_version"):
        op.add_column(
            "run_manifest",
            sa.Column("regulatory_registry_version", sa.Text(), nullable=True),
        )
    if not _column_exists("run_manifest", "regulatory_compiler_version"):
        op.add_column(
            "run_manifest",
            sa.Column("regulatory_compiler_version", sa.String(length=64), nullable=True),
        )
    if not _column_exists("run_manifest", "regulatory_plan_json"):
        op.add_column("run_manifest", sa.Column("regulatory_plan_json", sa.Text(), nullable=True))
    if not _column_exists("run_manifest", "regulatory_plan_hash"):
        op.add_column(
            "run_manifest", sa.Column("regulatory_plan_hash", sa.String(length=64), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    op.drop_column("run_manifest", "regulatory_plan_hash")
    op.drop_column("run_manifest", "regulatory_plan_json")
    op.drop_column("run_manifest", "regulatory_compiler_version")
    op.drop_column("run_manifest", "regulatory_registry_version")
    if not is_sqlite:
        op.drop_constraint("uq_regulatory_bundle_triplet", "regulatory_bundle", type_="unique")
    op.drop_index("ix_regulatory_bundle_status", table_name="regulatory_bundle")
    op.drop_column("regulatory_bundle", "updated_at")
    op.drop_column("regulatory_bundle", "status")
    op.drop_column("regulatory_bundle", "effective_to")
    op.drop_column("regulatory_bundle", "effective_from")
    op.drop_column("regulatory_bundle", "source_record_ids")
