"""Add tenant_id columns to run-related tables.

Revision ID: 0011_run_tenant_isolation
Revises: 0010_run_manifest
Create Date: 2026-02-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0011_run_tenant_isolation"
down_revision: str | None = "0010_run_manifest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = [
        "run_event",
        "run_materiality",
        "datapoint_assessment",
        "run_cache_entry",
        "run_manifest",
    ]
    for table in tables:
        op.add_column(
            table,
            sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    op.execute(
        """
        UPDATE run_event
        SET tenant_id = COALESCE((SELECT tenant_id FROM run WHERE run.id = run_event.run_id), 'default')
        """
    )
    op.execute(
        """
        UPDATE run_materiality
        SET tenant_id = COALESCE((SELECT tenant_id FROM run WHERE run.id = run_materiality.run_id), 'default')
        """
    )
    op.execute(
        """
        UPDATE datapoint_assessment
        SET tenant_id = COALESCE((SELECT tenant_id FROM run WHERE run.id = datapoint_assessment.run_id), 'default')
        """
    )
    op.execute(
        """
        UPDATE run_cache_entry
        SET tenant_id = COALESCE((SELECT tenant_id FROM run WHERE run.id = run_cache_entry.run_id), 'default')
        """
    )
    op.execute(
        """
        UPDATE run_manifest
        SET tenant_id = COALESCE((SELECT tenant_id FROM run WHERE run.id = run_manifest.run_id), 'default')
        """
    )


def downgrade() -> None:
    tables = [
        "run_manifest",
        "run_cache_entry",
        "datapoint_assessment",
        "run_materiality",
        "run_event",
    ]
    for table in tables:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
