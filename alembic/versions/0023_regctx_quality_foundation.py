"""Add compiled plan persistence, inventory metadata, diagnostics, and coverage tables.

Revision ID: 0023_regctx_quality_foundation
Revises: 0022_regctx_manifest_ext
Create Date: 2026-02-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_regctx_quality_foundation"
down_revision: str | None = "0022_regctx_manifest_ext"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compiled_plan",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("company.id"), nullable=False),
        sa.Column("reporting_year", sa.Integer(), nullable=True),
        sa.Column("regime", sa.String(length=64), nullable=False),
        sa.Column("cohort", sa.String(length=64), nullable=False),
        sa.Column("phase_in_flags", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_compiled_plan_entity_id", "compiled_plan", ["entity_id"], unique=False)
    op.create_index(
        "ix_compiled_plan_reporting_year", "compiled_plan", ["reporting_year"], unique=False
    )
    op.create_index("ix_compiled_plan_regime", "compiled_plan", ["regime"], unique=False)

    op.create_table(
        "compiled_obligation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "compiled_plan_id",
            sa.Integer(),
            sa.ForeignKey("compiled_plan.id"),
            nullable=False,
        ),
        sa.Column("obligation_code", sa.String(length=128), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "jurisdiction", sa.String(length=64), nullable=False, server_default="EU"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_compiled_obligation_compiled_plan_id",
        "compiled_obligation",
        ["compiled_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_compiled_obligation_obligation_code",
        "compiled_obligation",
        ["obligation_code"],
        unique=False,
    )

    op.create_table(
        "obligation_coverage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "compiled_plan_id",
            sa.Integer(),
            sa.ForeignKey("compiled_plan.id"),
            nullable=False,
        ),
        sa.Column("obligation_code", sa.String(length=128), nullable=False),
        sa.Column("coverage_status", sa.String(length=16), nullable=False),
        sa.Column("full_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("partial_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("absent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("na_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_obligation_coverage_compiled_plan_id",
        "obligation_coverage",
        ["compiled_plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_obligation_coverage_obligation_code",
        "obligation_coverage",
        ["obligation_code"],
        unique=False,
    )
    op.create_index(
        "ix_obligation_coverage_status",
        "obligation_coverage",
        ["coverage_status"],
        unique=False,
    )

    op.create_table(
        "extraction_diagnostics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column(
            "tenant_id", sa.String(length=64), nullable=False, server_default="default"
        ),
        sa.Column("datapoint_key", sa.String(length=128), nullable=False),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_extraction_diagnostics_run_id",
        "extraction_diagnostics",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_diagnostics_tenant_id",
        "extraction_diagnostics",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_extraction_diagnostics_datapoint_key",
        "extraction_diagnostics",
        ["datapoint_key"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("run_manifest", recreate="always") as batch_op:
            batch_op.add_column(sa.Column("regulatory_plan_id", sa.Integer(), nullable=True))
            batch_op.create_index(
                "ix_run_manifest_regulatory_plan_id",
                ["regulatory_plan_id"],
                unique=False,
            )
            batch_op.create_foreign_key(
                "fk_run_manifest_regulatory_plan_id",
                "compiled_plan",
                ["regulatory_plan_id"],
                ["id"],
            )
    else:
        op.add_column("run_manifest", sa.Column("regulatory_plan_id", sa.Integer(), nullable=True))
        op.create_index(
            "ix_run_manifest_regulatory_plan_id",
            "run_manifest",
            ["regulatory_plan_id"],
            unique=False,
        )
        op.create_foreign_key(
            "fk_run_manifest_regulatory_plan_id",
            "run_manifest",
            "compiled_plan",
            ["regulatory_plan_id"],
            ["id"],
        )

    op.add_column("document", sa.Column("doc_type", sa.String(length=64), nullable=True))
    op.add_column("document", sa.Column("reporting_year", sa.Integer(), nullable=True))
    op.add_column("document", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column(
        "document",
        sa.Column(
            "classification_confidence",
            sa.String(length=32),
            nullable=False,
            server_default="manual",
        ),
    )
    op.create_index("ix_document_doc_type", "document", ["doc_type"], unique=False)
    op.create_index("ix_document_reporting_year", "document", ["reporting_year"], unique=False)
    op.create_index(
        "ix_document_classification_confidence",
        "document",
        ["classification_confidence"],
        unique=False,
    )

    op.add_column(
        "datapoint_def",
        sa.Column(
            "datapoint_type",
            sa.String(length=32),
            nullable=False,
            server_default="narrative",
        ),
    )
    op.add_column(
        "datapoint_def",
        sa.Column(
            "requires_baseline",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("datapoint_def", "requires_baseline")
    op.drop_column("datapoint_def", "datapoint_type")

    op.drop_index("ix_document_classification_confidence", table_name="document")
    op.drop_index("ix_document_reporting_year", table_name="document")
    op.drop_index("ix_document_doc_type", table_name="document")
    op.drop_column("document", "classification_confidence")
    op.drop_column("document", "source_url")
    op.drop_column("document", "reporting_year")
    op.drop_column("document", "doc_type")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("run_manifest", recreate="always") as batch_op:
            batch_op.drop_constraint("fk_run_manifest_regulatory_plan_id", type_="foreignkey")
            batch_op.drop_index("ix_run_manifest_regulatory_plan_id")
            batch_op.drop_column("regulatory_plan_id")
    else:
        op.drop_constraint(
            "fk_run_manifest_regulatory_plan_id", "run_manifest", type_="foreignkey"
        )
        op.drop_index("ix_run_manifest_regulatory_plan_id", table_name="run_manifest")
        op.drop_column("run_manifest", "regulatory_plan_id")

    op.drop_index("ix_extraction_diagnostics_datapoint_key", table_name="extraction_diagnostics")
    op.drop_index("ix_extraction_diagnostics_tenant_id", table_name="extraction_diagnostics")
    op.drop_index("ix_extraction_diagnostics_run_id", table_name="extraction_diagnostics")
    op.drop_table("extraction_diagnostics")

    op.drop_index("ix_obligation_coverage_status", table_name="obligation_coverage")
    op.drop_index("ix_obligation_coverage_obligation_code", table_name="obligation_coverage")
    op.drop_index("ix_obligation_coverage_compiled_plan_id", table_name="obligation_coverage")
    op.drop_table("obligation_coverage")

    op.drop_index("ix_compiled_obligation_obligation_code", table_name="compiled_obligation")
    op.drop_index("ix_compiled_obligation_compiled_plan_id", table_name="compiled_obligation")
    op.drop_table("compiled_obligation")

    op.drop_index("ix_compiled_plan_regime", table_name="compiled_plan")
    op.drop_index("ix_compiled_plan_reporting_year", table_name="compiled_plan")
    op.drop_index("ix_compiled_plan_entity_id", table_name="compiled_plan")
    op.drop_table("compiled_plan")
